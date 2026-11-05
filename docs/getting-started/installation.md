# Installation

!!! tip "Prerequisites"
    **Python:** `3.12+` (3.13 recommended), **Ansible Core:** `2.18+`, **Router:** gRPC server enabled (see [Quick Start](quick-start.md))

    The Ansible controller must reach the gRPC port of the routers (often `57400`).
    Ansible controllers run on Linux and macOS. On Windows, use WSL.

## External dependencies

The collection needs these Python packages on the Ansible controller:

| Package | Version | Purpose |
| --- | --- | --- |
| [grpcio](https://pypi.org/project/grpcio/) | `>=1.59.0,<2` | gRPC transport |
| [protobuf](https://pypi.org/project/protobuf/) | `>=3.20.3,<8` (`>=5.29.0` on Python 3.14) | gNMI, gNOI and gNSI messages |
| [PyYAML](https://pypi.org/project/PyYAML/) | `>=6.0` | Request files, also required by Ansible |

!!! warning "Not installed by ansible-galaxy"
    `ansible-galaxy collection install` installs Ansible content only. Python packages must be installed with `pip` into the same Python environment that runs Ansible. If they are missing, the connection plugin fails with a message that names the `pip install` command to run.

The Python code generated from the OpenConfig protobuf files is part of the released collection, so no protobuf compiler is needed to use it.

## Option 1: Ansible environment (recommended)

This recipe builds a self-contained Ansible environment in a Python virtual environment, so the Python dependencies of the collection do not conflict with system packages.

### Step 1: Create and activate a virtual environment

```bash
python3 -m venv ansible-env
source ansible-env/bin/activate
```

### Step 2: Install Ansible and the Python dependencies

```bash
pip install --upgrade pip
pip install 'ansible-core>=2.18' 'grpcio>=1.59.0,<2' 'protobuf>=5.29.0,<8' 'PyYAML>=6.0'
```

### Step 3: Install the collection

/// tab | Ansible Galaxy
```bash
ansible-galaxy collection install nokia.openconfig --upgrade
```

Pre-release versions are only installed when requested, either with `--pre` or with an explicit version such as `nokia.openconfig:==2.0.2`.
///
/// tab | GitHub Release
Each [GitHub release](https://github.com/nokia-steward/openconfig-ansible-integration/releases) has the collection tarball attached, the same artifact that is published on Galaxy:

```bash
VERSION=2.0.2
curl -LO https://github.com/nokia-steward/openconfig-ansible-integration/releases/download/${VERSION}/nokia-openconfig-${VERSION}.tar.gz
ansible-galaxy collection install nokia-openconfig-${VERSION}.tar.gz --force
```
///

The collection ships its `requirements.txt`. To install exactly the Python dependencies it declares, run this after the collection install:

```bash
pip install -r ~/.ansible/collections/ansible_collections/nokia/openconfig/requirements.txt
```

## Option 2: Execution environment

For [AWX, Ansible Automation Platform](https://docs.ansible.com/automation-controller/latest/html/userguide/execution_environments.html) or [ansible-navigator](https://ansible.readthedocs.io/projects/navigator/), build an execution environment with [ansible-builder](https://ansible.readthedocs.io/projects/builder/). The collection declares its Python dependencies in `meta/execution-environment.yml`, so `ansible-builder` installs them into the image:

```yaml
# execution-environment.yml
version: 3
dependencies:
  galaxy:
    collections:
      - name: nokia.openconfig
```

```bash
ansible-builder build --tag openconfig-ee
```

## Option 3: Development environment

To contribute or to test unreleased changes, build the collection from source. This needs the development requirements, including the pinned protobuf compiler that `tools/build_openconfig_protos.sh` runs with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/nokia-steward/openconfig-ansible-integration.git
cd openconfig-ansible-integration
python3 -m venv .venv
source .venv/bin/activate
make install-dev                    # pip, setuptools, wheel and requirements-dev.txt
tools/build_openconfig_protos.sh    # generate the Python protobuf modules
ansible-galaxy collection install . --force
```

See the [Developer Guide](../guides/developer-guide.md) for tests and documentation builds.

## Verify the installation

```bash
# List installed collections
ansible-galaxy collection list nokia.openconfig

# Confirm that the Python dependencies import
python -c 'import grpc, google.protobuf; print(grpc.__version__, google.protobuf.__version__)'

# Show the plugin and module documentation
ansible-doc -t connection nokia.openconfig.grpc
ansible-doc nokia.openconfig.gnmi_get
```

!!! success "Installation complete"
    Continue with the [Quick Start](quick-start.md) to prepare the router and run a first gNMI Get. The shipped playbooks are listed with `ls ~/.ansible/collections/ansible_collections/nokia/openconfig/playbooks`, see [Examples](../examples.md#shipped-playbooks).
