"""URLS for testing the ecommerce_payfort app."""

from django.urls import include
from django.conf.urls import url

from django.http import JsonResponse


def dummy_view(request):
    return JsonResponse({'message': 'This is a dummy view for testing purposes.'})


# include the original urls
urlpatterns = [
    url(r'^payfort/', include('ecommerce_payfort.urls')),
    url(r'^login/', dummy_view),
    url(r'', include('ecommerce.urls')),
]
