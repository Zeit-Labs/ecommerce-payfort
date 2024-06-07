""" Tests for the PayFort payment processor. """
from unittest.mock import patch
import ddt
from django.conf import settings as django_settings
from ecommerce.extensions.payment.processors import HandledProcessorResponse
from ecommerce.extensions.payment.tests.processors.mixins import PaymentProcessorTestCaseMixin
from ecommerce.tests.testcases import TestCase

from ecommerce_payfort.processors import PayFort
from ecommerce_payfort import utils


@ddt.ddt
class PayFortTests(PaymentProcessorTestCaseMixin, TestCase):  # pylint: disable=too-many-ancestors
    """ Tests for the PayFort payment processor. """
    processor_name = "payfort"
    processor_class = PayFort

    @classmethod
    def setUpClass(cls):
        """ Set up the test class. """
        super().setUpClass()
        cls.patcher = patch("ecommerce_payfort.utils.get_currency", return_value=utils.VALID_CURRENCY)
        cls.mock_get_currency = cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        """ Tear down the test class. """
        cls.patcher.stop()
        super().tearDownClass()

    def test_init(self):
        """ Verify the processor initializes from the configuration. """
        settings = django_settings.PAYMENT_PROCESSOR_CONFIG["edx"]["payfort"]
        processor = self.processor_class(self.site)
        self.assertEqual(processor.site, self.site)
        self.assertEqual(processor.access_code, settings["access_code"])
        self.assertEqual(processor.merchant_identifier, settings["merchant_identifier"])
        self.assertEqual(processor.request_sha_phrase, settings["request_sha_phrase"])
        self.assertEqual(processor.response_sha_phrase, settings["response_sha_phrase"])
        self.assertEqual(processor.sha_method, settings["sha_method"])
        self.assertEqual(processor.ecommerce_url_root, settings["ecommerce_url_root"])

    def test_handle_processor_response(self):
        """ Verify that the processor creates the appropriate PaymentEvent and Source objects. """
        with patch("ecommerce_payfort.utils.get_transaction_id", return_value="1234567890"):
            response = {
                "amount": "2000",
                "currency": "SAR",
                "card_number": "1234",
                "payment_option": "VISA",
            }
            expected_result = HandledProcessorResponse(
                transaction_id="1234567890",
                total=20.0,
                currency="SAR",
                card_number="1234",
                card_type="VISA"
            )
            actual_result = self.processor.handle_processor_response(response)
            self.assertEqual(expected_result, actual_result)

    def test_get_transaction_parameters(self):
        """ Verify the processor returns the appropriate parameters required to complete a transaction. """
        customer_ip = "199.199.199.199"
        expected_result = {
            "command": "PURCHASE",
            "access_code": "123123123",
            "merchant_identifier": "mid123",
            "language": "en",
            "merchant_reference": f"{self.request.site.id}-{self.basket.owner.id}-{self.basket.id}",
            "amount": 2000,
            "currency": "SAR",
            "customer_email": self.basket.owner.email,
            "customer_ip": customer_ip,
            "order_description": f"1 X {self.basket.all_lines()[0].product.course.id}",
            "customer_name": "Ecommerce User",
            "return_url": "http://myecommerce.mydomain.com/payfort/response/",
        }
        with patch("ecommerce_payfort.utils.get_ip_address", return_value=customer_ip):
            actual_result = self.processor.get_transaction_parameters(self.basket, request=self.request)
        actual_result.pop("csrfmiddlewaretoken")
        actual_result.pop("payment_page_url")
        expected_result["signature"] = utils.get_signature(
            self.processor.request_sha_phrase,
            self.processor.sha_method,
            expected_result,
        )
        print("actual_result: ", actual_result)
        self.assertDictEqual(expected_result, actual_result)

    def test_issue_credit_error(self):
        """not used"""

    def test_issue_credit(self):
        """Verify that issue_credit raises a NotImplementedError."""
        with self.assertRaises(NotImplementedError) as exc:
            self.processor.issue_credit("order_number", self.basket, "reference_number", 2000, "SAR")
        self.assertEqual(
            str(exc.exception),
            "PayFort processor cannot issue credits or refunds from Open edX ecommerce."
        )
