"""Test the views of the app."""
import json
import logging
import unittest
from unittest.mock import Mock, patch, PropertyMock

import ddt
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404
from django.test import Client, RequestFactory
from django.urls import reverse
from ecommerce.tests.factories import UserFactory
from ecommerce.tests.testcases import TestCase

from ecommerce_payfort import utils
from ecommerce_payfort import views
from ecommerce_payfort.processors import PayFort
from ecommerce_payfort.tests.test_mixins import MockPatcherMixin


class BaseTests(TestCase):  # pylint: disable=too-many-ancestors
    """Base test class."""
    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory(username="testuser", password="12345")
        self.payment_data = {
            "command": "payment-command",
            "access_code": "access-code",
            "merchant_identifier": "something",
            "merchant_reference": "a reference",
            "amount": "an integer",
            "currency": "FAKE",
            "language": "en",
            "customer_email": "me@example.com",
            "customer_ip": "1.1.1.1",
            "order_description": "whatever",
            "signature": "long-string-after-encryption",
            "customer_name": "John Doe",
            "return_url": "/payfort/response/",
        }

    def login(self):
        """Log in the user."""
        self.client.login(username="testuser", password="12345")


class TestPayFortPaymentRedirectView(BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortPaymentRedirectView."""
    after_signature_keys = [
        "payment_page_url",
        "csrfmiddlewaretoken",
    ]

    def test_post(self):
        """Test the POST method."""
        self.login()
        response = self.client.post(reverse("payfort:form"), self.payment_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payfort_payment/form.html")

        content = response.content.decode("utf-8")
        self.assertIn("Redirecting to the Payment Gateway...", content)
        for key, value in self.payment_data.items():
            self.assertIn(f"<input type=\"hidden\" name=\"{key}\" value=\"{value}\">", content)

    def test_must_be_logged_in(self):
        """Test the POST method."""
        response = self.client.post(reverse("payfort:form"), self.payment_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/login/?next=/payfort/pay/")

    def test_payment_data(self):
        """Verify that payment data is set for all fields except those added after calculating the signature."""
        processor = PayFort(self.site)
        with patch("ecommerce_payfort.processors.utils"), patch("ecommerce_payfort.processors.get_token"):
            transaction_parameters = processor.get_transaction_parameters(Mock())

        for key in self.payment_data:
            self.assertIn(
                key, transaction_parameters,
                f"payment_data key ({key}) not found in transaction_parameters. This means that you've removed fields"
                " from get_transaction_parameters but you forgot to remove them from the payment_data in the test."
            )
            transaction_parameters.pop(key)
        for key in self.after_signature_keys:
            self.assertIn(
                key, transaction_parameters,
                f"after_signature_keys key ({key}) found in transaction_parameters. This means that you've removed"
                " fields from get_transaction_parameters after calculating the signature but you forgot to remove them"
                " from the after_signature_keys in the test."
            )
            transaction_parameters.pop(key)

        self.assertFalse(
            transaction_parameters,
            "transaction_parameters is not empty! this means that you've added new fields to the processor"
            " but you forgot to add them to the payment_data in the test. Adding the new fields to the payment_data"
            " will also require adding them to `form.html`, unless they are ecommerce-specific fields that are added"
            " after calculating the signature. If so, then add them only to the `after_signature_keys` list in the test"
            " and not in the payment_data nor in the `form.html`."
            "\nThis test is your guard to avoid missing up the synchronization between get_transaction_parameters"
            " and the form."
        )


class TestPayFortPaymentHandleInternalErrorView(BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortPaymentHandleInternalErrorView."""
    def test_get(self):
        """Test the GET method."""
        response = self.client.get(reverse("payfort:handle-internal-error", args=["merchant_reference_value"]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payfort_payment/handle_internal_error.html")
        self.assertIn(
            "For your reference, the payment ID is: <strong>merchant_reference_value</strong>",
            response.content.decode("utf-8")
        )


class TestPayFortPaymentHandleFormatErrorView(BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortPaymentHandleFormatErrorView."""
    def test_get(self):
        """Test the GET method."""
        response = self.client.get(reverse("payfort:handle-format-error", args=["a_reference_value"]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payfort_payment/handle_format_error.html")
        self.assertIn(
            "For your reference, the payment ID is: <strong>a_reference_value</strong>",
            response.content.decode("utf-8")
        )


class TestPayFortCallBaseView(MockPatcherMixin, BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortCallBaseView."""
    class DerivedView(views.PayFortCallBaseView):
        """Derived view for testing __class__.__name__ validity."""

    patching_config = {
        "get_transaction_id": ("ecommerce_payfort.utils.get_transaction_id", {
            "return_value": "the-transaction-id",
        }),
        "log_error": ("ecommerce_payfort.views.PayFortCallBaseView.log_error", {}),
        "verify_signature": ("ecommerce_payfort.utils.verify_signature", {
            "autospec": True
        }),
        "verify_response_format": ("ecommerce_payfort.utils.verify_response_format", {
            "autospec": True
        }),
    }

    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.view = views.PayFortCallBaseView()

    def _set_request(self, data, method="post", path="/", user=None):
        """Helper method to set the request."""
        request = getattr(RequestFactory(), method)(path, data)
        request.user = AnonymousUser() if user is None else user
        self.view.request = request

    def test_basket_with_basket_set(self):
        """Verify that  basket property reads from the cached object."""
        self.view._basket = "test_basket"  # pylint: disable=protected-access
        self.assertEqual(self.view.basket, "test_basket")

    def test_basket_with_no_request(self):
        """Verify that basket property returns None when request is None."""
        self.view.request = None
        self.assertIsNone(self.view.basket)

    def test_basket_with_non_existent_basket(self):
        """Verify that basket property returns None when the basket does not exist."""
        self._set_request(data={"merchant_reference": "test-1"})
        self.assertIsNone(self.view.basket)

    def test_basket_with_existent_basket(self):
        """Verify that basket property returns the basket when it exists."""
        basket = utils.Basket.objects.create()
        self._set_request(data={"merchant_reference": f"test-{basket.id}"})
        self.assertEqual(self.view.basket, basket)

    def test_basket_with_existent_basket_bad_merchant_reference(self):
        """Verify that basket property returns the basket when it exists."""
        basket = utils.Basket.objects.create()
        self._set_request(data={"merchant_reference": f"test{basket.id}"})
        self.assertIsNone(self.view.basket)

    def test_basket_with_existent_basket_with_missing_merchant_reference(self):
        """Verify that basket property returns None when merchant_reference is missing."""
        utils.Basket.objects.create()
        self._set_request(data={})
        self.assertIsNone(self.view.basket)

    @patch.object(logging.Logger, 'error')
    def test_log_error(self, mock_logger_error):
        """Verify that log_error method logs the error message."""
        self.patchers["log_error"].stop()
        self.DerivedView().log_error("Test message 1")
        mock_logger_error.assert_called_once_with("%s: %s", "DerivedView", "Test message 1")
        self.mocks["log_error"] = self.patchers["log_error"].start()

    def test_save_payment_processor_response(self):
        """Verify that save_payment_processor_response calls the record_processor_response method."""
        view = self.DerivedView()
        view.payment_processor = Mock(record_processor_response=Mock())
        view._basket = Mock(id=7, total_incl_tax=456.78, currency="FAKE")  # pylint: disable=protected-access
        view.save_payment_processor_response({"any": "any"})
        view.payment_processor.record_processor_response.assert_called_once_with(
            response={
                "view": "DerivedView",
                "response": {"any": "any"}
            },
            transaction_id="the-transaction-id",
            basket=view.basket,
        )

    def test_save_payment_processor_response_exception(self):
        """Verify that save_payment_processor_response logs the exception when record_processor_response fails."""
        view = self.DerivedView()
        view.payment_processor = Mock(record_processor_response=Mock(side_effect=Exception("Test exception")))

        with self.assertRaises(Http404):
            view.save_payment_processor_response({"merchant_reference": "test_ref"})

        self.mocks["log_error"].assert_called_once_with(
            "Recording payment processor response failed! "
            "merchant_reference: test_ref. "
            "Exception: Test exception"
        )

    def _validate_response_success(self):
        """Helper method to perform succeeding request."""
        response_data = {
            "status": utils.SUCCESS_STATUS,
            "merchant_reference": "test-1"
        }
        self.view.payment_processor = Mock()
        self.view._basket = Mock(id=7, total_incl_tax=456.78, currency="FAKE")  # pylint: disable=protected-access
        self.view.validate_response(response_data)
        return response_data

    def test_validate_response_success(self):
        """Verify that validate_response calls the appropriate functions."""
        response_data = self._validate_response_success()
        self.mocks["verify_signature"].assert_called_once_with(
            self.view.payment_processor.response_sha_phrase,
            self.view.payment_processor.sha_method,
            response_data,
        )
        self.mocks["verify_response_format"].assert_called_once_with(response_data)

    def test_validate_response_first_verify_signature_then_verify_response_format(self):
        """Verify that validate_response calls the appropriate functions."""
        self._validate_response_success()
        self.assertEqual(self.mocks["verify_signature"].call_count, 1)
        self.assertEqual(self.mocks["verify_response_format"].call_count, 1)
        for call in self.mocks["verify_signature"].mock_calls + self.mocks["verify_response_format"].mock_calls:
            self.assertNotIn(call, self.mocks["verify_response_format"].mock_calls)
            if call in self.mocks["verify_signature"].mock_calls:
                break

    def test_validate_response_bad_signature(self):
        """Verify that validate_response logs the exception when verify_signature fails."""
        response_data = {
            "status": "99",
            "merchant_reference": "test-1"
        }
        self.mocks["verify_signature"].side_effect = utils.PayFortBadSignatureException(
            "Signature verification failed for response data: %s" % response_data,
        )
        self.view.payment_processor = Mock()
        with self.assertRaises(utils.PayFortBadSignatureException):
            self.view.validate_response(response_data)
        self.mocks["verify_signature"].assert_called_once_with(
            self.view.payment_processor.response_sha_phrase,
            self.view.payment_processor.sha_method,
            response_data,
        )
        self.mocks["verify_response_format"].assert_not_called()
        self.mocks["log_error"].assert_called_once_with(
            "Signature verification failed for response data: {'status': '99', 'merchant_reference': 'test-1'}"
        )

    def _assert_bad_format_error(self, response_data):
        """Helper method to assert the bad format error."""
        self.mocks["verify_response_format"].side_effect = utils.PayFortException(
            "Bad format for response data: missing mandatory field",
        )
        self.view.payment_processor = Mock()

        with self.assertRaises(Http404):
            self.view.validate_response(response_data)

        self.mocks["verify_signature"].assert_called_once()
        self.mocks["verify_response_format"].assert_called_once_with(response_data)

    def test_validate_response_bad_format(self):
        """Verify that validate_response logs the exception when verify_response_format fails."""
        self._assert_bad_format_error({
            "status": "99",
            "merchant_reference": "test-1"
        })
        self.mocks["log_error"].assert_called_once_with(
            "Bad format for response data: missing mandatory field"
        )

    def test_validate_response_bad_format_but_successful_payment(self):
        """Verify that validate_response logs the incident of having a bad payload for a successful payment."""
        self.view._basket = Mock()  # pylint: disable=protected-access
        self._assert_bad_format_error({
            "status": utils.SUCCESS_STATUS,
            "merchant_reference": "test-1"
        })
        self.assertEqual(self.mocks["log_error"].call_count, 2)
        self.assertEqual(
            self.mocks["log_error"].mock_calls[0][1],
            ("Bad format for response data: missing mandatory field",)
        )
        self.assertEqual(
            self.mocks["log_error"].mock_calls[1][1],
            ("Bad response format for a successful payment! reference: none, merchant_reference: test-1",)
        )

    def test_validate_response_no_basket(self):
        """Verify that validate_response logs the error when the basket is not found."""
        response_data = {
            "status": utils.SUCCESS_STATUS,
            "merchant_reference": "test-1",
            "fort_id": "fort-id",
        }
        self.view.payment_processor = Mock()
        with self.assertRaises(Http404):
            self.view.validate_response(response_data)
        self.mocks["verify_signature"].assert_called_once_with(
            self.view.payment_processor.response_sha_phrase,
            self.view.payment_processor.sha_method,
            response_data,
        )
        self.mocks["verify_response_format"].assert_called_once_with(response_data)
        self.mocks["log_error"].assert_called_once_with("Basket not found! merchant_reference: test-1")


class TestPayFortRedirectionResponseView(MockPatcherMixin, BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortRedirectionResponseView."""
    patching_config = {
        "get_transaction_id": ("ecommerce_payfort.utils.get_transaction_id", {
            "return_value": "the-transaction-id",
        }),
        "validate_response": ("ecommerce_payfort.views.PayFortRedirectionResponseView.validate_response", {}),
        "save_response": ("ecommerce_payfort.views.PayFortRedirectionResponseView.save_payment_processor_response", {
            "return_value": Mock(transaction_id="the-transaction-id"),
        }),
        "log_error": ("ecommerce_payfort.views.PayFortRedirectionResponseView.log_error", {}),
    }

    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.data = {
            "status": utils.SUCCESS_STATUS,
            "merchant_reference": "test-1",
            "response_code": "00",
        }
        self.url = reverse("payfort:response")

    def test_retry_settings(self):
        """Verify that the retry settings are reasonable."""
        self.assertTrue(9 < views.PayFortRedirectionResponseView.MAX_ATTEMPTS < 30)
        self.assertTrue(1000 < views.PayFortRedirectionResponseView.WAIT_TIME < 10000)

    def test_post_success(self):
        """Verify that the POST method works."""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payfort_payment/wait_feedback.html")
        self.data.update({
            "ecommerce_transaction_id": "the-transaction-id",
            "ecommerce_error_url": reverse(
                'payfort:handle-internal-error',
                args=["the-transaction-id"]
            ),
            "ecommerce_status_url": reverse("payfort:status"),
            "ecommerce_max_attempts": views.PayFortRedirectionResponseView.MAX_ATTEMPTS,
            "ecommerce_wait_time": views.PayFortRedirectionResponseView.WAIT_TIME,
        })
        for key, value in self.data.items():
            self.assertEqual(response.context[key], value)

    def test_post_bad_signature(self):
        """Verify that the POST method does not save the response when the signature is bad."""
        self.mocks["validate_response"].side_effect = utils.PayFortBadSignatureException(
            f"Signature verification failed for response data: {self.data}",
        )
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 404)
        self.mocks["save_response"].assert_not_called()

    def test_post_internal_error(self):
        """Verify that the POST method saves the response when response validation fails."""
        self.mocks["validate_response"].side_effect = utils.PayFortException("something went wrong")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse(
            'payfort:handle-internal-error',
            args=[utils.get_transaction_id(self.data)]
        ))
        self.mocks["save_response"].assert_called_once_with(self.data)

    def test_post_bad_data(self):
        """Verify that the POST method saves the response when response validation fails because of bad format."""
        self.mocks["validate_response"].side_effect = Http404()
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 404)
        self.mocks["save_response"].assert_called_once_with(self.data)

    def test_post_status_failed(self):
        """Verify that the POST method logs an error and redirect to payment_error when the payment is failed."""
        self.data["status"] = "99"
        self.data["response_code"] = "99"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payment_error"))
        self.mocks["save_response"].assert_called_once_with(self.data)
        self.mocks["log_error"].assert_called_once_with(
            "Payfort payment failed! merchant_reference: test-1. response_code: 99"
        )


class TestPayFortStatusView(MockPatcherMixin, BaseTests):  # pylint: disable=too-many-ancestors
    """Test the PayFortStatusView."""
    patching_config = {
        "basket": ("ecommerce_payfort.views.PayFortStatusView.basket", {
            "return_value": None,
            "new_callable": PropertyMock,
        }),
    }

    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.url = reverse("payfort:status")

    def test_post_invalid_basket(self):
        """Verify that the POST method returns 404 when the basket is not found."""
        self.mocks["basket"].return_value = None
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)

    def test_post_frozen_basket(self):
        """Verify that the POST method returns 204 when the basket is still frozen."""
        self.mocks["basket"].return_value = Mock(status=views.Basket.FROZEN)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 204)

    def test_post_not_frozen_not_submitted_basket(self):
        """Verify that the POST method returns 404 when the basket is neither frozen nor submitted."""
        self.mocks["basket"].return_value = Mock(status="something-else")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)

    def test_post_submitted_basket(self):
        """Verify that the POST method returns 200 and the receipt_url when the basket is submitted."""
        self.mocks["basket"].return_value = Mock(status=views.Basket.SUBMITTED)
        with patch("ecommerce_payfort.views.get_receipt_page_url", return_value="a-url-to-the-receipt"):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8")), {
            "receipt_url": "a-url-to-the-receipt",
        })


@ddt.ddt
class TestPayFortFeedbackView(MockPatcherMixin, BaseTests, unittest.TestCase):  # pylint: disable=too-many-ancestors
    """Test the PayFortFeedbackView."""
    patching_config = {
        "validate_response": ("ecommerce_payfort.views.PayFortFeedbackView.validate_response", {}),
        "save_response": ("ecommerce_payfort.views.PayFortFeedbackView.save_payment_processor_response", {
            "return_value": Mock(id=18, transaction_id="the-transaction-id"),
        }),
        "log_error": ("ecommerce_payfort.views.PayFortFeedbackView.log_error", {}),
        "handle_payment": ("ecommerce_payfort.views.PayFortFeedbackView.handle_payment", {}),
        "create_order": ("ecommerce_payfort.views.PayFortFeedbackView.create_order", {}),
        "basket": ("ecommerce_payfort.views.PayFortFeedbackView.basket", {
            "return_value": None,
            "new_callable": PropertyMock,
        }),
    }

    def setUp(self):
        """Set up the test."""
        super().setUp()
        self.url = reverse("payfort:feedback")
        self.data = {
            "status": utils.SUCCESS_STATUS,
            "merchant_reference": "test-1",
            "response_code": "00",
        }

    def test_post_successful_payment(self):
        """Verify that the POST method works."""
        class IsWSGIRequest:  # pylint: disable=too-few-public-methods
            """Helper class to check if an object is a WSGIRequest."""
            def __eq__(self, other):
                """Check if the object is a WSGIRequest."""
                return isinstance(other, WSGIRequest)

        basket = Mock()
        self.mocks["basket"].return_value = basket
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.mocks["save_response"].assert_called_once_with(self.data)
        self.mocks["handle_payment"].assert_called_once_with(
            {'status': '14', 'merchant_reference': 'test-1', 'response_code': '00'},
            basket
        )
        self.mocks["create_order"].assert_called_once_with(IsWSGIRequest(), basket)

    def _verify_save_with_200_response(self, response):
        """Helper method to verify the save_response is called and a 200 is returned."""
        self.assertEqual(response.status_code, 200)
        self.mocks["save_response"].assert_called_once_with(self.data)
        self.mocks["handle_payment"].assert_not_called()
        self.mocks["create_order"].assert_not_called()

    def test_post_failed_payment(self):
        """Verify that the POST method works."""
        self.data["status"] = "99"
        response = self.client.post(self.url, self.data)
        self._verify_save_with_200_response(response)
        self.mocks["log_error"].assert_called_once_with(
            "Payfort payment failed! merchant_reference: test-1. response_code: 00"
        )

    def test_post_bad_signature(self):
        """Verify that the POST method does not save the response when the signature is bad."""
        self.mocks["validate_response"].side_effect = utils.PayFortBadSignatureException(
            f"Signature verification failed for response data: {self.data}",
        )
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 404)
        self.mocks["save_response"].assert_not_called()

    @ddt.data(utils.PayFortException, Http404)
    def test_post_other_errors(self, effect):
        """
        Verify that the POST method saves the response when response validation fails for any reason other
        than a bad signature.
        """
        self.mocks["validate_response"].side_effect = effect
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 404)
        self.mocks["save_response"].assert_called_once_with(self.data)

    def test_post_process_exception(self):
        """Verify that the POST method logs the exception when handle_payment fails."""
        self.mocks["basket"].return_value = Mock(id=7)
        self.mocks["handle_payment"].side_effect = Exception("Test exception")
        with patch("ecommerce_payfort.views.logger.exception") as mock_log_error:
            response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 422)
        mock_log_error.assert_called_once_with(
            "Processing payment for basket [%d] failed! The payment was successfully processed by PayFort. "
            "Response was recorded in entry no. (%d: %s). Exception: %s: %s",
            7, 18, "the-transaction-id", "Exception", "Test exception"
        )

    def test_already_processed_payment(self):
        """Verify that the POST method returns 200 when the payment is already processed."""
        self.mocks["basket"].return_value = Mock(status=views.Basket.SUBMITTED)
        response = self.client.post(self.url, self.data)
        self._verify_save_with_200_response(response)

    def test_notification_view(self):
        """Verify that the notification PayFortNotificationView view works is derived from feedback view."""
        self.assertTrue(issubclass(views.PayFortNotificationView, views.PayFortFeedbackView))
