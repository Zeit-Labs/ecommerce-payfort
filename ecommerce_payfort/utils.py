"""Utility functions for the Payfort payment gateway."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from oscar.apps.payment.exceptions import GatewayError
from oscar.core.loading import get_model

Basket = get_model("basket", "Basket")

MANDATORY_RESPONSE_FIELDS = [
    "merchant_reference",
    "command",
    "merchant_identifier",
    "amount",
    "currency",
    "response_code",
    "signature",
    "status",
]
MAX_ORDER_DESCRIPTION_LENGTH = 150
SUCCESS_STATUS = "14"
SUPPORTED_SHA_METHODS = {
    "SHA-256": hashlib.sha256,
    "SHA-512": hashlib.sha512,
}
VALID_CURRENCY = "SAR"
VALID_PATTERNS = {
    "order_description": r"[^A-Za-z0-9 '/\._\-#:$]",
    "customer_name": r"[^A-Za-z _\\/\-\.']",
}


class PayFortException(GatewayError):
    """PayFort exception."""


class PayFortBadSignatureException(PayFortException):
    """PayFort bad signature exception."""


def sanitize_text(
        text_to_sanitize: str, valid_pattern: str, max_length: int | None = None, replacement: str = "_"
) -> str:
    """
    Sanitize the text by replacing invalid characters with the replacement character.

    @param text_to_sanitize: The text to sanitize
    @param valid_pattern: The valid pattern to match the text against
    @param max_length: The maximum length of the sanitized text
    @param replacement: The replacement character for invalid characters
    @return: The sanitized text
    """
    if (valid_pattern or "") == "":
        return ""

    sanitized = re.sub(valid_pattern, replacement, text_to_sanitize)
    if max_length is None or max_length <= 0:
        return sanitized

    if len(sanitized) > max_length and r'\.' in valid_pattern:
        return sanitized[:max_length - 3] + "..."
    return sanitized[:max_length]


def verify_param(param: Any, param_name: str, required_type: Any):
    """
    Verify a parameter type

    @param param: The parameter to verify
    @param param_name: The name of the parameter to be used in the exception message
    @param required_type: The required type of the parameter
    """
    if param is None or not isinstance(param, required_type):
        raise PayFortException(
            f"verify_param failed: {param_name} is required and must be "
            f"({required_type.__name__}), but got ({type(param).__name__})"
        )


def get_amount(basket: Basket) -> int:
    """
    Return the amount for the given basket in the ISO 4217 currency format for SAR.

    @param basket: The basket
    @return: The amount
    """
    verify_param(basket, "basket", Basket)

    return int(round(basket.total_incl_tax * 100, 0))


def get_currency(basket: Basket) -> str:
    """
    Return the currency for the given basket.

    @param basket: The basket
    @return: The currency
    """
    verify_param(basket, "basket", Basket)

    for line in basket.all_lines():
        if line.price_currency and line.price_currency != VALID_CURRENCY:
            raise PayFortException(f"Currency not supported: {line.price_currency}")

    return VALID_CURRENCY


def get_customer_email(basket: Basket) -> str:
    """
    Return the customer email for the given basket.

    @param basket: The basket
    @return: The customer email
    """
    verify_param(basket, "basket", Basket)

    return basket.owner.email


def get_customer_name(basket: Basket) -> str:
    """
    Return the customer name for the given basket.

    @param basket: The basket
    @return: The customer name
    """
    verify_param(basket, "basket", Basket)

    return sanitize_text(
        basket.owner.get_full_name() or "Name not set",
        VALID_PATTERNS["customer_name"],
        max_length=50,
    )


def get_language(request: Any) -> str:
    """
    Return the language from the request.

    @param request: The request
    @return: The language
    """
    if request is None or not hasattr(request, "LANGUAGE_CODE"):
        return "en"
    result = request.LANGUAGE_CODE.split("-")[0].lower()

    return result if result in ("en", "ar") else "en"


def get_merchant_reference(site_id: int, basket: Basket) -> str:
    """
    Return the merchant reference for the given basket.

    @param site_id: The site ID
    @param basket: The basket
    @return: The merchant reference
    """
    verify_param(site_id, "site_id", int)
    verify_param(basket, "basket", Basket)

    return f"{site_id}-{basket.owner_id}-{basket.id}"


def get_order_description(basket: Basket) -> str:
    """
    Return the order description for the given basket.

    @param basket: The basket
    @return: The order description
    """
    def _get_course_id(product: Any) -> str | None:
        """Return the course ID."""
        if product.course:
            return product.course.id
        if product.parent and product.parent.course:
            return product.parent.course.id

        return None

    def _get_product_title(product: Any) -> str | None:
        """Return the product title."""
        result = (product.title or "").strip()
        if result != "":
            return result

        if not product.parent:
            return None

        return (product.parent.title or "").strip()

    def _get_product_description(product: Any) -> str:
        """Return the product description."""
        result = _get_course_id(product)
        if result is None:
            result = _get_product_title(product)

        return result or "-"

    verify_param(basket, "basket", Basket)

    description = ""
    max_index = len(basket.all_lines()) - 1
    for index, line in enumerate(basket.all_lines()):
        description += f"{line.quantity} X {_get_product_description(line.product).replace(';', '_') or '-'}"
        if index < max_index:
            description += " // "

    return sanitize_text(
        description,
        VALID_PATTERNS["order_description"],
        max_length=MAX_ORDER_DESCRIPTION_LENGTH
    )


def get_signature(sha_phrase: str, sha_method: str, transaction_parameters: dict) -> str:
    """
    Return the signature for the given transaction parameters.

    @param sha_phrase: The SHA phrase
    @param sha_method: The SHA method
    @param transaction_parameters: The transaction parameters
    @return: The calculated signature
    """
    verify_param(sha_phrase, "sha_phrase", str)
    verify_param(sha_method, "sha_method", str)
    verify_param(transaction_parameters, "transaction_parameters", dict)

    sha_method_fnc = SUPPORTED_SHA_METHODS.get(sha_method)
    if sha_method_fnc is None:
        raise PayFortException(f"Unsupported SHA method: {sha_method}")

    sorted_keys = sorted(transaction_parameters, key=lambda arg: arg.lower())
    sorted_dict = {key: transaction_parameters[key] for key in sorted_keys}

    result_string = f"{sha_phrase}{''.join(f'{key}={value}' for key, value in sorted_dict.items())}{sha_phrase}"

    return sha_method_fnc(result_string.encode()).hexdigest()


def get_transaction_id(response_data: dict) -> str:
    """
    Return the transaction ID from the response data.

    @param response_data: The response data
    @return: The transaction ID
    """
    verify_param(response_data, "response_data", dict)

    return f"{response_data.get('eci') or 'none'}-{response_data.get('fort_id') or 'none'}"


def verify_response_format(response_data):
    """Verify the format of the response from PayFort."""
    for field in MANDATORY_RESPONSE_FIELDS:
        if field not in response_data:
            raise PayFortException(f"Missing field in response: {field}")
        if not isinstance(response_data[field], str):
            raise PayFortException((
                f"Invalid field type in response: {field}. "
                f"Should be <str>, but got <{type(response_data[field]).__name__}>"
            ))

    try:
        amount = int(response_data["amount"])
        if amount < 0 or response_data["amount"] != str(amount):
            raise ValueError
    except ValueError as exc:
        raise PayFortException(
            f"Invalid amount in response (not a positive integer): {response_data['amount']}"
        ) from exc

    if response_data["currency"] != VALID_CURRENCY:
        raise PayFortException(f"Invalid currency in response: {response_data['currency']}")

    if response_data["command"] != "PURCHASE":
        raise PayFortException(f"Invalid command in response: {response_data['command']}")

    if re.fullmatch(r"\d+-\d+-\d+", response_data["merchant_reference"]) is None:
        raise PayFortException(
            f"Invalid merchant_reference in response: {response_data['merchant_reference']}"
        )

    if (
            (response_data.get("eci") is None or response_data.get("fort_id") is None) and
            response_data['status'] == SUCCESS_STATUS
    ):
        raise PayFortException(
            f"Unexpected successful payment that lacks eci or fort_id: {response_data['merchant_reference']}"
        )


def verify_signature(sha_phrase: str, sha_method: str, data: dict):
    """
    Verify the data signature.

    @param sha_phrase: The SHA phrase
    @param sha_method: The SHA method
    @param data: The response data
    """
    verify_param(data, "response_data", dict)

    sha_method_fnc = SUPPORTED_SHA_METHODS.get(sha_method)
    if sha_method_fnc is None:
        raise PayFortException(f"Unsupported SHA method: {sha_method}")

    data = data.copy()
    signature = data.pop("signature", None)
    if signature is None:
        raise PayFortBadSignatureException("Signature not found!")

    expected_signature = get_signature(
        sha_phrase,
        sha_method,
        data,
    )
    if signature != expected_signature:
        raise PayFortBadSignatureException(
            f"Response signature mismatch. merchant_reference: {data.get('merchant_reference', 'none')}"
        )


def get_ip_address(request: Any) -> str:
    """
    Return the customer IP address from the request.

    @param request: The request
    @return: The customer IP address
    """
    if request is None:
        return ""

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(",")[0]
    else:
        ip_address = request.META.get("REMOTE_ADDR")

    return (ip_address or "").strip()
