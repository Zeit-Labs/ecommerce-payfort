"""
PayFort payment processor Django application initialization.
"""
from django.apps import AppConfig


class PayFortConfig(AppConfig):
    """
    Configuration for the PayFort payment processor Django application.
    """
    name = 'ecommerce_payfort'
    plugin_app = {
        'url_config': {
            'ecommerce': {
                'namespace': 'ecommerce_payfort',
            }
        },
    }
