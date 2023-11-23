import ddt
import pytest

from ecommerce.extensions.payment.tests.processors.mixins import PaymentProcessorTestCaseMixin
from ecommerce.tests.testcases import TestCase
from ecommerce_payfort.tests.mixins import PayFortMixin


@ddt.ddt
@pytest.mark.xfail
class PayFortTests(PayFortMixin, PaymentProcessorTestCaseMixin, TestCase):
    pass
