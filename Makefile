.PHONY: help install-dev build-collection import-galaxy docs docs-serve test test-units test-sanity \
	test-setup test-integration-sros test-integration-srlinux install-artifact

PYTHON ?= python3
PYTHON_VERSION = $$($(PYTHON) -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
# Test inputs from .github/test-matrix.yml (SRL_VERSION and SROS_VERSION default in tests/*.clab.yml)
ANSIBLE_VERSION ?= 2.22
# The integration tests use the built artifact, installed here, not the checkout
COLLECTIONS := $(CURDIR)/.tmp/collections
JUNIT_DIR := tests/output/junit

help:
	@echo "OpenConfig Ansible collection — common tasks"
	@echo ""
	@echo "  make install-dev      Install requirements-dev.txt"
	@echo "  make build-collection Build collection tarball (protos + ansible-galaxy collection build)"
	@echo "  make import-galaxy    Run galaxy-importer on built tarball (requires build-collection)"
	@echo "  make test             The suites that need no lab (test-sanity, test-units)"
	@echo "  make docs             Generate reference + build MkDocs site (site/)"
	@echo "  make docs-serve       Serve docs at http://127.0.0.1:8000"
	@echo ""
	@echo "Test suites (.github/test-matrix.yml), JUnit in $(JUNIT_DIR):"
	@echo "  make test-setup       Install ansible-core \$$ANSIBLE_VERSION, requirements-dev.txt, protos"
	@echo "  make test-sanity      ansible-test sanity"
	@echo "  make test-units       ansible-test units and a syntax check of the shipped playbooks"
	@echo "  make test-integration-sros     Containerlab SR OS (\$$SROS_VERSION, needs an SR-SIM license)"
	@echo "  make test-integration-srlinux  Containerlab SR Linux (\$$SRL_VERSION)"

install-dev:
	$(PYTHON) -m pip install --upgrade pip setuptools wheel
	$(PYTHON) -m pip install -r requirements-dev.txt

build-collection:
	tools/build_openconfig_protos.sh
	ansible-galaxy collection build .

import-galaxy:
	@VER=$$(grep '^version:' galaxy.yml | awk '{print $$2}'); \
	ARTIFACT="nokia-openconfig-$$VER.tar.gz"; \
	test -f "$$ARTIFACT" || (echo "Artifact $$ARTIFACT not found; run make build-collection first" >&2; exit 1); \
	tools/import_galaxy.sh "$$ARTIFACT"

test: test-sanity test-units

test-setup:
	$(PYTHON) -m pip install --upgrade pip
ifeq ($(ANSIBLE_VERSION),devel)
	$(PYTHON) -m pip install -r requirements-dev.txt https://github.com/ansible/ansible/archive/devel.tar.gz
else
	$(PYTHON) -m pip install -r requirements-dev.txt "ansible-core==$(ANSIBLE_VERSION).*"
endif
	tools/build_openconfig_protos.sh

test-sanity:
	tools/build_openconfig_protos.sh
	rm -rf tests/output site
	tools/ansible_test.sh sanity --venv --python $(PYTHON_VERSION) -v --junit

test-units: install-artifact
	rm -rf tests/output site
	tools/ansible_test.sh units --venv --python $(PYTHON_VERSION) -v
	ansible-inventory -i playbooks/examples/inventory.yml --graph
	for playbook in playbooks/*.yml; do \
		ANSIBLE_COLLECTIONS_PATH=$(COLLECTIONS) ansible-playbook --syntax-check -i playbooks/examples/inventory.yml \
			"nokia.openconfig.$$(basename "$$playbook" .yml)" || exit 1; \
	done

test-integration-sros: install-artifact
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTIONS) tests/run.sh integration --topo sros.clab.yml \
		--playbooks playbooks-sros.yml --suite integration-sros

test-integration-srlinux: install-artifact
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTIONS) tests/run.sh integration --topo srlinux.clab.yml \
		--playbooks playbooks-srlinux.yml --suite integration-srlinux

install-artifact:
	tools/build_openconfig_protos.sh
	rm -rf .tmp/dist $(COLLECTIONS)
	ansible-galaxy collection build . --output-path .tmp/dist
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTIONS) \
		ansible-galaxy collection install --force -p $(COLLECTIONS) .tmp/dist/nokia-openconfig-*.tar.gz

docs:
	@echo "Generating module and connection reference..."
	$(PYTHON) tools/generate_docs.py
	mkdocs build --clean

docs-serve:
	$(PYTHON) tools/generate_docs.py
	mkdocs serve
