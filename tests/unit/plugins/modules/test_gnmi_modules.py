# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

from ansible.module_utils.connection import ConnectionError

from ansible_collections.nokia.openconfig.plugins.modules import gnmi_capabilities
from ansible_collections.nokia.openconfig.plugins.modules import gnmi_get
from ansible_collections.nokia.openconfig.plugins.modules import gnmi_set
from ansible_collections.nokia.openconfig.plugins.modules import gnmi_subscribe


def get(output):
    return {'output': output, 'extensions': []}


# gnmi_capabilities

def test_capabilities(connection, run_module):
    connection.responses['gnmiCapabilities'] = {
        'gNMIVersion': '0.10.0',
        'supportedEncodings': ['JSON_IETF'],
        'supportedModels': [{'name': 'nokia-conf', 'organization': 'Nokia', 'version': '25.7.R2'}],
    }
    result = run_module(gnmi_capabilities.main, {})
    assert result['gnmi_version'] == '0.10.0'
    assert result['encodings'] == ['JSON_IETF']
    assert result['models'][0]['name'] == 'nokia-conf'
    assert result['output']['gNMIVersion'] == '0.10.0'
    assert result['changed'] is False


# gnmi_get

def test_get_defaults_and_normalization(connection, run_module):
    connection.responses['gnmiGet'] = {'output': {'a': 1}, 'extensions': [{'depth': {'level': 1}}]}
    result = run_module(gnmi_get.main, {'path': ['/a'], 'type': 'config', 'encoding': 'json_ietf', 'depth': 1})
    method, kwargs = connection.calls[0]
    assert method == 'gnmiGet'
    assert kwargs['type'] == 'CONFIG'
    assert kwargs['encoding'] == 'JSON_IETF'
    assert kwargs['depth'] == 1
    assert json.loads(result['output']) == {'a': 1}
    assert result['extensions'] == [{'depth': {'level': 1}}]
    assert result['changed'] is False


def test_get_default_type_is_all(connection, run_module):
    connection.responses['gnmiGet'] = get({})
    run_module(gnmi_get.main, {})
    assert connection.calls[0][1]['type'] == 'ALL'
    assert connection.calls[0][1]['path'] == ['']


def test_get_origin_is_passed(connection, run_module):
    connection.responses['gnmiGet'] = get({})
    run_module(gnmi_get.main, {'path': ['/system'], 'origin': 'openconfig'})
    assert connection.calls[0][1]['origin'] == 'openconfig'
    connection.calls.clear()
    run_module(gnmi_get.main, {'path': ['/system']})
    assert connection.calls[0][1]['origin'] is None


def test_get_invalid_type(connection, run_module):
    result = run_module(gnmi_get.main, {'type': 'running'})
    assert result['failed']
    assert 'ALL, CONFIG, STATE, OPERATIONAL' in result['msg']
    assert connection.calls == []


def test_get_negative_depth(connection, run_module):
    result = run_module(gnmi_get.main, {'depth': -1})
    assert result['failed']


# gnmi_set

def test_set_changed_and_diff(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 2})]
    connection.responses['gnmiSet'] = {'output': {'response': [{'op': 'UPDATE', 'path': 'a'}]}, 'extensions': []}
    result = run_module(gnmi_set.main, {'prefix': '/p', 'update': [{'path': 'a', 'value': 2}], 'delete': ['b']},
                        diff=True)
    assert connection.methods() == ['gnmiGet', 'gnmiSet', 'gnmiGet']
    snapshot = connection.calls[0][1]
    assert snapshot['path'] == ['a', 'b']
    assert snapshot['prefix'] == '/p'
    assert snapshot['type'] == 'CONFIG'
    request = connection.calls[1][1]
    assert request['update'] == [{'path': 'a', 'value': 2}]
    assert request['delete'] == ['b']
    assert result['changed'] is True
    assert json.loads(result['diff']['before']) == {'a': 1}
    assert json.loads(result['output'])['response'][0]['op'] == 'UPDATE'


