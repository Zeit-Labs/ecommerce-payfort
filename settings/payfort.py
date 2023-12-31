from ecommerce.settings.test import *

INSTALLED_APPS += ['ecommerce_payfort']

PAYMENT_PROCESSOR_CONFIG = {
    'edx': {
        'payfort': {
            'merchant_identifier': '**********',
            'access_code': '**********',
            'SHARequestPhrase': '**********',
            'SHAResponsePhrase': '**********',
            'SHAType': '**********',
            'sandbox_mode': True,
            '3ds_modal': True,
            'debug_mode': False,
            'locale': 'en',
        }
    }
}