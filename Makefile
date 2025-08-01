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

run-tests: ## run tests quickly with the default Python
	pytest --cov=earningspy --cov-report=term-missing

tox-test: ## run tests on every Python version with tox
	tox

twine-upload: dist ## package and upload a release
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*


build-package: clean ## builds source and wheel package
	@echo "Building version $(VERSION)"
	VERSION=$(VERSION) python setup.py bdist_wheel
	# python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist