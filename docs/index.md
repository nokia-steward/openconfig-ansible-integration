# Nokia OpenConfig Ansible Collection

Welcome to the documentation of the Ansible collection `nokia.openconfig`.

This collection provides a gRPC connection plugin and modules for the OpenConfig management interfaces [gNMI](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md), [gNOI](https://github.com/openconfig/gnoi) and [gNSI](https://github.com/openconfig/gnsi). Those interfaces are used to access configuration and operational data, to stream telemetry, to run device operations and to manage security. The focus and coverage of this collection is based on Nokia IP networking equipment running either of the network operating systems SR OS or SR Linux.

## What is included

### Connection plugin

- [`nokia.openconfig.grpc`](reference/nokia.openconfig.grpc.md) — one persistent gRPC channel per host that serves gNMI, gNOI and gNSI, with TLS, credentials and encoding negotiation.

### Modules

The collection provides one module per RPC, using the management interface as prefix. gNMI modules follow the pattern `gnmi_<rpc>`, gNOI and gNSI modules follow the pattern `<interface>_<service>_<rpc>`, for example [`gnoi_system_ping`](reference/nokia.openconfig.gnoi_system_ping.md) or [`gnsi_certz_get_profile_list`](reference/nokia.openconfig.gnsi_certz_get_profile_list.md).

The collection only contains modules for RPCs and gNMI extensions that are supported by [Nokia SR OS](https://www.nokia.com/ip-networks/service-router-operating-system-nos/) or [Nokia SR Linux](https://www.nokia.com/ip-networks/service-router-linux-NOS/). See the [reference](reference/index.md) for the full list.

Most playbooks need only four of them: `gnmi_capabilities`, `gnmi_get`, `gnmi_set` and `gnmi_subscribe`. [Start Here](getting-started/start-here.md) maps common tasks to modules.

### Playbooks and filter

- Workflow playbooks for safe configuration changes, configuration snapshots with drift detection, LLDP and interface reports, reachability checks, OS upgrades and device inventory. Run them as `nokia.openconfig.<name>`, see [Examples](examples.md#shipped-playbooks).
- The filter `nokia.openconfig.strip_yang_prefixes` removes YANG module prefixes from response data, see [Platform Notes](guides/platform-notes.md#reading-responses).

## Supported specifications

The modules are built from the OpenConfig protobuf definitions listed below.

### gNMI

| Specification | Version | Source |
| --- | --- | --- |
| [gNMI](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md) | 0.10.0 | [openconfig/gnmi](https://github.com/openconfig/gnmi) tag `v0.14.1` |

| RPC | Module |
| --- | --- |
| Capabilities | [`gnmi_capabilities`](reference/nokia.openconfig.gnmi_capabilities.md) |
| Get | [`gnmi_get`](reference/nokia.openconfig.gnmi_get.md) |
| Set | [`gnmi_set`](reference/nokia.openconfig.gnmi_set.md) |
| Subscribe | [`gnmi_subscribe`](reference/nokia.openconfig.gnmi_subscribe.md) |

| gNMI extension | Used by |
| --- | --- |
| [Depth](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-depth.md) | [`gnmi_get`](reference/nokia.openconfig.gnmi_get.md), [`gnmi_subscribe`](reference/nokia.openconfig.gnmi_subscribe.md) |
| [Commit (confirmed commit)](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-commit-confirmed.md) | [`gnmi_set`](reference/nokia.openconfig.gnmi_set.md) |
| [ConfigSubscription](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-config-subscriptions.md) | [`gnmi_subscribe`](reference/nokia.openconfig.gnmi_subscribe.md) |

The extensions History and Master Arbitration are not supported.

### gNOI

Sources are taken from [openconfig/gnoi](https://github.com/openconfig/gnoi). The version is the `gnoi_version` option of each proto file.

| Service | Version |
| --- | --- |
| [System](https://github.com/openconfig/gnoi/blob/main/system/system.proto) | 1.4.0 |
| [File](https://github.com/openconfig/gnoi/blob/main/file/file.proto) | 0.1.1 |
| [OS](https://github.com/openconfig/gnoi/blob/main/os/os.proto) | 0.1.1 |
| [FactoryReset](https://github.com/openconfig/gnoi/blob/main/factory_reset/factory_reset.proto) | 0.1.0 |
| [Healthz](https://github.com/openconfig/gnoi/blob/main/healthz/healthz.proto) | 1.3.0 |
| [BGP](https://github.com/openconfig/gnoi/blob/main/bgp/bgp.proto) | 0.1.0 |

### gNSI

Sources are taken from [openconfig/gnsi](https://github.com/openconfig/gnsi) at commit `6c31586` (October 2026). gNSI protos do not carry a version option.

| Service | Purpose |
| --- | --- |
| [Authz](https://github.com/openconfig/gnsi/tree/main/authz) | gRPC authorization policy |
| [Certz](https://github.com/openconfig/gnsi/tree/main/certz) | TLS profiles and certificates |
| [Pathz](https://github.com/openconfig/gnsi/tree/main/pathz) | gNMI path authorization policy |
| [Credentialz](https://github.com/openconfig/gnsi/tree/main/credentialz) | SSH host keys and account credentials |

## Validated platforms

The collection is validated on Nokia SR OS and SR Linux. A lightweight gNMI, gNOI and gNSI mock server is included for component testing, which is useful when no SR OS or SR Linux image or license is available.

The implementation follows the OpenConfig specifications, so the collection works with routers of other vendors that expose the same gRPC services, for example Cisco IOS XE and IOS XR. Platform differences are set in the inventory: port, TLS, encoding and path origin. [Inventory Patterns](getting-started/inventory-patterns.md) has group variables per platform, and [Platform Notes](guides/platform-notes.md#other-vendors) lists what to check. Keep in mind that gNMI paths and payloads depend on the YANG models a device implements: native models differ between vendors, and support for OpenConfig models varies between platforms and releases.

## Getting started

1. [Start Here](getting-started/start-here.md) — which module or playbook to use for a task.
2. [Installation](getting-started/installation.md) — Python environment, external dependencies and the collection.
3. [Quick Start](getting-started/quick-start.md) — enable gRPC on the router, set up the inventory and run a first gNMI Get.
4. [Inventory Patterns](getting-started/inventory-patterns.md) — group variables per platform.
5. [User Guide](guides/user-guide.md) — connection options, gNMI, gNOI and gNSI modules and workflows.
6. [Reference](reference/index.md) — module and plugin documentation, generated from the module sources.

## Support

- [Examples](examples.md) — playbooks from the repository test suite.
- [Support](support.md) — community, issues and testing before production.
- [Changelog](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/CHANGELOG.md) on GitHub.

---

**Collection version:** 2.0.2 · **License:** BSD 3-Clause · **Ansible:** 2.18+ · **Python:** 3.12+
