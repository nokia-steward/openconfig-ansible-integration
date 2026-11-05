#!/usr/bin/python
# (c) 2020-2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
---
module: gnmi_set
author:
  - "Hans Thienpondt (@HansThienpondt)"
  - "Sven Wisotzky (@wisotzky)"
short_description: Modify configuration using a single gNMI Set
description:
  - Sends a single gNMI C(SetRequest). Deletes are applied first, then
    replaces, then updates, as a single transaction.
  - Option names are the C(SetRequest) fields in snake_case, and the values
    follow the gNMI 0.10.0 protobuf messages.
  - Confirmed commit uses the gNMI Commit extension. There is no separate
    commit module.
  - To report C(changed), the module reads the affected paths (or the full
    configuration if O(backup=true)) with gNMI Get before and after the Set.
  - This module was called C(nokia.openconfig.gnmi_config) in 1.0.0.
version_added: 1.0.0
options:
  prefix:
    description:
      - Common prefix for all paths, C(SetRequest.prefix).
    type: str
  origin:
    description:
      - Origin of the paths, C(Path.origin), for example C(openconfig) or
        C(rfc7951). Set on O(prefix) if given, otherwise on each path that
        does not name its own origin.
      - With an origin, element names keep their YANG module prefix, for
        example C(/Cisco-IOS-XE-native:native/hostname) with C(rfc7951).
      - Also used for the gNMI Get requests of O(backup) and C(changed).
      - Defaults to the C(gnmi_origin) option of the connection. An empty
        string sends the paths without origin.
    type: str
    version_added: 2.0.1
  target:
    description:
      - Target name set on the prefix, C(Path.target).
    type: str
    version_added: 2.0.0
  update:
    description:
      - Paths and values to merge, C(SetRequest.update).
    type: list
    elements: dict
    suboptions:
      path:
        description:
          - Path to update. A path can name its origin, for example
            C(openconfig:/system/config). Otherwise O(origin) applies.
        type: str
        required: true
      value:
        description:
          - Value to set. Dicts and lists are sent as JSON.
          - Alias C(val) is accepted for compatibility with 1.0.0 playbooks.
        type: raw
        required: true
        aliases:
          - val
      encoding:
        description:
          - Encoding of this value, C(TypedValue). Defaults to the
            encoding of the connection.
          - One of C(JSON), C(JSON_IETF), C(ASCII), C(STRING), C(INT), C(UINT),
            C(BOOL), C(FLOAT), C(BYTES).
        type: str
        version_added: 2.0.0
  replace:
    description:
      - Paths and values to replace, C(SetRequest.replace).
    type: list
    elements: dict
    suboptions:
      path:
        description:
          - Path to replace.
        type: str
        required: true
      value:
        description:
          - Value to set. Dicts and lists are sent as JSON.
          - Alias C(val) is accepted for compatibility with 1.0.0 playbooks.
        type: raw
        required: true
        aliases:
          - val
      encoding:
        description:
          - Encoding of this value. Defaults to the encoding of the connection.
        type: str
        version_added: 2.0.0
  delete:
    description:
      - Paths to delete, C(SetRequest.delete).
    type: list
    elements: str
  request_file:
    description:
      - JSON or YAML file with the request. Top-level keys are C(updates),
        C(replaces) and C(deletes). Each update and replace has C(path),
        C(value) and optionally C(encoding). This is the request file format
        of common gNMI clients.
      - Go templates are not supported. Use M(ansible.builtin.template) to
        render the file first.
      - Relative paths are searched like M(ansible.builtin.copy) sources.
      - The entries are added to O(update), O(replace) and O(delete).
    type: path
    version_added: 2.0.0
  encoding:
    description:
      - Default encoding of the values in this request. Defaults to the
        encoding of the connection.
      - With C(JSON_IETF), SR OS expects member names qualified with the YANG
        module in container values, for example C(nokia-conf:location).
        Use C(JSON) to send plain member names.
    type: str
    version_added: 2.0.0
  commit_id:
    description:
      - ID of the confirmed commit, C(Commit.id).
      - Required with O(commit_request), O(commit_confirm), O(commit_cancel)
        or O(rollback_duration).
    type: str
    version_added: 2.0.0
  commit_request:
    description:
      - Starts a confirmed commit with this Set, C(Commit.commit).
      - The device rolls back the change unless it is confirmed within
        O(rollback_duration).
    type: bool
    default: false
    version_added: 2.0.0
  commit_confirm:
    description:
      - Confirms the confirmed commit O(commit_id), C(Commit.confirm).
      - Usually sent without O(update), O(replace) and O(delete).
    type: bool
    default: false
    version_added: 2.0.0
  commit_cancel:
    description:
      - Cancels the confirmed commit O(commit_id) and rolls back its changes,
        C(Commit.cancel).
    type: bool
    default: false
    version_added: 2.0.0
  rollback_duration:
    description:
      - Rollback timer as Go duration, for example C(30s) or C(1m30s).
      - With O(commit_request) it sets C(CommitRequest.rollback_duration).
        Alone, it changes the timer of the confirmed commit in progress
        (C(Commit.set_rollback_duration)).
    type: str
    version_added: 2.0.0
  dry_run:
    description:
      - Build the C(SetRequest) and return it as RV(request) without
        sending it. Check mode does the same.
    type: bool
    default: false
    version_added: 2.0.0
  backup:
    description:
      - Save the full configuration, as read before the change, to a file on
        the controller.
      - The file contains JSON. To restore it, replace C(/) with its content,
        as shown in the examples.
    type: bool
    default: false
  backup_options:
    description:
      - Options for O(backup). Ignored if O(backup=false).
    type: dict
    suboptions:
      filename:
        description:
          - File name of the backup. Defaults to
            C(<hostname>_config.<date>@<time>).
        type: str
      dir_path:
        description:
          - Directory of the backup. Defaults to C(backup) next to the
            playbook or role. Created if missing.
        type: path
