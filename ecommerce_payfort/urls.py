"""Defines the URL routes for the payfort app."""
from django.urls import re_path

from .views import (
    PayFortFeedbackView,
    PayFortPaymentHandleFormatErrorView,
    PayFortPaymentHandleInternalErrorView,
    PayFortPaymentRedirectView,
    PayFortRedirectionResponseView,
    PayFortStatusView,
)

app_name = 'payfort'

urlpatterns = [
    re_path(r'^pay/$', PayFortPaymentRedirectView.as_view(), name='form'),
    re_path(r'^response/$', PayFortRedirectionResponseView.as_view(), name='response'),
    re_path(r'^feedback/$', PayFortFeedbackView.as_view(), name='feedback'),
    re_path(r'^status/$', PayFortStatusView.as_view(), name='status'),

    re_path(
        r'^handle_internal_error/(.+)/$',
        PayFortPaymentHandleInternalErrorView.as_view(),
        name='handle-internal-error'
    ),
    re_path(
        r'^handle_format_error/(.+)/$',
        PayFortPaymentHandleFormatErrorView.as_view(),
        name='handle-format-error'
    ),
]
