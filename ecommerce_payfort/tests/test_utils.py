"""Tests for payfort_utils.py"""
from unittest.mock import Mock, patch
import pytest

from ecommerce_payfort import utils
from ecommerce_payfort.utils import verify_param as original_verify_param


class MockBasket:  # pylint: disable=too-few-public-methods
    """Mocked Basket class."""
    class Product:  # pylint: disable=too-few-public-methods
        """Mocked Product class."""
        def __init__(self, course_key=None, title=None, parent=None):
            if course_key:
                self.course = Mock(id=course_key)
            else:
                self.course = None
            self.title = title
            self.parent = parent

    class Line:  # pylint: disable=too-few-public-methods
        """Mocked Line class."""
        def __init__(self, product, quantity=1, price_currency=None):
            self.product = product
            self.quantity = quantity
            self.price_currency = price_currency

    class Owner:  # pylint: disable=too-few-public-methods
        """Mocked Owner class."""
        def __init__(self):
            """Initialize the owner."""
            self.email = "test@example.com"
            self.the_full_name = "Test User"

        def get_full_name(self):
            """Return the full name of the owner."""
            return self.the_full_name

    def __init__(self):
        """Initialize the basket."""
        self.id = 1  # pylint: disable=invalid-name
        self.owner = self.Owner()
        self.owner_id = 77
        self.total_incl_tax = 98.765
        self.internal_lines = [
            self.Line(self.Product(course_key="course-v1:C1+CC1+2024")),
            self.Line(self.Product(course_key="course-v1:C2+CC2+2024"), price_currency="SAR"),
        ]
        self.all_lines = lambda: self.internal_lines


def mocked_verify_param_basket(param, param_name, required_type):
    """Mocked verify_param function."""
    if required_type == utils.Basket:
        return
    original_verify_param(param, param_name, required_type)


@pytest.fixture
def mocked_basket():
    """Create a basket for testing."""
    basket = MockBasket()
    with patch("ecommerce_payfort.utils.verify_param", side_effect=mocked_verify_param_basket):
        yield basket


@pytest.fixture
def valid_response_data():
    """Return valid response data."""
    return {
        "merchant_reference": "1-2-1",
        "command": "PURCHASE",
        "merchant_identifier": "mid123",
        "amount": "2000",
        "currency": "SAR",
        "response_code": "200",
        "signature": "6eaf677bcdea16fc186dfdbf405ecc6f472094dff73ce699cc3afedc376a81d7",
        "status": "14",
        "eci": "eci-value",
        "fort_id": "fort-id-value",
    }


@pytest.mark.parametrize(
    "text_to_sanitize, valid_pattern, expected_result",
    [
        ("", "", ""),
        (None, None, ""),
        ("whatever", None, ""),
        ("whatever", "", ""),
        (
            "Some text with $ sign, a plus + and numbers like 123 and a dash -!!",
            r"[^A-Za-z0-9 !]",
            "Some text with _ sign_ a plus _ and numbers like 123 and a dash _!!",
        ),
    ]
)
def test_sanitize_text_defaults(text_to_sanitize, valid_pattern, expected_result):
    """
    Verify that the text is sanitized correctly using sanitize_text using default replacement and with no max_length.
    """
    assert utils.sanitize_text(text_to_sanitize, valid_pattern) == expected_result


@pytest.mark.parametrize(
    "max_length, expected_result",
    [
        (-1, "Some text with _ sign and numbers like 123 and a dash _!!"),
        (0, "Some text with _ sign and numbers like 123 and a dash _!!"),
        (20, "Some text with _ ..."),
    ]
)
def test_sanitize_text_max_length(max_length, expected_result):
    """Verify that the text is sanitized correctly using sanitize_text with a max_length."""
    assert utils.sanitize_text(
        "Some text with $ sign and numbers like 123 and a dash -!!",
        r"[^A-Za-z0-9 !\.]",
        max_length
    ) == expected_result