def test_set_origin_is_used_for_set_snapshots_and_backup(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 2})]
    connection.responses['gnmiSet'] = get({})
    run_module(gnmi_set.main, {'origin': 'openconfig', 'update': [{'path': 'a', 'value': 2}]})
    assert [c[1]['origin'] for c in connection.calls] == ['openconfig'] * 3
    connection.calls.clear()
    connection.responses['gnmiGet'] = get({})
    run_module(gnmi_set.main, {'origin': 'openconfig', 'backup': True})
    assert connection.calls[0][1]['origin'] == 'openconfig'


def test_set_unchanged(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 1})]
    connection.responses['gnmiSet'] = get({})
    result = run_module(gnmi_set.main, {'update': [{'path': 'a', 'value': 1}]})
    assert result['changed'] is False


def test_set_unreadable_path_reports_changed(connection, run_module):
    def not_found(**kwargs):
        raise ConnectionError('gRPC NOT_FOUND: path not found', code=-32603)
    connection.responses['gnmiGet'] = not_found
    connection.responses['gnmiSet'] = get({})
    result = run_module(gnmi_set.main, {'delete': ['/a']}, diff=True)
    assert connection.methods() == ['gnmiGet', 'gnmiSet', 'gnmiGet']
    assert result['changed'] is True
    assert 'diff' not in result
    assert 'NOT_FOUND' in json.dumps(result['warnings'])


def test_set_rpc_error_fails(connection, run_module):
    def rejected(**kwargs):
        raise ConnectionError('gRPC INVALID_ARGUMENT: bad value', code=-32603)
    connection.responses['gnmiGet'] = [get({}), get({})]
    connection.responses['gnmiSet'] = rejected
    result = run_module(gnmi_set.main, {'update': [{'path': 'a', 'value': 1}]})
    assert result['failed']
    assert result['msg'] == 'gRPC INVALID_ARGUMENT: bad value'


def test_set_val_alias(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 2})]
    connection.responses['gnmiSet'] = get({})
    result = run_module(gnmi_set.main, {
        'update': [{'path': 'a', 'val': 2}],
        'replace': [{'path': 'b', 'val': {'c': 3}}],
    })
    assert result['changed'] is True
    request = connection.calls[1][1]
    assert request['update'] == [{'path': 'a', 'value': 2}]
    assert request['replace'] == [{'path': 'b', 'value': {'c': 3}}]


def test_rpc_socket_connection_error_without_code(connection, run_module, monkeypatch):
    def socket_down(**kwargs):
        raise ConnectionError('unable to connect to socket /tmp/ansible-conn.sock')
    connection.responses['gnmiCapabilities'] = socket_down
    result = run_module(gnmi_capabilities.main, {})
    assert result['failed'] is True
    assert result['code'] == -1
    assert 'unable to connect to socket' in result['msg']

    connection.responses['gnmiGet'] = socket_down
    connection.responses['gnmiSet'] = get({})
    warn_result = run_module(gnmi_set.main, {'delete': ['/a']})
    assert warn_result['changed'] is True
    assert 'unable to connect to socket' in json.dumps(warn_result['warnings'])

    def init_down(socket_path):
        raise ConnectionError('socket setup failed')
    monkeypatch.setattr(gnmi_set.Rpc, '_connection', None, raising=False)
    from ansible_collections.nokia.openconfig.plugins.module_utils import gnmi_module
    monkeypatch.setattr(gnmi_module, 'Connection', init_down)
    init_result = run_module(gnmi_capabilities.main, {})
    assert init_result['failed'] is True
    assert init_result['code'] == -1
    assert init_result['msg'] == 'socket setup failed'


def test_set_check_mode_returns_request(connection, run_module):
    connection.responses['gnmiSet'] = {'request': {'update': []}}
    result = run_module(gnmi_set.main, {'update': [{'path': 'a', 'value': 1}]}, check_mode=True)
    assert connection.methods() == ['gnmiSet']
    assert connection.calls[0][1]['dry_run'] is True
    assert result['request'] == {'update': []}
    assert result['changed'] is False


