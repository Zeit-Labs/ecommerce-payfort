"""PayFort payment processor."""
import logging
from urllib.parse import urljoin

from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from ecommerce.extensions.payment.processors import BasePaymentProcessor, HandledProcessorResponse

from ecommerce_payfort import utils

logger = logging.getLogger(__name__)


class PayFort(BasePaymentProcessor):
    """
    PayFort payment processor.

    For reference, see https://paymentservices-reference.payfort.com/docs/api/build/index.html
    Scroll through the page, it's a very long single-page documentation.
    """
    CHECKOUT_TEXT = _("Checkout with credit card")
    NAME = "payfort"

    def __init__(self, site):
        """Initialize the PayFort processor."""
        super().__init__(site)
        self.site = site

        self.access_code = self.configuration.get("access_code")
        self.merchant_identifier = self.configuration.get("merchant_identifier")
        self.request_sha_phrase = self.configuration.get("request_sha_phrase")
        self.response_sha_phrase = self.configuration.get("response_sha_phrase")
        self.sha_method = self.configuration.get("sha_method")
        self.ecommerce_url_root = self.configuration.get("ecommerce_url_root")

    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=False, **kwargs):
        """Return the transaction parameters needed for this processor."""
        transaction_parameters = {
            "command": "PURCHASE",
            "access_code": self.access_code,
            "merchant_identifier": self.merchant_identifier,
            "language": utils.get_language(request),
            "merchant_reference": utils.get_merchant_reference(self.site.id, basket),
            "amount": utils.get_amount(basket),
            "currency": utils.get_currency(basket),
            "customer_email": utils.get_customer_email(basket),
            "customer_ip": utils.get_ip_address(request),
            "order_description": utils.get_order_description(basket),
            "customer_name": utils.get_customer_name(basket),
            "return_url": urljoin(
                self.ecommerce_url_root,
                reverse("payfort:response")
            ),
        }

        signature = utils.get_signature(
            self.request_sha_phrase,
            self.sha_method,
            transaction_parameters,
        )
        transaction_parameters.update({
            "signature": signature,
            "payment_page_url": reverse("payfort:form"),
            "csrfmiddlewaretoken": get_token(request),
        })

        return transaction_parameters

    def handle_processor_response(self, response, basket=None):
        """Handle the payment processor response and record the relevant details."""
        currency = response["currency"]
        total = int(response["amount"]) / 100
        transaction_id = utils.get_transaction_id(response)
        card_number = response.get("card_number")
        card_type = response.get("payment_option")

        return HandledProcessorResponse(
            transaction_id=transaction_id,
            total=total,
            currency=currency,
            card_number=card_number,
            card_type=card_type
        )

    def issue_credit(
            self, order_number, basket, reference_number, amount, currency
    ):  # pylint: disable=too-many-arguments
        """Not available."""
        raise NotImplementedError("PayFort processor cannot issue credits or refunds from Open edX ecommerce.")
