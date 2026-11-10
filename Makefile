.PHONY: help install-dev build-collection import-galaxy docs docs-serve test test-units test-sanity

PYTHON ?= python3

help:
	@echo "OpenConfig Ansible collection — common tasks"
	@echo ""
	@echo "  make install-dev      Install requirements-dev.txt"
	@echo "  make build-collection Build collection tarball (protos + ansible-galaxy collection build)"
	@echo "  make import-galaxy    Run galaxy-importer on built tarball (requires build-collection)"
	@echo "  make test             Build protos and run ansible-test units (same as CI sanity-units units step)"
	@echo "  make test-units    Run unit tests only (requires protos and ansible-test)"
	@echo "  make test-sanity   Run sanity tests (requires protos and ansible-test)"
	@echo "  make docs          Generate reference + build MkDocs site (site/)"
	@echo "  make docs-serve    Serve docs at http://127.0.0.1:8000"

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

test: test-units

test-units:
	tools/build_openconfig_protos.sh
	rm -rf tests/output site
	tools/ansible_test.sh units --venv --python $$( $(PYTHON) -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' ) -v

test-sanity:
	tools/build_openconfig_protos.sh
	rm -rf tests/output site
	tools/ansible_test.sh sanity --venv --python $$( $(PYTHON) -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' ) -v

docs:
	@echo "Generating module and connection reference..."
	$(PYTHON) tools/generate_docs.py
	mkdocs build --clean

docs-serve:
	$(PYTHON) tools/generate_docs.py
	mkdocs serve