def test_set_check_mode_backup_only_skips_get(connection, run_module):
    result = run_module(gnmi_set.main, {'backup': True}, check_mode=True)
    assert connection.calls == []
    assert result['changed'] is False
    assert '__backup__' not in result


def test_set_check_mode_with_update_skips_backup_get(connection, run_module):
    connection.responses['gnmiSet'] = {'request': {'update': [{'path': 'a'}]}}
    result = run_module(gnmi_set.main, {'backup': True, 'update': [{'path': 'a', 'value': 1}]}, check_mode=True)
    assert connection.methods() == ['gnmiSet']
    assert 'gnmiGet' not in connection.methods()
    assert result['changed'] is False


def test_set_dry_run(connection, run_module):
    connection.responses['gnmiSet'] = {'request': {'delete': [{}]}}
    result = run_module(gnmi_set.main, {'delete': ['/a'], 'dry_run': True})
    assert connection.calls[0][1]['dry_run'] is True
    assert result['request'] == {'delete': [{}]}


def test_set_commit_request(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 2})]
    connection.responses['gnmiSet'] = {'output': {}, 'extensions': [{'commit': {'id': 'c1'}}]}
    result = run_module(gnmi_set.main, {'update': [{'path': 'a', 'value': 2}], 'commit_id': 'c1',
                                        'commit_request': True, 'rollback_duration': '30s'})
    request = connection.calls[1][1]
    assert request['commit_id'] == 'c1'
    assert request['commit_request'] is True
    assert request['rollback_duration'] == '30s'
    assert result['extensions'] == [{'commit': {'id': 'c1'}}]


def test_set_commit_confirm_only(connection, run_module):
    connection.responses['gnmiSet'] = get({})
    result = run_module(gnmi_set.main, {'commit_id': 'c1', 'commit_confirm': True})
    assert connection.methods() == ['gnmiSet']
    assert result['changed'] is True


def test_set_commit_validation(connection, run_module):
    result = run_module(gnmi_set.main, {'commit_confirm': True})
    assert result['failed']
    assert 'commit_id is required' in result['msg']
    result = run_module(gnmi_set.main, {'commit_id': 'c', 'commit_confirm': True, 'commit_cancel': True})
    assert 'mutually exclusive' in result['msg']
    result = run_module(gnmi_set.main, {'commit_id': 'c', 'rollback_duration': 'soon'})
    assert 'Invalid duration' in result['msg']
    assert connection.calls == []


def test_set_nothing_to_do(connection, run_module):
    result = run_module(gnmi_set.main, {})
    assert result['failed']
    assert 'Nothing to do' in result['msg']


def test_set_invalid_encoding(connection, run_module):
    result = run_module(gnmi_set.main, {'update': [{'path': 'a', 'value': 1, 'encoding': 'proto'}]})
    assert result['failed']
    assert 'update.encoding' in result['msg']


def test_set_request_file(connection, run_module, tmp_path):
    request_file = tmp_path / 'set.yml'
    request_file.write_text("updates:\n  - path: /a\n    value: 1\n    encoding: uint\nreplaces:\n  - value: {b: 2}\n"
                            "deletes:\n  - /c\n")
    connection.responses['gnmiGet'] = [get({}), get({'a': 1})]
    connection.responses['gnmiSet'] = get({})
    run_module(gnmi_set.main, {'request_file': str(request_file), 'delete': ['/d']})
    request = connection.calls[1][1]
    assert request['update'] == [{'path': '/a', 'value': 1, 'encoding': 'uint'}]
    assert request['replace'] == [{'path': '/', 'value': {'b': 2}}]
    assert request['delete'] == ['/d', '/c']


def test_set_request_file_invalid(connection, run_module, tmp_path):
    request_file = tmp_path / 'set.yml'
    request_file.write_text("update: []\n")
    result = run_module(gnmi_set.main, {'request_file': str(request_file)})
    assert result['failed']
    assert 'Unsupported keys' in result['msg']


