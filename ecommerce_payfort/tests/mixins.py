import responses
from django.conf import settings
from oscar.core.loading import get_class, get_model
from six.moves.urllib.parse import urljoin

CURRENCY = 'SAR'
Basket = get_model('basket', 'Basket')
Order = get_model('order', 'Order')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentProcessorResponse = get_model('payment', 'PaymentProcessorResponse')
SourceType = get_model('payment', 'SourceType')

post_checkout = get_class('checkout.signals', 'post_checkout')


class PayFortMixin:
    """
    Mixin with helper methods for mocking PayFort API responses.
    """

    def mock_api_response(self, path, body, method=responses.POST, resp=responses):
        url = self._create_api_url(path=path)
        resp.add(method, url, json=body)

    def _create_api_url(self, path):
        """
        Returns the API URL
        """
        base_url = settings.PAYMENT_PROCESSOR_CONFIG['edx']['payfort']['payfort_base_api_url']
        return urljoin(base_url, path)
