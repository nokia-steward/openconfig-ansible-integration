# Developer Guide

Contributors extend **`nokia.openconfig`** in the Git repository [openconfig-ansible-integration](https://github.com/nokia-steward/openconfig-ansible-integration). The canonical step-by-step environment setup lives in **[CONTRIBUTING.md](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/CONTRIBUTING.md)** on GitHub.

## Repository layout

| Path | Purpose |
| --- | --- |
| `plugins/connection/grpc.py` | Persistent gRPC connection (gNMI, gNOI, gNSI) |
| `plugins/modules/` | Ansible modules (`gnoi_*` / `gnsi_*` are generated) |
| `plugins/module_utils/gnxi_module.py` | Shared runner of the generated gNOI / gNSI modules |
| `plugins/module_utils/proto/` | gNMI / gNOI / gNSI `.proto` sources |
| `tools/nokia_grpc_modules.yaml` | Nokia-supported gNOI / gNSI RPCs, one entry per module |
| `tools/generate_grpc_modules.py` | Renders `plugins/modules/gnoi_*.py` / `gnsi_*.py` from the manifest |
| `tools/sync_openconfig_protos.sh` | Refresh protos from OpenConfig upstream |
| `tools/build_openconfig_protos.sh` | Generate `*_pb2.py` (pinned protoc) |
| `tests/unit/` | Module and connection unit tests |
| `plugins/filter/` | `strip_yang_prefixes` filter |
| `playbooks/` | Workflow playbooks shipped with the collection, run as `nokia.openconfig.<name>` |
| `tests/playbooks/` | Integration categories via `tests/run.sh` |
| `tests/unit/plugins/connection/openconfig_mock_server.py` | In-process gNxI mock server for unit tests |

## Module naming

Every module maps to exactly one gRPC RPC; there is no `rpc` option. Ansible module names cannot contain dots, so the logical name `gnoi.system.time` becomes the FQCN `nokia.openconfig.gnoi_system_time`.

| Protocol | Module name | Example | gRPC |
| --- | --- | --- | --- |
| gNMI | `gnmi_{rpc}` | `gnmi_get` | `gNMI.Get` |
| gNOI | `gnoi_{service}_{rpc}` | `gnoi_system_time`, `gnoi_factory_reset_start` | `System.Time`, `FactoryReset.Start` |
| gNSI | `gnsi_{service}_{rpc}` | `gnsi_certz_get_profile_list` | `Certz.GetProfileList` |

- Service and RPC are the proto names in snake_case; acronyms stay together (`ClearBGPNeighbor` → `clear_bgp_neighbor`, `CanGenerateCSR` → `can_generate_csr`).
- Single-RPC services use the full pattern too (`gnoi_bgp_clear_bgp_neighbor`).
- New gRPC services follow the same rule (for example `gribi_{service}_{rpc}`).
- gNMI keeps its 1.x module set; `meta/runtime.yml` tombstones `gnmi_config` in favour of `gnmi_set`.

## gNOI / gNSI module scope

The `.proto` trees are complete, but modules exist only for RPCs that **Nokia SR OS and/or SR Linux implement** and that we can validate. The inventory lives in `tools/nokia_grpc_modules.yaml`: one entry per module with service, RPC, streaming pattern, platforms (`sros`, `srl`), validation (`unit`, `integration`), check-mode behaviour, and typed options mapped to protobuf JSON fields.

Add an entry only when:

1. Nokia documents the RPC on at least one platform, and a lab device does not return `UNIMPLEMENTED`.
2. The mock server implements it and a unit test covers it. Add an integration task on `nokia_srsim` / `nokia_srlinux` when the RPC is safe to run in the lab, add the playbook to the category of `tests/playbooks.yml` that matches the platforms it supports, and list `integration` under `validation`.

RPCs that cannot run safely in the lab (reboot, factory reset, OS install, gNSI rotations) are listed with `validation: [unit]`; their module notes say so. The manifest header lists RPCs that were evaluated and left out because both lab platforms return `UNIMPLEMENTED`.

After editing the manifest:

```bash
python tools/generate_grpc_modules.py          # writes modules, removes stale gnoi_/gnsi_ files
python tools/generate_grpc_modules.py --check  # CI-style check, exit 1 when out of date
make docs                                      # reference pages
```

Generated modules call `run()` from `gnoi_module` / `gnsi_module`, which delegates to `gnxi_module.run()`:

- Typed options are written to their protobuf JSON field (`field`), optionally encoded (`path`/`paths` take gNMI path strings, `duration` takes Go durations or seconds and sends nanoseconds).
- Options that are not request fields (local files, remote paths of streaming RPCs) are passed to the connection as keyword arguments (`transport`).
- Read-only RPCs run in check mode and report `changed: false`; all others report `changed: true` and are skipped in check mode.

`tests/unit/plugins/test_grpc_manifest.py` fails when generated modules are out of date, when the connection's service or streaming tables differ from the manifest, or when the mock server implements more or fewer RPCs than the manifest lists.

## Connection plugin internals

[gRPC Architecture](grpc-architecture.md) gives the overview and explains why the protocol logic lives in the connection plugin rather than in an `ansible.netcommon.grpc` sub-plugin.

Modules call the persistent connection through `Rpc(module)(method, **kwargs)` (`plugins/module_utils/gnmi_module.py`):

| Method | Used by | Dispatch |
| --- | --- | --- |
| `gnmiCapabilities`, `gnmiGet`, `gnmiSet`, `gnmiSubscribe` | `gnmi_*` | One method per RPC |
| `invokeGnoi(service, rpc, request=None, local_path=None, remote_path=None, …)` | `gnoi_*` | Keyed by `(service, rpc)` |
| `invokeGnsi(service, rpc, request=None, stream=None)` | `gnsi_*` | Keyed by `(service, rpc)` |

These names are internal; playbooks only see module FQCNs.

### Streaming

Ansible tasks are one-shot. Every stream is opened, fed, and drained inside the connection plugin before the task returns, so no module exposes an open stream:

```text
task params ──> module ──> invokeGnoi / invokeGnsi / gnmiSubscribe
                                 │
          ┌──────────────┬───────┴────────┬──────────────────┬──────────────────────┐
        unary     server streaming   client streaming   bidi streaming        gNMI Subscribe
   one request    drain to a list    generator from     iterator in,          request generator +
   one response   (File.Get: file)   local_path         list of responses     read loop with timeout
```

`invokeGnoi` checks special cases first, then the tables in `plugins/module_utils/gnoi.py`:

1. `File.Put`, `System.SetPackage`: `gnoi.file_put_requests()` / `set_package_requests()` yield the open/details message, 64 KiB `contents` chunks, then a SHA-256 `hash`; `_gnoi_stream_client()` returns the single response.
2. `OS.Install`: `gnoi.os_install_requests()` yields `transfer_request`, chunks, and `transfer_end`; `_gnoi_stream_both()` collects every server message.
3. `File.Get`: `_gnoi_stream_server()` writes `contents` chunks to `save_to` and returns the final `hash`.
4. Other RPCs in `gnoi.SERVER_STREAMING` (`Ping`, `Traceroute`, `Healthz.Artifact`): `_gnoi_stream_server()` returns all messages as a list.
5. Everything else is unary.

`invokeGnsi` sends `stream` items (dicts parsed into `gnsi.STREAM_REQUEST[(service, rpc)]`) through `_gnoi_stream_both()` for `gnsi.BIDI_STREAMING` RPCs, otherwise it builds one unary request.

`gnmiSubscribe` drives a bidirectional stream with its own request generator (initial `SubscribeRequest`, one `Poll` in POLL mode) and reads until `duration` expires, ONCE/POLL sync completes, or a ConfigSubscription `sync_done` with `done` arrives.

**Limitation:** bidirectional RPCs use a client iterator that is fixed before the call (file chunks or the module's `stream` list). The connection never picks the next client message based on a server response in the same RPC. An RPC that needs that conversation (for example, a gNSI Certz rotation that signs a device-generated CSR within the same stream) needs an RPC-specific state machine in the connection plugin, not a longer `stream` list.

### Mock server

`OpenConfigMockServer` serves gNMI plus exactly the manifest's gNOI / gNSI RPCs on one insecure port. Streaming handlers mirror the device side (`File.Put` and `System.SetPackage` consume chunks and reject a wrong SHA-256 hash, `Authz.Rotate` answers each upload), so connection tests exercise the same code paths as a device. When you add a manifest entry, add the mock handler in the same change.

## Build protobuf modules

```bash
pip install -r requirements-dev.txt
tools/build_openconfig_protos.sh
```

Generated `*_pb2.py` files are **gitignored**; CI and release builds run the script before tests and collection build.

## Tests

`.github/test-matrix.yml` lists the test suites and the exact version combinations. CI runs every case as `make test-setup` followed by `make test-<suite>`, and you can run the same targets locally:

```bash
make test-setup                  # ansible-core $ANSIBLE_VERSION (default 2.22), requirements-dev.txt, protos
make test-sanity                 # ansible-test sanity
make test-units                  # ansible-test units and a syntax check of the shipped playbooks
make test-integration            # containerlab: SR OS when $SROS_VERSION is set, else SR Linux $SRL_VERSION
make test-integration SROS_VERSION=26.10.R1        # needs an SR-SIM license
make test-integration SRL_VERSION=26.7 REGISTRY=ghcr.io/nokia/srlinux
```

`REGISTRY` is the image path without the tag. A release without a patch number, such as `26.10`, runs the newest patch release in that registry; the target logs the image it picked.

The integration tests are not end-to-end tests: each platform has its own single-node lab, `tests/sros.clab.yml` or `tests/srlinux.clab.yml`, and both run the one test list, `tests/playbooks.yml`. Each category there names the platforms it applies to (`hosts: nokia_srsim:nokia_srlinux`, the same as the hosts of its playbooks); a category with no host in the lab is reported as skipped. The platform groups are declared in `tests/platforms.yml`, so a pattern may name a platform the lab lacks; to test another platform, add its group there and to the categories it supports. The integration targets build and install the collection artifact first, deploy the lab, run all categories of the list and destroy the lab. They need containerlab 0.83.0 or newer: older releases render a TLS 1.3 cipher that SR OS 26.7 and newer reject, and the node then starts without gRPC. Results are written to `tests/output/junit/`, the playbook logs to `tests/output/logs/`. Step by step:

```bash
tools/ansible_test.sh units --python 3.13
tools/ansible_test.sh sanity --docker default   # when Docker is available

cd tests
./run.sh deploy --topo srlinux.clab.yml         # or --topo sros.clab.yml
./run.sh run --category common
./run.sh destroy --topo srlinux.clab.yml
```

ansible-core devel runs as an experimental case: its failures are reported but never block a merge. The SR OS cases need a license; without an `SRSIM_LICENSE` secret, GitHub lists them as not run, and a maintainer runs them with nokia-steward-validator, which posts the result to the pull request. See [.github/workflows/README.md](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/.github/workflows/README.md). `.github/workflows/ci.yml`, `.github/scripts/` and `tests/run.sh` are shared files of the nokia-steward test pattern; change the matrix, not these files.

## Documentation

User docs are **MkDocs Material**. Reference pages are generated from module docstrings:

```bash
make install-dev   # or pip install -r requirements-dev.txt
make docs          # tools/generate_docs.py + mkdocs build
make docs-serve    # http://127.0.0.1:8000
```

`tools/generate_docs.py` updates `docs/reference/*.md` and the **Reference** section of `mkdocs.yml`.

## Pull requests

Follow Ansible collection conventions: sanity tests, unit tests, changelog entry for user-visible changes, and module documentation blocks (`DOCUMENTATION` / `EXAMPLES` / `RETURN`) as the source of truth for the reference site.
