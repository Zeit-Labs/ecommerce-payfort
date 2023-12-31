"""
PayFort payment processor.
"""

import logging

from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from oscar.apps.payment.exceptions import GatewayError

from ecommerce.extensions.payment.processors import BasePaymentProcessor

logger = logging.getLogger(__name__)


def format_price(price):
    """
    Return the price in the expected format.
    """
    return '{:0.2f}'.format(price)


class PayFortException(GatewayError):
    """
    An umbrella exception to catch all errors from PayFort.
    """
    pass  # pylint: disable=unnecessary-pass


class PayFort(BasePaymentProcessor):
    """
    PayFort payment processor.

    For reference, see https://paymentservices-reference.payfort.com/docs/api/build/index.html
    Scroll through the page, it's a very long single-page documentation.
    """

    NAME = 'payfort'
    CHECKOUT_TEXT = _("Checkout with credit card")
    CHECKOUT_ENDPOINT = '/paymentPage/'
    
    def __init__(self, site):
        super(PayFort, self).__init__(site)
        configuration = self.configuration
        self.merchant_identifier = configuration['merchant_identifier']
        self.access_code = configuration['access_code']
        self.SHARequestPhrase = configuration['SHARequestPhrase']
        self.SHAResponsePhrase = configuration['SHAResponsePhrase']
        self.SHAType = configuration['SHAType']
        self.payfort_base_api_url = configuration.get('payfort_base_api_url', 'https://sbcheckout.payfort.com/FortAPI/paymentPage')
        self.return_url = reverse('hyperpay:payment-form'),

        self.site = site
