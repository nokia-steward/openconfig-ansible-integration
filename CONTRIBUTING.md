# OpenConfig Ansible Collection – Developer & Contributor Guide

Thank you for your interest in improving the **`nokia.openconfig`** Ansible collection!
This guide explains how to set up your development environment, run tests, and contribute changes — following the [Ansible Community Guidelines](https://docs.ansible.com).

---

## Overview

The `nokia.openconfig` collection provides network automation support for devices with OpenConfig gRPC services: **gNMI**, **gNOI** and **gNSI**, tested with Nokia **SR OS** and **SR Linux**.
Developers can use the included `run.sh` helper script to simplify local development, containerlab deployment, and regression testing.

---

## Prerequisites

Before contributing, ensure your environment includes:

* **Python 3.12 or newer** (3.13 recommended)
* **Ansible Core 2.18 or newer** (2.22 recommended)
* **Docker** for running SR OS and SR Linux container images
* **Access** to SR OS and SR Linux container images and a valid SR OS license file
* A Linux, macOS, or BSD-like system with common GNU tools (`bash`, `curl`, `make`, etc.)

---

## Quick Start

### 1. Set up a Python virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. Clone the repository

```bash
git clone https://github.com/nokia-steward/openconfig-ansible-integration.git
```

### 3. Build and Install collection locally

```bash
cd openconfig-ansible-integration
pip install -r requirements-dev.txt

tools/build_openconfig_protos.sh

ansible-galaxy collection install . --force
```

`tools/build_openconfig_protos.sh` compiles the gNMI, gNOI and gNSI protos in `plugins/module_utils/proto` and rewrites the generated imports. Refresh `.proto` sources from upstream with `tools/sync_openconfig_protos.sh` (gNMI, gNOI, and gNSI in one script). Run `build_openconfig_protos.sh` again whenever a `.proto` file changes. It uses [uv](https://docs.astral.sh/uv/) (part of `requirements-dev.txt`) to run a pinned, old protoc (grpcio-tools 1.47.5 on Python 3.10), so the generated code stays compatible with old and new protobuf releases. Do not regenerate with a newer grpcio-tools.

Connection unit tests use **`OpenConfigMockServer`** in `tests/unit/plugins/connection/openconfig_mock_server.py` — one in-process mock for gNMI, gNOI, and gNSI. See `test_openconfig_grpc.py`.

User documentation is built with **MkDocs** (`make docs`); the site is published to GitHub Pages from the `main` branch. Edit guides under `docs/`; module reference pages are generated from docstrings via `tools/generate_docs.py`.

### 4. Install runtime dependencies

The collection needs no other Ansible collections.

Install [containerlab](https://containerlab.dev):

```bash
bash -c "$(curl -sL https://get.containerlab.dev)"
```

### 5. Prepare images and licenses

Pull the `nokia_srsim` and `nokia_srlinux` container images, and copy a valid SR OS license file to `tests/license.txt`.


### 6. Deploy and test the example lab

```bash
cd tests
chmod +x run.sh
./run.sh deploy
```

### 7. Run all regression tests

```bash
./run.sh run --quiet --all
```

### 8. Clean up when finished

```bash
./run.sh destroy
```

---

## Coding Standards

Follow Ansible and Python best practices:

* Use the standard [Ansible module structure](https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html)
* Include `DOCUMENTATION`, `EXAMPLES`, and `RETURN` blocks in every module
* Keep `galaxy.yml` metadata accurate and up to date
* Update `CHANGELOG.md` and `README.md` for user-visible changes
* Validate your work with:

  * `./run.sh sanity` and `./run.sh units`
  * Linting and style checks
  * Unit and integration test suites

---

## Commit & Pull Request Guidelines

* Write **clear, focused commits** that explain both *what* and *why*
* Reference related issues (e.g. `Fixes #42`)
* Ensure all tests pass before requesting review
* Add or update tests for new features or bug fixes
* Maintain consistent docstrings, examples, and return schemas

A pull request can be merged only when:

* All CI checks pass successfully
* A maintainer approves the change
* The update fits the project's goals and quality standards

---

## Contributing

We welcome all contributions — from small fixes to major enhancements. Whether you're reporting a bug, improving documentation, or extending functionality, we'd love your input.

Before submitting a pull request:

* Run all tests (`./run.sh sanity` and `./run.sh units`)
* Follow [PEP 8](https://peps.python.org/pep-0008/) and Ansible plugin guidelines
* Ensure changes are documented and clearly commented
* Update or add integration tests where relevant

---

## Getting Help

If you encounter problems or need support:

**Search existing threads**
Check [open issues](https://github.com/nokia-steward/openconfig-ansible-integration/issues) to see if your topic is already covered.

**Open a new issue**

Include the following information:

* Your **OS**, **Python**, and **Ansible** versions
* The **SR OS** and **SRLinux** versions used
* A concise problem description or error log

The maintainers and community collaborators monitor these channels and respond as time permits.
