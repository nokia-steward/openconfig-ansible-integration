# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.2]

Compatibility and reliability fixes for TLS lab connections, check-mode backups, atomic gNOI file downloads, multi-module OpenConfig paths, and Ansible 2.18+ controllers.

### Added
- `gnmi_set` accepts `val` as a backward-compatible alias for `value` on `update` and `replace` entries.

### Changed
- Relaxed `requires_ansible` in `meta/runtime.yml` from `>=2.20.0` to `>=2.18.0` so Ansible 11 (`ansible-core` 2.18+) runs without unsupported-version warnings.

### Fixed
- `nokia.openconfig.grpc` with `validate_certs: false` now extracts DNS/IP Subject Alternative Names or Subject `commonName` from DER peer certificates (`getpeercert(True)`) so IP connections to certificates without an IP SAN automatically set `grpc.ssl_target_name_override`.
- `gnmi_module.Rpc.call` uses `getattr(exc, 'code', -1)` so persistent-socket startup `ConnectionError` exceptions report the real connection failure instead of raising `AttributeError`.
- `gnmi_set` with `backup: true` no longer fails with `AnsibleError: Failed while reading configuration backup` in `--check` mode or with `dry_run: true`.
- `gnoi_file_get` streams into a temporary file (preserving existing file permissions or process `umask`) and atomically replaces `local_path` on completion so existing local files are not truncated when a remote RPC fails.
- `gnmi.encode_path` and `gnmi._prefix` preserve the root module `origin` and strip nested OpenConfig module prefixes on both single-path and split `prefix` + `path` requests (such as `/openconfig-interfaces:interfaces/interface[name=eth0]/openconfig-if-ip:ipv4`).

## [2.0.1]

Shorter gNMI paths with a dedicated origin, workflow playbooks shipped with the collection, and documentation organized by task. Existing playbooks keep working unchanged.

### Added
- `origin` option on `gnmi_get`, `gnmi_set` and `gnmi_subscribe`. It applies to every path that does not name its own origin, so OpenConfig paths can be written as `/system/config/hostname` with `origin: openconfig`. It is placed on the prefix when the request has one, otherwise on each path. `gnmi_set` also uses it for the backup and for the reads behind `changed` and `diff`.
- Connection option `gnmi_origin` (ini `grpc_connection`, env `ANSIBLE_GNMI_ORIGIN`, var `ansible_gnmi_origin`): default origin per host. `origin: ""` on a task sends paths without origin.
- Filter `nokia.openconfig.strip_yang_prefixes`: removes YANG module prefixes from member names of response data, so the same expressions work for `JSON` and `JSON_IETF` and across platforms.
- Action group `nokia.openconfig.gnmi` (`gnmi_get`, `gnmi_set`, `gnmi_subscribe`) for `module_defaults`.
- Workflow playbooks under `playbooks/`, run as `nokia.openconfig.<name>`: `safe_config_change`, `config_snapshot`, `lldp_neighbors`, `interface_health`, `reachability_check`, `os_upgrade` and `device_inventory`. `playbooks/examples/` contains an inventory with group variables for Nokia SR Linux, Nokia SR OS, Cisco IOS XE, Cisco IOS XR and a generic gNMI router.
- Documentation: Start Here, Inventory Patterns, Platform Notes and gRPC Architecture, TLS modes in the Security Guide, and the shipped playbooks in Examples.
- CI checks the syntax of the shipped playbooks, run by name.

### Changed
- When a path has an origin, from the path itself or from `origin`, module-qualified element names are sent unchanged, for example `rfc7951:/Cisco-IOS-XE-native:native/hostname`. Paths without any origin behave as in 2.0.0: a prefix in the first element, as in `/openconfig-lldp:lldp`, becomes the origin.
- The connection reference documents `grpc.max_receive_message_length` for responses larger than 4 MB.
- The gNOI and gNSI support matrix in the User Guide moved to Platform Notes and the module reference.

## [2.0.0]

Module options follow the request fields of the gNMI, gNOI and gNSI specifications, the connection follows `ansible.netcommon.grpc`, and gNOI and gNSI are supported with one module per RPC. This is a breaking release: the 1.0.0 connection, module, option and parameter names were removed. See "Removed" below for the replacements.

