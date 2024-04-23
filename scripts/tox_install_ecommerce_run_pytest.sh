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

if [ ! -d ".tox/ecommerce-palm.master" ]; then
    git clone --single-branch --branch=open-release/palm.master --depth=1 https://github.com/openedx/ecommerce.git .tox/ecommerce-palm.master
fi

cat settings/test_settings.py > .tox/ecommerce-palm.master/ecommerce/settings/payfort.py

#rm -rf .tox/ecommerce/assets
#cp -r scripts/fake_assets/ .tox/ecommerce/assets

export tests_root_dir=$(pwd)

mkdir -p .tox/ecommerce
ln -s -f ../ecommerce-palm.master/ecommerce .tox/ecommerce/ecommerce
export PYTHONPATH="$PYTHONPATH:$tests_root_dir/.tox/ecommerce"
echo "PYTHONPATH=$PYTHONPATH"

echo "***********************************************************----"
echo "* Running command from tox file:" "$@"
echo "***********************************************************----"
eval "$@"