def test_set_backup_only(connection, run_module):
    connection.responses['gnmiGet'] = get({'system': {'name': 'r1'}})
    result = run_module(gnmi_set.main, {'backup': True})
    assert connection.methods() == ['gnmiGet']
    assert connection.calls[0][1]['path'] == ['/']
    assert result['changed'] is False


def test_set_backup_with_change_uses_full_snapshots(connection, run_module):
    connection.responses['gnmiGet'] = [get({'a': 1}), get({'a': 2})]
    connection.responses['gnmiSet'] = get({})
    result = run_module(gnmi_set.main, {'backup': True, 'update': [{'path': 'a', 'value': 2}]})
    assert connection.methods() == ['gnmiGet', 'gnmiSet', 'gnmiGet']
    assert result['changed'] is True


# gnmi_subscribe

def test_subscribe_check_mode_skips_rpc(connection, run_module):
    result = run_module(gnmi_subscribe.main, {'path': ['/a'], 'mode': 'once'}, check_mode=True)
    assert connection.calls == []
    assert result['skipped'] is True
    assert result['changed'] is False


def test_subscribe_defaults_and_normalization(connection, run_module):
    connection.responses['gnmiSubscribe'] = {'output': [{'values': {'a': 1}}], 'extensions': []}
    result = run_module(gnmi_subscribe.main, {'path': ['/a'], 'stream_mode': 'on_change', 'sample_interval': '1s'})
    kwargs = connection.calls[0][1]
    assert kwargs['mode'] == 'STREAM'
    assert kwargs['stream_mode'] == 'ON_CHANGE'
    assert kwargs['sample_interval'] == '1s'
    assert kwargs['config_subscription'] is False
    assert kwargs['duration'] is None
    assert json.loads(result['output']) == [{'values': {'a': 1}}]


def test_subscribe_removed_subscription_keys(connection, run_module):
    result = run_module(gnmi_subscribe.main, {
        'subscription': [{'path': '/a', 'mode': 'SAMPLE', 'sampleInterval': 1000000000}]})
    assert result['failed']
    assert result['msg'] == ('Subscription keys removed in 2.0.0: mode, sampleInterval. '
                             'Use stream_mode, sample_interval instead')
    assert connection.calls == []


def test_subscribe_origin_is_passed(connection, run_module):
    connection.responses['gnmiSubscribe'] = get({})
    run_module(gnmi_subscribe.main, {'path': ['/a'], 'origin': 'openconfig', 'mode': 'once'})
    assert connection.calls[0][1]['origin'] == 'openconfig'


def test_subscribe_subscription_list(connection, run_module):
    connection.responses['gnmiSubscribe'] = get({})
    run_module(gnmi_subscribe.main, {'subscription': [{'path': '/a', 'stream_mode': 'sample', 'sample_interval': '1s'}]})
    assert connection.calls[0][1]['subscription'] == [{'path': '/a', 'stream_mode': 'sample', 'sample_interval': '1s'}]


def test_module_without_grpc_connection(run_module):
    result = run_module(gnmi_get.main, {}, socket_path=None)
    assert result['failed']
    assert 'ansible_connection: nokia.openconfig.grpc' in result['msg']


def test_subscribe_requires_path_or_subscription(connection, run_module):
    result = run_module(gnmi_subscribe.main, {})
    assert result['failed']
    result = run_module(gnmi_subscribe.main, {'path': ['/a'], 'subscription': [{'path': '/b'}]})
    assert 'mutually exclusive' in result['msg']


def test_subscribe_validation(connection, run_module):
    assert run_module(gnmi_subscribe.main, {'path': ['/a'], 'mode': 'sample'})['failed']
    assert run_module(gnmi_subscribe.main, {'path': ['/a'], 'sample_interval': 'fast'})['failed']
    assert run_module(gnmi_subscribe.main, {'path': ['/a'], 'duration': 0})['failed']
    assert run_module(gnmi_subscribe.main, {'subscription': [{'path': '/a', 'interval': 1}]})['failed']
    assert run_module(gnmi_subscribe.main, {'subscription': [{'stream_mode': 'SAMPLE'}]})['failed']
    assert connection.calls == []