notes:
  - Requires the P(nokia.openconfig.grpc#connection) connection.
  - In check mode and with O(dry_run=true) the request is built and returned
    but not sent, and C(changed) is always false. No backup file is written
    and no gNMI Get for O(backup) runs in check mode.
  - Commit operations without O(update), O(replace) or O(delete) (confirm,
    cancel, new rollback duration) always report C(changed).
requirements:
  - grpcio
  - protobuf
"""

EXAMPLES = """
# SR OS expects qualified member names in JSON_IETF container values;
# JSON accepts plain names
- name: Update location and contact in one container (SR OS)
  nokia.openconfig.gnmi_set:
    prefix: /configure
    encoding: json
    update:
      - path: system
        value:
          location: Antwerp
          contact: noc@example.com

- name: Update and replace in one transaction (SR Linux)
  nokia.openconfig.gnmi_set:
    update:
      - path: /system/information
        value:
          location: Antwerp
          contact: noc@example.com
    replace:
      - path: /interface[name=ethernet-1/1]/description
        value: uplink to spine1

- name: Enable LLDP and set the hostname using OpenConfig
  nokia.openconfig.gnmi_set:
    origin: openconfig
    update:
      - path: /lldp/config/enabled
        value: true
      - path: /system/config/hostname
        value: leaf1

- name: Apply a request file
  nokia.openconfig.gnmi_set:
    request_file: set-request.yml

- name: Start a confirmed commit, rolled back after 1 minute (SR OS)
  nokia.openconfig.gnmi_set:
    update:
      - path: /configure/system/location
        value: Antwerp
    commit_id: change-42
    commit_request: true
    rollback_duration: 1m

- name: Start a confirmed commit, rolled back after 1 minute (SR Linux)
  nokia.openconfig.gnmi_set:
    update:
      - path: /system/information/location
        value: Antwerp
    commit_id: change-42
    commit_request: true
    rollback_duration: 1m

- name: Confirm it
  nokia.openconfig.gnmi_set:
    commit_id: change-42
    commit_confirm: true

- name: Show a delete request without sending it (SR OS)
  nokia.openconfig.gnmi_set:
    delete:
      - /configure/port[port-id=1/1/c1/1]/description
    dry_run: true
  register: preview

- name: Show a delete request without sending it (SR Linux)
  nokia.openconfig.gnmi_set:
    delete:
      - /interface[name=ethernet-1/1]/description
    dry_run: true
  register: preview

- name: Save the configuration to a backup file
  nokia.openconfig.gnmi_set:
    backup: true
  register: backup

# The full restore with a replace of / is validated on SR Linux
- name: Restore the backup (SR Linux)
  nokia.openconfig.gnmi_set:
    replace:
      - path: /
        value: "{{ lookup('file', backup.backup_path) | from_json }}"
"""

RETURN = """
output:
  description:
    - The C(SetResponse) as JSON string, with paths as strings.
  returned: when the request was sent
  type: str
  sample: '{"prefix": "configure", "response": [{"op": "UPDATE", "path": "system/location"}], "timestamp": "2020-02-18T00:19:30.805600"}'
extensions:
  description:
    - Extensions returned in the C(SetResponse), using protobuf field names.
  returned: when the request was sent
  type: list
  elements: dict
  sample: [{"commit": {"id": "change-42", "commit": {"rollback_duration": "60s"}}}]
request:
  description:
    - The C(SetRequest) that would be sent, using protobuf field names.
  returned: check mode or O(dry_run=true)
  type: dict
diff:
  description:
    - Configuration of the affected paths before and after, as JSON strings.
  returned: when changed and diff mode is enabled
  type: dict
backup_path:
  description:
    - Full path of the backup file.
  returned: when O(backup=true)
  type: str
  sample: /playbooks/backup/leaf1_config.2025-01-01@10:00:00
filename:
  description:
    - Name of the backup file.
  returned: when O(backup=true) and O(backup_options.filename) is not set
  type: str
shortname:
  description:
    - Full path of the backup file without extension.
  returned: when O(backup=true) and O(backup_options.filename) is not set
  type: str
date:
  description:
    - Date of the backup.
  returned: when O(backup=true)
  type: str
time:
  description:
    - Time of the backup.
  returned: when O(backup=true)
  type: str
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text
from ansible_collections.nokia.openconfig.plugins.module_utils.gnmi import (
    ENCODINGS,
    GnmiError,
    load_set_request,
)
from ansible_collections.nokia.openconfig.plugins.module_utils.gnmi_ext import commit_extension
from ansible_collections.nokia.openconfig.plugins.module_utils.gnmi_module import (
    Rpc,
    normalize_enum,
    to_json,
)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _entries(module, name):
    result = []
    for entry in module.params[name] or []:
        item = dict(path=entry['path'], value=entry['value'])
        if entry.get('encoding'):
            item['encoding'] = normalize_enum(module, '%s.encoding' % name, ENCODINGS, entry['encoding'])
        result.append(item)
    return result


def _load_request_file(module, path):
    try:
        with open(path) as f:
            text = f.read()
    except (IOError, OSError) as exc:
        module.fail_json(msg="Unable to read request_file %s: %s" % (path, to_text(exc)))
    try:
        data = yaml.safe_load(text) if HAS_YAML else json.loads(text)
    except Exception as exc:
        module.fail_json(msg="Unable to parse request_file %s: %s" % (path, to_text(exc)))
    try:
        return load_set_request(data)
    except GnmiError as exc:
        module.fail_json(msg=to_text(exc))


_UNKNOWN = object()


def _snapshot(module, rpc, paths, prefix, target, origin):
    """Reads the affected configuration. Some targets reject a Get of a path
    that does not exist (yet), so a failed read does not fail the task."""
    if not paths:
        return None
    response = rpc.call('gnmiGet', dict(type='CONFIG', prefix=prefix, target=target, path=paths, origin=origin),
                        fail=False)
    if response is None:
        module.warn("Could not read the affected paths, changed is reported as true")
        return _UNKNOWN
    return response['output']


def main():
    entry_spec = dict(
        path=dict(type='str', required=True),
        value=dict(type='raw', required=True, aliases=['val']),
        encoding=dict(type='str'),
    )
    backup_spec = dict(filename=dict(type='str'), dir_path=dict(type='path'))
    argument_spec = dict(
        prefix=dict(type='str'),
        origin=dict(type='str'),
        target=dict(type='str'),
        update=dict(type='list', elements='dict', options=entry_spec),
        replace=dict(type='list', elements='dict', options=entry_spec),
        delete=dict(type='list', elements='str'),
        request_file=dict(type='path'),
        encoding=dict(type='str'),
        commit_id=dict(type='str'),
        commit_request=dict(type='bool', default=False),
        commit_confirm=dict(type='bool', default=False),
        commit_cancel=dict(type='bool', default=False),
        rollback_duration=dict(type='str'),
        dry_run=dict(type='bool', default=False),
        backup=dict(type='bool', default=False),
        backup_options=dict(type='dict', options=backup_spec),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    p = module.params

    update = _entries(module, 'update')
    replace = _entries(module, 'replace')
    delete = list(p['delete'] or [])
    if p['request_file']:
        loaded = _load_request_file(module, p['request_file'])
        update.extend(loaded['update'])
        replace.extend(loaded['replace'])
        delete.extend(loaded['delete'])

    commit = dict(commit_id=p['commit_id'], commit_request=p['commit_request'], commit_confirm=p['commit_confirm'],
                  commit_cancel=p['commit_cancel'], rollback_duration=p['rollback_duration'])
    try:
        has_commit = commit_extension(p['commit_id'], p['commit_request'], p['commit_confirm'],
                                      p['commit_cancel'], p['rollback_duration']) is not None
    except GnmiError as exc:
        module.fail_json(msg=to_text(exc))

    has_changes = bool(update or replace or delete)
    if not has_changes and not has_commit and not p['backup']:
        module.fail_json(msg="Nothing to do: one of update, replace, delete, request_file, "
                             "a commit operation or backup is required")

    request = dict(prefix=p['prefix'], origin=p['origin'], target=p['target'], update=update, replace=replace,
                   delete=delete, encoding=normalize_enum(module, 'encoding', ('JSON', 'JSON_IETF')), **commit)
    rpc = Rpc(module)
    result = dict(changed=False)

    if module.check_mode or p['dry_run']:
        if has_changes or has_commit:
            result['request'] = rpc('gnmiSet', dry_run=True, **request)['request']
        module.exit_json(**result)

    paths = [e['path'] for e in update] + [e['path'] for e in replace] + delete
    full = None
    if p['backup']:
        full = rpc('gnmiGet', type='CONFIG', target=p['target'], path=['/'], origin=p['origin'])['output']
        result['__backup__'] = to_json(full)

    if has_changes or has_commit:
        if full is not None:
            before = full
        else:
            before = _snapshot(module, rpc, paths, p['prefix'], p['target'], p['origin'])

        response = rpc('gnmiSet', **request)
        result['output'] = to_json(response['output'])
        result['extensions'] = response['extensions']

        if full is not None:
            after = rpc('gnmiGet', type='CONFIG', target=p['target'], path=['/'], origin=p['origin'])['output']
        else:
            after = _snapshot(module, rpc, paths, p['prefix'], p['target'], p['origin'])

        known = before is not _UNKNOWN and after is not _UNKNOWN
        if has_changes and known:
            result['changed'] = before != after
        else:
            result['changed'] = True
        if result['changed'] and module._diff and has_changes and known:
            result['diff'] = dict(before=to_json(before), after=to_json(after))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
