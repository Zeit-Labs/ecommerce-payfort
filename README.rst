Amazon Payment Services (PayFort) Payment Processor backend for Open edX ecommerce
==================================================================================

This application provides a custom `Open edX ecommerce <https://github.com/edx/ecommerce/>`
payment processor backend for the `Amazon Payment Services <https://paymentservices-reference.payfort.com/>`_.

Getting Started with PayFort Integration Development
####################################################

The API documentation for the PayFort payment services is available at:

- https://paymentservices-reference.payfort.com/docs/api/build/index.html

Scroll through the page, it's a very long single-page documentation.

There's no official Python SDK for PayFort. But we can use the
`PayFort PHP SDK <https://github.com/payfort/payfort-php-sdk>`_ to understand the API calls and redirect mechanism.

There's a 2016 unofficial Python SDK for PayFort: https://github.com/alisterionold/payfort-python

There's a 2018 blog documenting the integration process:

- `Integrating PayFort — we suffered so you don't have to <https://medium.com/@jaysadiq/integrating-payfort-we-suffered-so-you-dont-have-to-23a4dbdef556>`_

Testing Credit Cards
####################

When the testing account is used,
`PayFort test payment card numbers <https://paymentservices.amazon.com/docs/EN/12.html>`_ can be used.


Development and Testing
#######################

TBD: Add devstck and Tutor instructions.


To run tests locally in your machine, you need to install the following dependencies::

   $ pip install tox

Then run the all tests::

   $ make tests


Or run the unit tests only::

   $ make unit_tests

To run quality quality::

   $ make flake8


``tox`` can be used directly to run a specific, for example::

   $ tox -e py38 -- tests/unit/test_payfort_utils.py


Installation and usage
######################

* Install this repository inside the ecommerce virtualenv environment using `pip`.
* In `ecommerce.yml`, add the following settings:
  ::

     ADDL_INSTALLED_APPS:
       - payfort
     ADDL_PAYMENT_PROCESSORS:
       - 'ecommerce_payfort.processors.PayFort'
     # many other settings
     PAYMENT_PROCESSOR_CONFIG:
       <partner name>:
         payfort:
           <TBD: integration docs is coming>

* Restart the `ecommerce` service in production and the devserver in the devstack.
* In the `ecommerce` Django admin site, create waffle switches `payment_processor_active_payfort`, ` to enable the backends.
* Verify and ensure that the `enable_client_side_checkout` waffle flag is disabled for everyone.
* Once these steps are done, the `PayFort` processor backend provided by this application will be available as payment options
  during the payment flow for purchasing paid seats in courses.


Author
######

This application was developed by `ZeitLabs <https://zeitlabs.com/>`_ at the request of
`The National Learning Center <https://elc.edu.sa/>`_.

This application is released under the terms of the `AGPLv3 license <https://www.gnu.org/licenses/agpl-3.0.html>`_
and is based on the `ecommmerce-hyperpay plugin <https://github.com/open-craft/ecommerce-hyperpay>`_.
