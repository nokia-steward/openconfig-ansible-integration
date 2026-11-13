# Examples

The collection ships workflow playbooks for everyday operations. The repository also contains the integration test suite, whose playbooks show each module in use.

## Shipped playbooks

The playbooks in [`playbooks/`](https://github.com/nokia-steward/openconfig-ansible-integration/tree/main/playbooks) are installed with the collection. Run them by name from any directory, with your own inventory:

```bash
ansible-playbook -i inventory.yml nokia.openconfig.<name> [-e variable=value ...]
```

They take the connection settings from the inventory, so the same playbook runs on every router your inventory describes; see [Inventory Patterns](getting-started/inventory-patterns.md). Each playbook lists its variables in the comment at the top, and `-e target=<pattern>` limits it to some routers. Reports, snapshots and backups are written below the current directory.

| Playbook | What it does | Output |
| --- | --- | --- |
| [safe_config_change](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/safe_config_change.yml) | Backup, preview, optional approval, apply and verify. With `use_confirmed_commit: true` the change is a confirmed commit that is cancelled when the verification fails | `backup/` |
| [config_snapshot](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/config_snapshot.yml) | Saves the configuration, keeps a history per router and reports drift since the previous run | `snapshots/<host>/` |
| [lldp_neighbors](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/lldp_neighbors.yml) | Topology report from OpenConfig LLDP; checks the cabling against `expected_neighbors` | `reports/lldp_neighbors.{csv,json}` |
| [interface_health](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/interface_health.yml) | Interfaces that are admin up but not oper up, or have errors or discards above a threshold | `reports/interface_health.{csv,json}` |
| [reachability_check](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/reachability_check.yml) | gNOI ping from every router to a list of destinations, with loss and round-trip times | `reports/reachability.{csv,json}` |
| [os_upgrade](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/os_upgrade.yml) | gNOI OS install and activate, one router at a time, with configuration backup and version check | `backup/` |
| [device_inventory](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/playbooks/device_inventory.yml) | Vendor, model, serial number, software version, gNMI version, encodings and models of every router | `reports/device_inventory.{csv,json}` |

The read playbooks use the OpenConfig models. `os_upgrade` needs gNOI OS, which SR Linux supports on hardware platforms.

### A safe change

Describe the change in a file:

```yaml
# change.yml
origin: openconfig
use_confirmed_commit: true
rollback_duration: 5m
changes:
  update:
    - path: /lldp/config/enabled
      value: true
verify:
  - path: /lldp/config/enabled
    value: true
```

Run it against one router first, then the rest. Routers are changed one at a time unless you set `batch_size`:

```bash
ansible-playbook -i inventory.yml nokia.openconfig.safe_config_change -e @change.yml -e target=leaf1
ansible-playbook -i inventory.yml nokia.openconfig.safe_config_change -e @change.yml
```

If a read-back value differs, the confirmed commit is cancelled and the router returns to its previous configuration. Without a confirmed commit, the playbook stops and names the backup to restore.

### Drift detection

```bash
ansible-playbook -i inventory.yml nokia.openconfig.config_snapshot --diff
```

The first run saves a baseline. Later runs report the routers whose configuration changed and, with `--diff`, show the change. Add `-e fail_on_drift=true` to make drift fail the run, for example in a scheduled job.

### Example inventory

[`playbooks/examples/`](https://github.com/nokia-steward/openconfig-ansible-integration/tree/main/playbooks/examples) has an inventory with group variables for Nokia SR Linux, Nokia SR OS, Cisco IOS XE, Cisco IOS XR and a generic gNMI router, and an example change. Copy it as a starting point.

## Integration test playbooks

The playbooks below are part of the integration test suite in [`tests/playbooks/`](https://github.com/nokia-steward/openconfig-ansible-integration/tree/main/tests/playbooks). Each one runs against Nokia SR OS, SR Linux or both, and can be used as a template for your own playbooks.

The Platform column names the routers a playbook runs on. Playbooks for both platforms take their native YANG paths from the group variables [`nokia_srsim.yml`](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/group_vars/nokia_srsim.yml) and [`nokia_srlinux.yml`](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/group_vars/nokia_srlinux.yml). Playbooks marked OpenConfig use the OpenConfig paths in [`model_oc.yml`](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/vars/model_oc.yml); OpenConfig must be enabled on the router.

### gNMI

| Playbook | Platform | Description |
| --- | --- | --- |
| [gNMI_Capabilities.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Capabilities.yml) | SR OS, SR Linux | Capabilities and encoding checks |
| [gNMI_GetConfig.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_GetConfig.yml) | SR OS, SR Linux | Get of configuration |
| [gNMI_SubscribeOnce.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_SubscribeOnce.yml) | SR OS, SR Linux | Subscribe in ONCE mode |
| [gNMI_Backup.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Backup.yml) | SR OS, SR Linux | Set with `backup: true` |
| [gNMI_Depth.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Depth.yml) | SR OS, SR Linux | Depth extension on Get and Subscribe |
| [gNMI_CommitConfirmed.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_CommitConfirmed.yml) | SR OS, SR Linux | Confirmed commit: confirm, rollback, extend and cancel |
| [gNMI_ConfigSubscription.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_ConfigSubscription.yml) | SR OS, SR Linux | ConfigSubscription extension, in ONCE mode on SR Linux and STREAM mode on both |
| [gNMI_GetConfig_OC.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_GetConfig_OC.yml) | SR OS, SR Linux (OpenConfig) | Get of LLDP configuration and state |
| [gNMI_Config_OC.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Config_OC.yml) | SR OS, SR Linux (OpenConfig) | Set of LLDP `config/enabled` |
| [gNMI_Subscribe_OC.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Subscribe_OC.yml) | SR OS, SR Linux (OpenConfig) | Interface counters in SAMPLE mode |
| [gNMI_Config_SROS.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Config_SROS.yml) | SR OS | Update, replace and delete in one transaction under `/configure` |
| [gNMI_Subscribe_SROS.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Subscribe_SROS.yml) | SR OS | State and configuration subscriptions |
| [gNMI_SubscribeOnce_SROS.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_SubscribeOnce_SROS.yml) | SR OS | Subscribe in ONCE mode to native paths |
| [gNMI_Config_SRL.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Config_SRL.yml) | SR Linux | Configuration changes |
| [gNMI_Subscribe_SRL.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Subscribe_SRL.yml) | SR Linux | State and configuration subscriptions |
| [gNMI_Restore_SRL.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNMI_Restore_SRL.yml) | SR Linux | Backup, change and full restore with `replace` on `/` |

### gNOI and gNSI

| Playbook | Platform | Description |
| --- | --- | --- |
| [gNOI_System.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNOI_System.yml) | SR OS, SR Linux | Time, Ping and Traceroute |
| [gNOI_File.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNOI_File.yml) | SR OS, SR Linux | Put, Stat, Get and Remove round trip |
| [gNOI_Healthz_SRL.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNOI_Healthz_SRL.yml) | SR Linux | Healthz List and Get |
| [gNSI_Validate_SRL.yml](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks/gNSI_Validate_SRL.yml) | SR Linux | Authz, Certz, Pathz and Credentialz, including a Certz profile add and delete |

### Running the integration tests

The test runner groups the playbooks into categories in [`tests/playbooks.yml`](https://github.com/nokia-steward/openconfig-ansible-integration/blob/main/tests/playbooks.yml), for example `common`, `sros`, `srlinux`, `gnoi` and `gnsi`. Each category names the platforms it applies to. The list runs against a single-node containerlab topology, `tests/sros.clab.yml` or `tests/srlinux.clab.yml`, and skips the categories that do not apply to it:

```bash
cd tests
./run.sh deploy --topo srlinux.clab.yml      # or --topo sros.clab.yml
./run.sh run --category common               # run one category
./run.sh destroy --topo srlinux.clab.yml
```

The default `tests/ansible.cfg` uses the containerlab inventory under `tests/clab-ansible/`, generated on deploy. For physical lab routers, use a private inventory, for example under `tests/clab-lab/` (gitignored), and `ANSIBLE_CONFIG=tests/ansible_lab.cfg`.

See also the [Quick Start](getting-started/quick-start.md) and the [User Guide](guides/user-guide.md).