### Added
- Connection plugin `nokia.openconfig.grpc`, which replaces `nokia.openconfig.gnmi`. It carries gNMI, gNOI and gNSI on one persistent gRPC channel.
- gNMI 0.10.0 protos (gnmi v0.14.1), compiled by `tools/build_openconfig_protos.sh` with a pinned protoc 3.19.5 (grpcio-tools 1.47.5), so the generated code works with protobuf 3.20.3 up to 7.x and any grpcio release.
- Depth extension: `depth` on `gnmi_get` and `gnmi_subscribe`.
- Commit extension (confirmed commit) on `gnmi_set`: `commit_id`, `commit_request`, `commit_confirm`, `commit_cancel`, `rollback_duration`.
- ConfigSubscription extension: `config_subscription` on `gnmi_subscribe`. In `STREAM` mode it waits for the next sync-done.
- Response extensions are returned as `extensions`, using protobuf field names.
- `gnmi_get`: `target`, `model`, `encoding`, `values_only`.
- `gnmi_set`: `target`, `encoding`, per-item `encoding`, `request_file` (JSON or YAML request file), `dry_run`, check mode, and `diff`.
- `gnmi_subscribe`:
  - `path` with `stream_mode`, `sample_interval`, `heartbeat_interval` and `suppress_redundant`.
  - `POLL` mode, `target`, `model`, `encoding`.
- `gnmi_capabilities` returns `gnmi_version`, `encodings`, `models` and `extensions` next to the raw `output`.
- Connection options:
  - `validate_certs` (ini `grpc_connection`, env `ANSIBLE_GRPC_VALIDATE_CERTS`, var `ansible_grpc_validate_certs`). When `false`, pins the server TLS certificate at connect time for lab use.
  - `ssl_target_name_override`.
  - `[defaults]` and `[persistent_connection]` ini and `ANSIBLE_*` environment sources for port, user and timeouts.
  - `persistent_command_timeout` is used as the gRPC deadline for Capabilities, Get and Set.
- OpenConfig gNOI and gNSI: one module per RPC that Nokia SR OS or SR Linux supports, named `gnoi_<service>_<rpc>` and `gnsi_<service>_<rpc>` (39 modules). gNSI requires SR Linux with gNSI enabled on the gRPC server.
  - gNOI System: `gnoi_system_time`, `gnoi_system_ping`, `gnoi_system_traceroute`, `gnoi_system_reboot`, `gnoi_system_cancel_reboot`, `gnoi_system_reboot_status`, `gnoi_system_switch_control_processor`, `gnoi_system_kill_process`, `gnoi_system_set_package`.
  - gNOI File: `gnoi_file_get`, `gnoi_file_put`, `gnoi_file_stat`, `gnoi_file_remove`, `gnoi_file_transfer_to_remote`.
  - gNOI OS: `gnoi_os_install`, `gnoi_os_activate`, `gnoi_os_verify`.
  - gNOI FactoryReset, Healthz and BGP: `gnoi_factory_reset_start`, `gnoi_healthz_get`, `gnoi_healthz_list`, `gnoi_healthz_acknowledge`, `gnoi_healthz_check`, `gnoi_healthz_artifact`, `gnoi_bgp_clear_bgp_neighbor`.
  - gNSI: `gnsi_authz_get`, `gnsi_authz_probe`, `gnsi_authz_rotate`, `gnsi_certz_get_profile_list`, `gnsi_certz_can_generate_csr`, `gnsi_certz_add_profile`, `gnsi_certz_delete_profile`, `gnsi_certz_rotate`, `gnsi_pathz_get`, `gnsi_pathz_probe`, `gnsi_pathz_rotate`, `gnsi_credentialz_get_public_keys`, `gnsi_credentialz_can_generate_key`, `gnsi_credentialz_rotate_account_credentials`, `gnsi_credentialz_rotate_host_parameters`.
