.PHONY: compile_messages download_ecommerce_requirements


compile_messages:
	msgfmt--check --strict --output-file payfort/locale/ar/LC_MESSAGES/django.mo payfort/locale/ar/LC_MESSAGES/django.po

OPENEDX_RELEASE ?= maple.master
download_ecommerce_requirements:
	curl -L https://github.com/openedx/ecommerce/raw/open-release/$(OPENEDX_RELEASE)/requirements/test.txt -o requirements/ecommerce-$(OPENEDX_RELEASE).txt
	sed -i '1i# This file has been downloaded by "make download_ecommerce_requirements"' requirements/ecommerce-$(OPENEDX_RELEASE).txt
	sed -i '2i# Every thing else below this line is a copy from the openedx/ecommerce test.txt requirements file' requirements/ecommerce-$(OPENEDX_RELEASE).txt


tests:  ## Run unit and integration tests
	tox -e py38-tests

quality:  ## Run code quality checks
	tox -e py38-quality

translation.requirements:
	pip install -r requirements/translation.txt

translation.extract:
	i18n_tool extract --no-segment

translation.compile:
	i18n_tool generate
