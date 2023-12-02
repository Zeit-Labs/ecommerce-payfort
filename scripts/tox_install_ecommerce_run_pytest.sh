#!/usr/bin/env bash
# Clone the openedx/ecommerce and install the ecommerce-payfort package and run tests
# This is refactored form the following CircleCI config file:
#   - https://github.com/open-craft/ecommerce-hyperpay/blob/main/.circleci/config.yml
#
#  Usage:
#
#   bash ./scripts/tox_install_ecommerce_run_pytest.sh pytest -v   # Run all tests
#
#   bash ./scripts/tox_install_ecommerce_run_pytest.sh pytest -v tests/test_utils.py  # Run a specific test
#
#

set -e

export PYTHONWARNINGS=ignore  # Suppress warnings from `openedx/ecommerce` code

pip install -e .  # Install ecommerce_payfort into the virtualenv

if [ ! -d ".tox/ecommerce-maple.master" ]; then
    git clone --single-branch --branch=open-release/maple.master --depth=1 https://github.com/openedx/ecommerce.git .tox/ecommerce-maple.master
fi

rm -rf .tox/ecommerce-maple.master/ecommerce_payfort
cat settings/payfort.py > .tox/ecommerce-maple.master/ecommerce/settings/payfort.py

cd .tox/ecommerce-maple.master/ecommerce


"$@"  # Arguments passed to this script