- gNOI and gNSI module options are the RPC request fields in snake_case; path options take gNMI path strings and duration options take values such as `500ms`. Read-only RPCs run in check mode, all others are skipped. Streams are opened and drained by the connection, so playbooks never handle an open stream. A relative `local_path` is resolved against the working directory of `ansible-playbook`.
- `tools/sync_openconfig_protos.sh` refreshes the gNMI, gNOI and gNSI `.proto` sources from [openconfig/gnmi](https://github.com/openconfig/gnmi), [openconfig/gnoi](https://github.com/openconfig/gnoi) and [openconfig/gnsi](https://github.com/openconfig/gnsi).
- `tools/nokia_grpc_modules.yaml` lists every shipped gNOI and gNSI RPC with its platforms and how it is validated, and `tools/generate_grpc_modules.py` generates the modules from it.
- **MkDocs** user documentation under `docs/`, built with `make docs` / `make docs-serve` and published to GitHub Pages (`.github/workflows/docs.yml`). The module reference is generated from docstrings by `tools/generate_docs.py`, grouped by gNMI, gNOI and gNSI. Each streaming module documents in its reference page how the task runs the stream and when it completes.
- In-process **`OpenConfigMockServer`** for connection unit tests: gNMI plus exactly the gNOI and gNSI RPCs of the manifest on one port. Unit tests fail when the modules, the connection or the mock server differ from the manifest.
- `ansible-test sanity` and `units` in CI on ansible-core 2.20, 2.21 and 2.22, and a weekly `devel` workflow.
- Integration test categories per YANG model family: `_OC` playbooks use OpenConfig paths, `_SROS` and `_SRL` playbooks native YANG. The `depth`, `commit_confirmed` and `config_subscription` categories check that each extension takes effect, so a server that silently ignores it fails the test. The `gnoi` and `gnsi` categories cover every RPC marked for integration in the manifest. Every playbook asserts its results.
- `run.sh units`, `run.sh sanity` and `run.sh integration`, plus JUnit and Markdown reports. A category whose inventory group has no hosts is reported as skipped.
- CI integration job on containerlab: SR Linux always, and SR OS when the `SRSIM_LICENSE` secret is set.

### Changed
- `gnmi_config` is renamed to `gnmi_set`.
- `gnmi_get` `type` defaults to `ALL` instead of `CONFIG`, matching the gNMI specification.
- `gnmi_subscribe` `mode` defaults to `STREAM` instead of `ONCE`, matching the gNMI specification.
- Connection options are renamed to the `ansible.netcommon.grpc` names, and the ini section is now `[grpc_connection]`.
- Supported versions are ansible-core 2.20 or newer and controller Python 3.12 or newer. `grpcio` must be 1.59.0 or newer and `protobuf` 3.20.3 or newer (5.29.0 or newer on Python 3.14).
- A missing, too old or broken `grpcio` or `protobuf` fails with a message that names the problem, the Python interpreter and the `pip` command to fix it.
- `meta/execution-environment.yml` points `ansible-builder` to `requirements.txt`.
- The protos and generated code moved to `plugins/module_utils/proto`. The unused `collector.proto` and `target.proto` were dropped.
- gRPC errors are reported as `gRPC <CODE>: <details>`.
- `galaxy.yml` `documentation` and `homepage` URLs point to the GitHub Pages site, and the repository and issue URLs were corrected.
- README and CONTRIBUTING describe the docs site and local MkDocs workflow.

### Removed
The 1.0.0 names below were removed. Playbooks using the old connection or module name fail with a message that names the replacement, and so do the old `gnmi_set` and `gnmi_subscribe` keys.
- Connection `nokia.openconfig.gnmi`. Use `nokia.openconfig.grpc`.
- Module `nokia.openconfig.gnmi_config`. Use `nokia.openconfig.gnmi_set`.
- 1.0.0 connection option names:
  - `ansible_root_ca_cert`. Use `ansible_root_certificates_file`.
  - `ansible_cert_chain` and `ANSIBLE_CERT_CHAIN`. Use `ansible_certificate_chain_file` and `ANSIBLE_CERTIFICATE_CHAIN_FILE`.
  - `ansible_channel_options`. Use `ansible_grpc_channel_options`.
  - `ansible_grpc_env`. Use `ansible_grpc_environment`.
  - The `[grpc]` ini section. Use `[grpc_connection]` with the keys `root_certificates_file`, `certificate_chain_file`, `private_key_file`, `gnmi_encoding`, `grpc_channel_options` and `grpc_environment`.
- `gnmi_set` item key `val`. Use `value`.
- `gnmi_subscribe` subscription keys `mode`, `sampleInterval`, `heartbeatInterval` and `suppressRedundant`. Use `stream_mode`, `sample_interval`, `heartbeat_interval` and `suppress_redundant`.
- Connection option `certificate_path` from `nokia.grpc`. Certificate options take a file path.

### Fixed
- IPv6 management addresses: `ansible_host: 2001:db8::1` failed to connect because the address was not put in brackets. Both forms, with and without brackets, now work.
- Release tarballs did not contain the compiled protos, so the connection plugin could not be imported.
- Subscribe results were truncated at the first response without updates.
- Path origins were lost when decoding responses.
- `0` and `false` values were silently dropped from requests.
- A missing certificate file now fails with a clear error.
- `gnmi_subscribe` in check mode skips the Subscribe RPC and returns `skipped: true`; it used to call the device.
- Source file lookup in the shared network action code did not detect URLs or role-relative paths.
- The SR Linux image in the lab topologies used the SR OS version variable.

## [1.0.0]
### Added
- Renamed Ansible collection from `nokia.grpc` to `nokia.openconfig`
- Dedicated GitHub repository for `nokia.openconfig` for simplified release management and CI/CD
- Containerlab topology for test-automation
- GitHub workflow to build collection for every new release
- Updated playbooks for compatibility with latest Ansible releases
