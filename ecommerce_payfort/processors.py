"""
PayFort payment processor.
"""

import logging

from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from oscar.apps.payment.exceptions import GatewayError

from ecommerce.extensions.payment.processors import BasePaymentProcessor
from ecommerce.extensions.payment.utils import clean_field_value

logger = logging.getLogger(__name__)


# TODO: this will use the algorithm provided by Payfort for different currencies
def format_price(price, currency):
    """
    Return the price in the expected format.
    """
    return price


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

    def _get_customer_profile_data(self, user, request):
        """
        Return the user profile data.
        """

        def get_extended_profile_field(account_details, field_name, default_value=None):
            """
            Helper function to get the values of extended profile fields.
            """
            return next(
                (
                    field.get('field_value', default_value) for field in account_details['extended_profile']
                    if field['field_name'] == field_name
                ),
                default_value
            )
        user_account_details = user.account_details(request)
        data = {
            'customer.email': user.email,
        }

        first_name = get_extended_profile_field(user_account_details, 'first_name', '')
        if first_name:
            data['customer.givenName'] = first_name
            data['customer.surname'] = get_extended_profile_field(user_account_details, 'last_name', '')
        else:
            logger.warning('Unable to get the first name and last name for the user %s', user.username)

        return data

    def _get_basket_data(self, basket):
        """
        Return the basket data
        """

        def get_cart_field(index, name):
            """
            Return the cart field name.
            """
            return 'cart.items[{}].{}'.format(index, name)

        basket_data = {
            'amount': basket.total_incl_tax,
            'currency': self.currency,
            'merchantTransactionId': basket.order_number
        }
        for index, line in enumerate(basket.all_lines()):
            cart_item = {
                get_cart_field(index, 'name'): clean_field_value(line.product.title),
                get_cart_field(index, 'quantity'): line.quantity,
                get_cart_field(index, 'type'): self.CART_ITEM_TYPE_DIGITAL,
                get_cart_field(index, 'sku'): line.stockrecord.partner_sku,
                get_cart_field(index, 'price'): line.unit_price_incl_tax,
                get_cart_field(index, 'currency'): self.currency,
                get_cart_field(index, 'totalAmount'): line.line_price_incl_tax_incl_discounts
            }
            basket_data.update(cart_item)
        return basket_data
    
    def get_transaction_parameters(self, basket, request=None, use_client_side_checkout=False, **kwargs):
        """
        Return the transaction parameters needed for this processor.
        """
        
        transaction_parameters = {
            'payment_page_url': reverse('payfort:payment-form'),
            'payment_result_url': self.return_url,
            'locale': request.LANGUAGE_CODE.split('-')[0],
            'csrfmiddlewaretoken': get_token(request),
        }
        return transaction_parameters
    
    def handle_processor_response(self, response, basket=None):
        logger.exception(
            'Not yet implemented in Payfort'
        )

    def issue_credit(self, order_number, basket, reference_number, amount, currency):
        logger.exception(
            'Payfort processor cannot issue credits or refunds from Open edX ecommerce.'
        )