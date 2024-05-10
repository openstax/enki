.PHONY: help_submake
help_submake:
	@echo "make build-sdist           Build the source distribution of the content job resource"
	@echo "make build-image           Build the image according to the version number"
	@echo "make tag-latest            Tag the currently built image with latest"
	@echo "make release-latest        Release the latest tagged image to docker hub"
	@echo "make release               Release the tagged version image to docker hub"
	@echo "make test                  Run the tests"
	@echo "make lint                  Lint source and test files"

ORG_NAME := openstax
VERSION := $$(poetry version -s)
NAMESPACE := corgi-concourse-resource
BUILD_ARGS := $(BUILD_ARGS)
MAJOR := $(word 1,$(subst ., ,$(VERSION)))
MINOR := $(word 2,$(subst ., ,$(VERSION)))
MAJOR_MINOR_PATCH := $(word 1,$(subst -, ,$(VERSION)))
STATEDIR = $(PWD)/.$(NAMESPACE)-state
BINDIR = $(STATEDIR)/env/bin
PYTHON := /usr/bin/env python3

$(STATEDIR)/env/pyvenv.cfg : $(PWD)/pyproject.toml
	# Create our Python 3 virtual environment
	rm -rf $(STATEDIR)/env
	$(PYTHON) -m venv $(VENV_EXTRA_ARGS) $(STATEDIR)/env

	# Upgrade tooling requirements
	$(BINDIR)/python -m pip install --upgrade pip setuptools wheel
	$(BINDIR)/python -m pip install ".[test]"

.PHONY: build-sdist
build-sdist:
	poetry build -f sdist

.PHONY: build-image
build-image: build-sdist
	docker build $(BUILD_ARGS) -t $(ORG_NAME)/$(NAMESPACE):$(VERSION) .

.PHONY: tag-latest
tag-latest: build-image
	docker tag $(ORG_NAME)/$(NAMESPACE):$(VERSION) $(ORG_NAME)/$(NAMESPACE):latest

.PHONY: release-latest
release-latest: tag-latest
	docker push $(ORG_NAME)/$(NAMESPACE):latest

.PHONY: release
release:
	@if ! docker images $(ORG_NAME)/$(NAMESPACE) | awk '{ print $$2 }' | grep -q -F $(VERSION); then echo "$(ORG_NAME)/$(NAMESPACE) version $(VERSION) is not yet built. Please run 'make build-image'"; false; fi
	docker push $(ORG_NAME)/$(NAMESPACE):$(VERSION)

lint : $(STATEDIR)/env/pyvenv.cfg
	$(BINDIR)/python -m ruff check corgi_concourse_resource/ tests/
	$(BINDIR)/python -m ruff format --check corgi_concourse_resource/ tests/

format : $(STATEDIR)/env/pyvenv.cfg
	$(BINDIR)/python -m ruff check --fix corgi_concourse_resource/ tests/
	$(BINDIR)/python -m ruff format corgi_concourse_resource/ tests/

TEST_EXTRA_ARGS=

test : $(STATEDIR)/env/pyvenv.cfg
	$(BINDIR)/python -m pytest tests/test_resource.py --cov=corgi_concourse_resource --cov-report=term -vvv $(TEST_EXTRA_ARGS)
