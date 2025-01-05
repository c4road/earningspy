.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -fr .pytest_cache

lint: ## check style with flake8
	flake8 impyrial tests

pytest-test: ## run tests quickly with the default Python
	pytest

tox-test: ## run tests on every Python version with tox
	tox

twine-upload: dist ## package and upload a release
	twine upload dist/*


build-package: clean ## builds source and wheel package
	@echo "Building version $(VERSION)"
	VERSION=$(VERSION) python setup.py bdist_wheel
	# python setup.py sdist
	python setup.py bdist_wheel --version $(VERSION)
	ls -l dist

aws-token:  ## fetch aws codeartifact token
	aws codeartifact get-authorization-token --domain earningspy --domain-owner 923699018646 --query authorizationToken

aws-assume:  ## assume project role to execute aws cli commands on resources
	export AWS_VAULT=
	aws-vault exec earningspy

aws-login:  ## enable pip to use codeartifact repo, no need to fetch token first. make changes in pip.conf
	aws codeartifact login --tool pip --repository EarningSpy --domain earningspy --domain-owner 923699018646 --region us-east-1
	cat ~/.config/pip/pip.conf

aws-upload:  ## upload wheel to codeartifact repo
	twine upload --repository codeartifact --verbose dist/$(WHEEL)

aws-delete-package:
	aws codeartifact delete-package-versions \
		--domain earningspy \
		--domain-owner 923699018646 \
		--repository EarningSpy \
		--format pypi \
		--package earningspy \
		--versions $(VERSION)

aws-open-console:  ## open AWS console as project user (not root)
	open https://923699018646.signin.aws.amazon.com/console

aws-open-root-console:  ## open AWS console to login as root
	open https://us-east-1.console.aws.amazon.com/console/home?nc2=h_ct&src=header-signin&region=us-east-1

aws-get-repository:  ## Fetch codeartifact repo url
	aws codeartifact get-repository-endpoint --domain earningspy --repository EarningSpy --format pypi

