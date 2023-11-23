"""
Defines the URL routes for the payfort app.
"""
from django.conf.urls import url

from .views import PayFortPaymentPageView, PayFortResponseView

urlpatterns = [
    url(r'^payment/payfort/pay/$', PayFortPaymentPageView.as_view(), name='payment-form'),
    url(r'^payment/payfort/submit/$', PayFortResponseView.as_view(), name='submit'),
    url(
        r'^payment/payfort/status/(?P<encrypted_resource_path>.+)/$',
        PayFortResponseView.as_view(),
        name='status-check'
    ),
]
