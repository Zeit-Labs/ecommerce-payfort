from ecommerce.settings.test import *

INSTALLED_APPS += ["ecommerce_payfort"]

payfort_settings = {
    "access_code": "123123123",
    "merchant_identifier": "mid123",
    "request_sha_phrase": "secret@req",
    "response_sha_phrase": "secret@res",
    "sha_method": "SHA-256",
    "ecommerce_url_root": "http://myecommerce.mydomain.com",
}
PAYMENT_PROCESSOR_CONFIG["edx"]["payfort"] = payfort_settings.copy()
PAYMENT_PROCESSOR_CONFIG["other"]["payfort"] = payfort_settings.copy()

COMPRESS_ENABLED = False
COMPRESS_OFFLINE = False
COMPRESS_PRECOMPILERS = []
ROOT_URLCONF = "ecommerce_payfort.tests.urls"
