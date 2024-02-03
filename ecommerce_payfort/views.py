"""
Views related to the PayFort payment processor.
"""

import logging

from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from oscar.core.loading import get_class, get_model

from ecommerce.extensions.checkout.mixins import EdxOrderPlacementMixin

from .processors import PayFort

logger = logging.getLogger(__name__)

Applicator = get_class('offer.applicator', 'Applicator')
Basket = get_model('basket', 'Basket')
OrderNumberGenerator = get_class('order.utils', 'OrderNumberGenerator')


class PayFortPaymentPageView(View):
    """
    Render the template which loads the PayFort payment form via JavaScript
    """
    template_name = 'payment/payfort.html'

    @method_decorator(csrf_exempt)
    def post(self, request):
        """
        Handles the POST request.
        """
        return render(request, self.template_name, request.POST.dict())


class PayFortResponseView(EdxOrderPlacementMixin, View):
    """
    Handle the response from PayFort after processing the payment.
    """

    @property
    def payment_processor(self):
        return PayFort(self.request.site)

    @method_decorator(transaction.non_atomic_requests)
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(PayFortResponseView, self).dispatch(request, *args, **kwargs)
