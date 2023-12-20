set -e

SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
PAYFORT_PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
ECOMMERCE_DIR="$(dirname "$PAYFORT_PACKAGE_DIR")/ecommerce"

##if [ -z "$TVM_PROJECT_ENV" ]; then
##  echo "Error: activate tvm project environment first: "
##  echo
##  echo "  $ source .tvm/bin/activate"
##  echo
##  exit 1
##fi


set -x


tutor config save \
  --set 'ECOMMERCE_EXTRA_PIP_REQUIREMENTS=["-e /openedx/ecommerce-payfort"]'

cat "$SCRIPT_DIR/docker-compose.override.yml" \
  | sed -e "s|PAYFORT_PACKAGE_DIR|${PAYFORT_PACKAGE_DIR}|g" \
  | sed -e "s|ECOMMERCE_DIR|${ECOMMERCE_DIR}|g" \
  > "$(tutor config printroot)/env/dev/docker-compose.override.yml"

pip install \
  tutor-mfe==13.0.6 \
  tutor-ecommerce==13.0.1

pip install -e discovery

tutor plugins enable ecommerce
tutor plugins enable discovery
tutor plugins enable mfe
tutor config save --set "DISCOVERY_DB_PREVIOUS_PARTNERS=false"  # NELC specific setting: https://github.com/eduNEXT/tutor-discovery/pull/1

tutor config save --set "ECOMMERCE_PAYMENT_PROCESSORS=$(cat "$SCRIPT_DIR/ecommerce-config.yml")"
tutor config save

tutor dev quickstart --non-interactive

tutor dev createuser --staff --superuser edx edx@example.com --password edx

tutor dev importdemocourse

tutor dev run ecommerce npm install
tutor dev run ecommerce ./node_modules/.bin/bower install --allow-root
tutor dev run ecommerce python3 manage.py update_assets --skip-collect
