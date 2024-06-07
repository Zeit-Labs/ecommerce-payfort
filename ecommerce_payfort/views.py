"""Views related to the PayFort payment processor."""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic, non_atomic_requests
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin
from ecommerce.extensions.checkout.utils import get_receipt_page_url
from oscar.apps.partner import strategy
from oscar.core.loading import get_class, get_model

from ecommerce_payfort import utils
from ecommerce_payfort.processors import PayFort

logger = logging.getLogger(__name__)

Applicator = get_class("offer.applicator", "Applicator")
Basket = get_model("basket", "Basket")
OrderNumberGenerator = get_class("order.utils", "OrderNumberGenerator")


class PayFortPaymentRedirectView(LoginRequiredMixin, TemplateView):
    """Render the template which loads the PayFort payment form via JavaScript"""
    template_name = "payfort_payment/form.html"

    def post(self, request):
        """Handles the POST request."""
        return render(request=request, template_name=self.template_name, context=request.POST.dict())


class PayFortCallBaseView(EdxOrderPlacementMixin, View):
    """Base class for the PayFort views."""
    def __init__(self, *args, **kwargs):
        """Initialize the PayFortCallBaseView."""
        super().__init__(*args, **kwargs)
        self.payment_processor = None
        self.request = None
        self._basket = None

    @method_decorator(non_atomic_requests)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Dispatch the request to the appropriate handler."""
        return super().dispatch(request, *args, **kwargs)

    @property
    def basket(self):
        """Retrieve the basket from the database."""
        if self._basket is not None:
            return self._basket

        if not self.request:
            return None

        merchant_reference = self.request.POST.get("merchant_reference", "")

        try:
            basket_id = int(merchant_reference.split('-')[-1])
            basket = Basket.objects.get(id=basket_id)
            basket.strategy = strategy.Default()
            Applicator().apply(basket, basket.owner, self.request)

            self._basket = basket
        except (ValueError, ObjectDoesNotExist):
            return None

        return self._basket

    def log_error(self, message):
        """Log the error message."""
        logger.error("%s: %s", self.__class__.__name__, message)

    def save_payment_processor_response(self, response_data):
        """Save the payment processor response to the database."""
        try:
            return self.payment_processor.record_processor_response(
                response={
                    "view": self.__class__.__name__,
                    "response": response_data
                },
                transaction_id=utils.get_transaction_id(response_data),
                basket=self.basket
            )
        except Exception as exc:
            self.log_error(
                f"Recording payment processor response failed! "
                f"merchant_reference: {response_data.get('merchant_reference', 'none')}. "
                f"Exception: {str(exc)}"
            )
            raise Http404 from exc

    def validate_response(self, response_data):
        """Validate the response from PayFort."""
        try:
            utils.verify_signature(
                self.payment_processor.response_sha_phrase,
                self.payment_processor.sha_method,
                response_data,
            )
        except utils.PayFortBadSignatureException as exc:
            self.log_error(str(exc))
            raise

        success = response_data.get("status", "") == utils.SUCCESS_STATUS

        try:
            utils.verify_response_format(response_data)
        except utils.PayFortException as exc:
            self.log_error(str(exc))
            if success and self.basket:
                reference = response_data.get("fort_id", "none")
                self.log_error(
                    f"Bad response format for a successful payment! reference: {reference}, "
                    f"merchant_reference: {response_data.get('merchant_reference', 'none')}"
                )
            raise Http404 from exc

        if not self.basket:
            self.log_error(
                f"Basket not found! merchant_reference: {response_data['merchant_reference']}"
            )
            raise Http404()


class PayFortRedirectionResponseView(PayFortCallBaseView):
    """Handle the response from PayFort sent to customer after processing the payment."""
    template_name = "payfort_payment/wait_feedback.html"
    MAX_ATTEMPTS = 24
    WAIT_TIME = 5000

    def post(self, request):
        """Handle the POST request from PayFort after processing the payment."""
        data = request.POST.dict()
        self.payment_processor = PayFort(request.site)
        self.request = request

        try:
            self.validate_response(data)
        except utils.PayFortBadSignatureException as exc:
            raise Http404 from exc
        except utils.PayFortException:
            self.save_payment_processor_response(data)
            return redirect(reverse(
                'payfort:handle-internal-error',
                args=[utils.get_transaction_id(data)]
            ))
        except Http404:
            self.save_payment_processor_response(data)
            raise

        payment_processor_response = self.save_payment_processor_response(data)
        if data["status"] == utils.SUCCESS_STATUS:
            data["ecommerce_transaction_id"] = payment_processor_response.transaction_id
            data["ecommerce_error_url"] = reverse(
                'payfort:handle-internal-error',
                args=[payment_processor_response.transaction_id]
            )
            data["ecommerce_status_url"] = reverse("payfort:status")
            data["ecommerce_max_attempts"] = self.MAX_ATTEMPTS
            data["ecommerce_wait_time"] = self.WAIT_TIME
            return render(request=request, template_name=self.template_name, context=data)

        self.log_error(
            f"Payfort payment failed! merchant_reference: {data['merchant_reference']}. "
            f"response_code: {data['response_code']}"
        )
        return redirect(reverse("payment_error"))


class PayFortStatusView(PayFortCallBaseView):
    """Handle the status request from PayFort."""
    def post(self, request):
        """Handle the POST request from PayFort."""
        if not self.basket:
            return HttpResponse(status=404)

        if self.basket.status == Basket.FROZEN:
            return HttpResponse(status=204)

        if self.basket.status == Basket.SUBMITTED:
            return JsonResponse(
                {
                    "receipt_url": get_receipt_page_url(
                        request=request,
                        site_configuration=self.basket.site.siteconfiguration,
                        order_number=self.basket.order_number,
                    ),
                },
                status=200,
            )

        return HttpResponse(status=404)


class PayFortFeedbackView(PayFortCallBaseView):
    """Handle the response from PayFort sent to customer after processing the payment."""
    def post(self, request):
        """Handle the POST request from PayFort after processing the payment."""
        data = request.POST.dict()
        self.payment_processor = PayFort(request.site)
        self.request = request

        try:
            self.validate_response(data)
        except utils.PayFortBadSignatureException as exc:
            raise Http404 from exc
        except (Http404, utils.PayFortException) as exc:
            self.save_payment_processor_response(data)
            raise Http404 from exc

        payment_processor_response = self.save_payment_processor_response(data)
        if data["status"] != utils.SUCCESS_STATUS:
            self.log_error(
                f"Payfort payment failed! merchant_reference: {data['merchant_reference']}. "
                f"response_code: {data['response_code']}"
            )
            return HttpResponse(status=200)

        if self.basket.status == Basket.SUBMITTED:
            return HttpResponse(status=200)

        try:
            with atomic():
                self.handle_payment(data, self.basket)
                self.create_order(request, self.basket)
        except Exception as exc:  # pylint:disable=broad-except
            logger.exception(
                "Processing payment for basket [%d] failed! "
                "The payment was successfully processed by PayFort. Response was recorded in entry no. "
                "(%d: %s). "
                "Exception: %s: %s",
                self.basket.id,
                payment_processor_response.id,
                payment_processor_response.transaction_id,
                exc.__class__.__name__,
                str(exc),
            )
            return HttpResponse(status=422)

        return HttpResponse(status=200)


class PayFortNotificationView(PayFortFeedbackView):
    """Handle the notification from PayFort."""


class PayFortPaymentHandleInternalErrorView(TemplateView):
    """Render the template that shows the error message to the user when the payment handling is failed."""
    template_name = "payfort_payment/handle_internal_error.html"

    def get(self, request, *args, **kwargs):
        """Handles the GET request."""
        context = {
            "merchant_reference": args[0],
        }
        return render(request, self.template_name, context)


class PayFortPaymentHandleFormatErrorView(TemplateView):
    """Render the template that shows the error message to the user when the payment response is in wrong format."""
    template_name = "payfort_payment/handle_format_error.html"

    def get(self, request, *args, **kwargs):
        """Handles the GET request."""
        context = {
            "reference": args[0],
        }
        return render(request, self.template_name, context)
