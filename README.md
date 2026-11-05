![NOKIA](media/logo.png)

---

# Nokia OpenConfig Ansible Collection

[![CI](https://github.com/nokia-steward/openconfig-ansible-integration/actions/workflows/ci.yml/badge.svg)](https://github.com/nokia-steward/openconfig-ansible-integration/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue)](https://nokia-steward.github.io/openconfig-ansible-integration/)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Ansible](https://img.shields.io/badge/ansible--core-2.18%2B-blue)](https://docs.ansible.com/)

Ansible collection **`nokia.openconfig`** for devices that expose **OpenConfig gRPC** services: **gNMI** 0.10.0, **gNOI**, and **gNSI**, validated on Nokia **SR OS** and **SR Linux**.

---

## Requirements

- **Ansible Core** 2.18 or newer  
- **Python** 3.12 or newer on the controller  
- **Python libraries**: [grpcio](https://pypi.org/project/grpcio/) ≥ 1.59.0, [protobuf](https://pypi.org/project/protobuf/) ≥ 3.20.3 (5.29+ on Python 3.14), [PyYAML](https://pypi.org/project/PyYAML/) ≥ 6.0
- **Router**: gRPC server enabled with gNMI, gNOI and gNSI as needed

---

## Installation

```bash
pip install 'ansible-core>=2.18' 'grpcio>=1.59.0,<2' 'protobuf>=5.29.0,<8' 'PyYAML>=6.0'
ansible-galaxy collection install nokia.openconfig
```

`ansible-galaxy` does not install Python libraries; install them into the same Python environment as Ansible, preferably a virtual environment. Pre-release versions are only installed with `--pre` or an explicit version.

Building from a git checkout also requires generated protobuf modules:

```bash
pip install -r requirements-dev.txt
tools/build_openconfig_protos.sh
ansible-galaxy collection install . --force
```

---

## Quick example

```yaml
- name: gNMI get
  hosts: srlinux
  gather_facts: false
  vars:
    ansible_connection: nokia.openconfig.grpc
    ansible_port: 57400
    ansible_root_certificates_file: ./ca.pem
  tasks:
    - name: Get the system name
      nokia.openconfig.gnmi_get:
        path: [/system/name/host-name]
        type: config
      register: cfg
```

Set **`ansible_connection: nokia.openconfig.grpc`**. Module options are the request fields of the gNMI, gNOI and gNSI specifications in snake_case.

---

## Documentation

Full user documentation is published with **MkDocs** on GitHub Pages:

**https://nokia-steward.github.io/openconfig-ansible-integration/**

| Section | Description |
| --- | --- |
| [Start Here](https://nokia-steward.github.io/openconfig-ansible-integration/getting-started/start-here/) | Which module or playbook to use for a task |
| [Installation](https://nokia-steward.github.io/openconfig-ansible-integration/getting-started/installation/) | Python dependencies, Galaxy, GitHub release, source build |
| [Quick Start](https://nokia-steward.github.io/openconfig-ansible-integration/getting-started/quick-start/) | Router gRPC setup, inventory and first gNMI tasks |
| [Inventory Patterns](https://nokia-steward.github.io/openconfig-ansible-integration/getting-started/inventory-patterns/) | Group variables for SR OS, SR Linux and other gNMI routers |
| [User Guide](https://nokia-steward.github.io/openconfig-ansible-integration/guides/user-guide/) | Origins, gNMI extensions, gNOI/gNSI, backup & diff |
| [Platform Notes](https://nokia-steward.github.io/openconfig-ansible-integration/guides/platform-notes/) | Origins, encodings and limits per platform |
| [Security Guide](https://nokia-steward.github.io/openconfig-ansible-integration/guides/security-guide/) | TLS modes, credentials, gNSI |
| [gRPC Architecture](https://nokia-steward.github.io/openconfig-ansible-integration/guides/grpc-architecture/) | How the connection works, relation to `ansible.netcommon.grpc` |
| [Reference](https://nokia-steward.github.io/openconfig-ansible-integration/reference/) | Modules and connection (from docstrings) |
| [Examples](https://nokia-steward.github.io/openconfig-ansible-integration/examples/) | Shipped workflow playbooks and the `tests/playbooks/` integration suite |

Build docs locally:

```bash
make install-dev
make docs
make docs-serve   # http://127.0.0.1:8000
```

---

## Features

- **gNMI 0.10.0** — Get, Set, Subscribe, Capabilities; Depth, Commit, ConfigSubscription extensions  
- **gNOI** — System, File, OS, FactoryReset, Healthz, BGP  
- **gNSI** — Authz, Certz, Pathz, Credentialz  
- **Persistent gRPC** — One connection plugin; no vendor-specific loader  
- **Specification-aligned** modules — One module per RPC, options named after the request fields  
- **Backup / check mode / diff** on `gnmi_set` — Ansible-native operational patterns  
- **Origin option** on the gNMI modules and per host (`ansible_gnmi_origin`) — short paths for OpenConfig and native models  
- **Workflow playbooks** — safe configuration change, snapshot and drift detection, LLDP and interface reports, reachability, OS upgrade, device inventory  
- **Multi-vendor gNMI** — validated on SR OS and SR Linux; other OpenConfig routers are configured through inventory variables  

See [Supported specifications](https://nokia-steward.github.io/openconfig-ansible-integration/#supported-specifications) for the versions of the specifications and services.

---

## Modules (overview)

**gNMI:** `gnmi_capabilities`, `gnmi_get`, `gnmi_set`, `gnmi_subscribe`  

**gNOI** and **gNSI:** one module per RPC that Nokia SR OS or SR Linux supports, named `gnoi_<service>_<rpc>` and `gnsi_<service>_<rpc>`, for example `gnoi_system_ping`, `gnoi_file_put`, `gnoi_healthz_get`, `gnsi_certz_get_profile_list`, `gnsi_authz_rotate`.  

**Playbooks:** run with `ansible-playbook -i inventory.yml nokia.openconfig.<name>`, for example `nokia.openconfig.safe_config_change` or `nokia.openconfig.config_snapshot`. See [playbooks/README.md](playbooks/README.md).

Details: [module reference](https://nokia-steward.github.io/openconfig-ansible-integration/reference/).

---

## Support

- [Documentation site](https://nokia-steward.github.io/openconfig-ansible-integration/)  
- [Issues](https://github.com/nokia-steward/openconfig-ansible-integration/issues)  
- [Changelog](CHANGELOG.md)  
- [Contributing](CONTRIBUTING.md)  

---

**Version:** 2.0.2 · **License:** BSD 3-Clause