def test_sanitize_text_max_length_dots_not_allowed():
    """Verify that the text is sanitized correctly using sanitize_text with a max_length."""
    assert utils.sanitize_text(
        "Some text with $ sign and numbers like 123 and a dash -!!",
        r"[^A-Za-z0-9 !]",
        20
    ) == "Some text with _ sig"


def test_verify_param():
    """Verify that verify_param raises an exception if the parameter is None or not of the required type."""
    with pytest.raises(utils.PayFortException) as exc:
        utils.verify_param(None, "param", str)
    assert "verify_param failed: param is required and must be (str), but got (NoneType)" in str(exc.value)
    with pytest.raises(utils.PayFortException) as exc:
        utils.verify_param("param", "param", int)
    assert "verify_param failed: param is required and must be (int), but got (str)" in str(exc.value)


def test_get_amount(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_amount returns the amount of the basket."""
    assert utils.get_amount(mocked_basket) == 9876


def test_get_currency(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_currency returns the currency of the basket."""
    assert utils.get_currency(mocked_basket) == "SAR"


def test_get_currency_bad_one(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_currency raises an exception if the currency is not supported."""
    mocked_basket.internal_lines.append(
        mocked_basket.Line(mocked_basket.Product("course-v1:C1+CC1+2024"), price_currency="USD")
    )
    with pytest.raises(utils.PayFortException) as exc:
        utils.get_currency(mocked_basket)
    assert "Currency not supported: USD" in str(exc)


def test_get_customer_email(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_customer_email returns the email of the basket owner."""
    assert utils.get_customer_email(mocked_basket) == "test@example.com"


def test_get_customer_name(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_customer_name returns the name of the basket owner."""
    assert utils.get_customer_name(mocked_basket) == "Test User"


def test_get_customer_name_sanitized(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_customer_name returns the name of the basket owner after sanitizing it."""
    mocked_basket.owner.the_full_name = "Good _\\/-.' Bad!+%^*()[@+123]<> Arabic عربي"
    assert utils.get_customer_name(mocked_basket) == "Good _\\/-.' Bad________________ Arabic ____"


@pytest.mark.parametrize(
    "lang_code, expected_result",
    [
        ("ar", "ar"),
        ("en", "en"),
        ("AR", "ar"),
        ("Ar", "ar"),
        ("ar-SA", "ar"),
    ]
)
def test_get_language(lang_code, expected_result):
    """Verify that get_language returns the default language if the request has no language."""
    request = Mock(LANGUAGE_CODE=lang_code)
    assert utils.get_language(request) == expected_result


def test_get_language_no_request():
    """Verify that get_language returns the default language if the request is None."""
    assert utils.get_language(None) == "en"


def test_get_language_no_language():
    """Verify that get_language returns the default language if the request has no language."""
    request = Mock()
    delattr(request, "LANGUAGE_CODE")  # pylint: disable=literal-used-as-attribute
    assert not hasattr(request, "LANGUAGE_CODE")
    assert utils.get_language(request) == "en"


@pytest.mark.parametrize(
    "lang_code",
    [
        "bad",
        "fr",
        "bad-bb",
        "fr-fr",
    ]
)
def test_get_language_bad_language(lang_code):
    """Verify that get_language returns the default language if the request has anything other than en or ar."""
    request = Mock(LANGUAGE_CODE=lang_code)
    assert utils.get_language(request) == "en"


def test_get_merchant_reference(mocked_basket):  # pylint: disable=redefined-outer-name
    """Verify that get_merchant_reference returns a valid merchant reference."""
    assert utils.get_merchant_reference(26, mocked_basket) == "26-77-1"


@pytest.mark.parametrize(
    "self_key, self_title, parent_key, parent_title, expected_with_parent, expected_without_parent",
    [
        (True, True, True, True, "self_key", "self_key"),
        (True, True, True, False, "self_key", "self_key"),
        (True, True, False, True, "self_key", "self_key"),
        (True, True, False, False, "self_key", "self_key"),
        (True, False, True, True, "self_key", "self_key"),
        (True, False, True, False, "self_key", "self_key"),
        (True, False, False, True, "self_key", "self_key"),
        (True, False, False, False, "self_key", "self_key"),
        (False, True, True, True, "parent_key", "self_title"),
        (False, True, True, False, "parent_key", "self_title"),
        (False, True, False, True, "self_title", "self_title"),
        (False, True, False, False, "self_title", "self_title"),
        (False, False, True, True, "parent_key", "-"),
        (False, False, True, False, "parent_key", "-"),
        (False, False, False, True, "parent_title", "-"),
        (False, False, False, False, "-", "-"),
    ]
)
def test_get_order_description(
        mocked_basket, self_key, self_title, parent_key, parent_title, expected_with_parent, expected_without_parent
):  # pylint: disable=redefined-outer-name, too-many-arguments
    """
    Verify that get_order_description returns a valid order description from the related fields:
    - product course_key
    - if no course in the product; then parent's product course_key
    - if no course in the parent product; then product title
    - if no title in the product; then parent's product title
    """
    parent = mocked_basket.Product(
        course_key="parent_key" if parent_key else None,
        title="parent_title" if parent_title else None
    )
    product = mocked_basket.Product(
        course_key="self_key" if self_key else None,
        title="self_title" if self_title else None,
    )

    mocked_basket.internal_lines.append(mocked_basket.Line(product, quantity=2))
    assert utils.get_order_description(
        mocked_basket
    ) == f"1 X course-v1:C1_CC1_2024 // 1 X course-v1:C2_CC2_2024 // 2 X {expected_without_parent}"

    product.parent = parent
    assert utils.get_order_description(
        mocked_basket
    ) == f"1 X course-v1:C1_CC1_2024 // 1 X course-v1:C2_CC2_2024 // 2 X {expected_with_parent}"


def test_get_signature():
    """Verify that get_signature returns a valid signature."""
    assert utils.get_signature(
        "secret!", "SHA-256", {"param1": "value1", "param2": "value2"}
    ) == "811171c0e6a56ed10e69f0954a20aeeef71b4003303165ae16e9e02d7d659d73"


def test_get_signature_bad_method():
    """Verify that get_signature raises an exception if the method is not supported."""
    with pytest.raises(utils.PayFortException) as exc:
        utils.get_signature("any", "bad_method", {"param1": "value1", "param2": "value2"})
    assert "Unsupported SHA method: bad_method" in str(exc)


@pytest.mark.parametrize(
    "response_data, expected_result",
    [
        ((None, None), "none-none"),
        (("eci-value", None), "eci-value-none"),
        ((None, "fort-id-value"), "none-fort-id-value"),
        (("", ""), "none-none"),
        (("eci-value", ""), "eci-value-none"),
        (("", "fort-id-value"), "none-fort-id-value"),
        (("eci-value", "fort-id-value"), "eci-value-fort-id-value"),
        (("absence", "fort-id-value"), "none-fort-id-value"),
        (("eci-value", "absence"), "eci-value-none"),
        (("absence", "absence"), "none-none"),
    ]
)
def test_get_transaction_id(response_data, expected_result):
    """Verify that get_transaction_id returns a valid transaction ID."""
    data = {"eci": response_data[0], "fort_id": response_data[1]}
    if response_data[0] == "absence":
        data.pop("eci")
    if response_data[1] == "absence":
        data.pop("fort_id")
    assert utils.get_transaction_id(data) == expected_result


def test_verify_response_format(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_response_format returns successfully if the response format is valid."""
    utils.verify_response_format(valid_response_data)


def test_verify_response_format_guard(valid_response_data):  # pylint: disable=redefined-outer-name
    """Protect MANDATORY_RESPONSE_FIELDS from being changed by mistake."""
    assert utils.MANDATORY_RESPONSE_FIELDS == [
        "merchant_reference", "command", "merchant_identifier", "amount",
        "currency", "response_code", "signature", "status",
    ]
    for field in utils.MANDATORY_RESPONSE_FIELDS:
        assert field in valid_response_data


def test_verify_response_format_missing(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_response_format raises an exception if a mandatory field is missing."""
    for field in utils.MANDATORY_RESPONSE_FIELDS:
        data = valid_response_data.copy()
        data.pop(field)
        with pytest.raises(utils.PayFortException) as exc:
            utils.verify_response_format(data)
        assert f"Missing field in response: {field}" in str(exc)


def test_verify_response_format_not_string(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_response_format raises an exception if a mandatory field is missing."""
    for field in utils.MANDATORY_RESPONSE_FIELDS:
        data = valid_response_data.copy()
        data.update({field: 123})
        with pytest.raises(utils.PayFortException) as exc:
            utils.verify_response_format(data)
        assert f"Invalid field type in response: {field}. Should be <str>, but got <int>" in str(exc)


@pytest.mark.parametrize(
    "field, value, expected_error_msg",
    [
        ("amount", "abc", "Invalid amount in response (not a positive integer): abc"),
        ("amount", "1.2", "Invalid amount in response (not a positive integer): 1.2"),
        ("amount", "-1", "Invalid amount in response (not a positive integer): -1"),
        ("currency", "USD", "Invalid currency in response: USD"),
        ("command", "AUTHORIZATION", "Invalid command in response: AUTHORIZATION"),
        ("merchant_reference", "1-2-3-4", "Invalid merchant_reference in response: 1-2-3-4"),
        ("eci", None, "Unexpected successful payment that lacks eci or fort_id"),
        ("fort_id", None, "Unexpected successful payment that lacks eci or fort_id"),
    ]
)
def test_verify_response_format_bad(
        valid_response_data, field, value, expected_error_msg
):  # pylint: disable=redefined-outer-name
    """Verify that verify_response_format returns successfully if the response format is valid."""
    valid_response_data[field] = value
    with pytest.raises(utils.PayFortException) as exc:
        utils.verify_response_format(valid_response_data)
    assert expected_error_msg in str(exc)


def test_verify_signature(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_signature returns successfully if the signature is valid."""
    utils.verify_signature("secret@res", "SHA-256", valid_response_data)


def test_verify_signature_invalid(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_signature raises an exception if the signature is invalid."""
    valid_response_data["signature"] = "invalid_signature"

    with pytest.raises(utils.PayFortBadSignatureException) as exc:
        utils.verify_signature("secret@res", "SHA-256", valid_response_data)
    assert "Response signature mismatch" in str(exc)


def test_verify_signature_missing(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_signature raises an exception if the signature is missing."""
    valid_response_data.pop("signature")

    with pytest.raises(utils.PayFortBadSignatureException) as exc:
        utils.verify_signature("secret@res", "SHA-256", valid_response_data)
    assert "Signature not found!" in str(exc)


def test_verify_signature_bad_method(valid_response_data):  # pylint: disable=redefined-outer-name
    """Verify that verify_signature raises an exception if the method is not supported."""
    with pytest.raises(utils.PayFortException) as exc:
        utils.verify_signature("secret@res", "bad_method", valid_response_data)
    assert "Unsupported SHA method: bad_method" in str(exc)


def test_get_ip_address_no_request():
    """Verify that get_ip_address returns a valid IP address when the request is None."""
    assert utils.get_ip_address(None) == ""


def test_get_ip_address_with_proxy():
    """Verify that get_ip_address returns a valid IP address when a proxy is used."""
    request = Mock(META={
        "HTTP_X_FORWARDED_FOR": "1.1.1.1, 2.2.2.2, 3.3.3.3",
        "REMOTE_ADDR": "should be ignored",
    })
    assert utils.get_ip_address(request) == "1.1.1.1"


def test_get_ip_address_no_proxy():
    """Verify that get_ip_address returns a valid IP address when no proxy is used."""
    request = Mock(META={
        "REMOTE_ADDR": " 4.4.4.4 ",
    })
    assert utils.get_ip_address(request) == "4.4.4.4"
