# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import json

import pytest

from ansible_collections.nokia.openconfig.plugins.module_utils import gnmi
from ansible_collections.nokia.openconfig.plugins.module_utils.gnmi import GnmiError


def b64(value):
    return base64.b64encode(json.dumps(value).encode()).decode()


@pytest.mark.parametrize('value, expected', [
    ('30s', 30 * 10 ** 9),
    ('1m30s', 90 * 10 ** 9),
    ('1h', 3600 * 10 ** 9),
    ('500ms', 5 * 10 ** 8),
    ('1.5s', 15 * 10 ** 8),
    ('10us', 10 ** 4),
    ('10\u00b5s', 10 ** 4),
    ('7ns', 7),
    ('0s', 0),
    (5, 5 * 10 ** 9),
    ('5', 5 * 10 ** 9),
    (0.25, 25 * 10 ** 7),
    (None, None),
])
def test_parse_duration(value, expected):
    assert gnmi.parse_duration(value) == expected


@pytest.mark.parametrize('value', ['', 'abc', '1x', '30s5', 's', -1, True])
def test_parse_duration_invalid(value):
    with pytest.raises(GnmiError):
        gnmi.parse_duration(value)


@pytest.mark.parametrize('ns, expected', [
    (30 * 10 ** 9, '30s'),
    (15 * 10 ** 8, '1.5s'),
    (1, '0.000000001s'),
    (0, '0s'),
])
def test_duration_to_proto(ns, expected):
    assert gnmi.duration_to_proto(ns) == expected


def test_encode_path_keys_and_slashes():
    assert gnmi.encode_path('/interface[name=ethernet-1/1]/subinterface[index=0]') == {
        'elem': [{'name': 'interface', 'key': {'name': 'ethernet-1/1'}},
                 {'name': 'subinterface', 'key': {'index': '0'}}],
    }


def test_encode_path_multiple_keys_and_escapes():
    path = gnmi.encode_path('a[x=1][y=a\\]b]/c')
    assert path['elem'][0] == {'name': 'a', 'key': {'x': '1', 'y': 'a]b'}}


def test_encode_path_ipv6_key_value():
    path = gnmi.encode_path('/network-instance[name=default]/route[prefix=2001:db8::/64]')
    assert path['elem'][1] == {'name': 'route', 'key': {'prefix': '2001:db8::/64'}}
    assert 'origin' not in path


def test_encode_path_origin_forms():
    assert gnmi.encode_path('openconfig:/interfaces')['origin'] == 'openconfig'
    legacy = gnmi.encode_path('/oc:interfaces/interface')
    assert legacy['origin'] == 'oc'
    assert legacy['elem'][0]['name'] == 'interfaces'


def test_encode_path_multi_prefix_preserves_root_origin():
    xpath = '/openconfig-interfaces:interfaces/interface[name=eth0]/openconfig-if-ip:ipv4'
    encoded = gnmi.encode_path(xpath)
    assert encoded == {
        'origin': 'openconfig-interfaces',
        'elem': [
            {'name': 'interfaces'},
            {'name': 'interface', 'key': {'name': 'eth0'}},
            {'name': 'ipv4'},
        ],
    }
    assert gnmi.encode_path(gnmi.decode_path(encoded)) == encoded
    unprefixed_root = gnmi.encode_path('/interfaces/interface[name=eth0]/openconfig-if-ip:ipv4')
    assert 'origin' not in unprefixed_root
    assert unprefixed_root['elem'][2]['name'] == 'ipv4'
    split_req = gnmi.build_get_request(
        prefix='/openconfig-interfaces:interfaces/interface[name=eth0]',
        path=['openconfig-if-ip:ipv4/addresses'],
    )
    assert split_req['prefix'] == {
        'origin': 'openconfig-interfaces',
        'elem': [{'name': 'interfaces'}, {'name': 'interface', 'key': {'name': 'eth0'}}],
    }
    assert split_req['path'] == [{'elem': [{'name': 'ipv4'}, {'name': 'addresses'}]}]


def test_encode_path_explicit_origin_keeps_qualified_names():
    path = gnmi.encode_path('rfc7951:/Cisco-IOS-XE-native:native/hostname')
    assert path['origin'] == 'rfc7951'
    assert [e['name'] for e in path['elem']] == ['Cisco-IOS-XE-native:native', 'hostname']


def test_encode_path_origin_argument():
    path = gnmi.encode_path('/Cisco-IOS-XE-native:native/hostname', origin='rfc7951')
    assert path['origin'] == 'rfc7951'
    assert path['elem'][0]['name'] == 'Cisco-IOS-XE-native:native'
    assert gnmi.encode_path('openconfig:/system', origin='rfc7951')['origin'] == 'openconfig'


def test_encode_path_qualified_without_origin():
    path = gnmi.encode_path('/oc:interfaces', qualified=True)
    assert 'origin' not in path
    assert path['elem'][0]['name'] == 'oc:interfaces'


def test_build_get_request_origin_on_paths():
    request = gnmi.build_get_request(path=['/system', 'rfc7951:/native', ''], origin='openconfig')
    assert 'prefix' not in request
    assert [p.get('origin') for p in request['path']] == ['openconfig', 'rfc7951', 'openconfig']


def test_build_get_request_origin_on_prefix():
    request = gnmi.build_get_request(path=['config/hostname', 'state'], prefix='/system', origin='openconfig')
    assert request['prefix']['origin'] == 'openconfig'
    assert all('origin' not in p for p in request['path'])


def test_build_get_request_target_only_prefix_puts_origin_on_paths():
    request = gnmi.build_get_request(path=['/system'], target='dut', origin='openconfig')
    assert request['prefix'] == {'target': 'dut'}
    assert request['path'][0]['origin'] == 'openconfig'


def test_build_get_request_prefix_origin_wins():
    request = gnmi.build_get_request(path=['Cisco-IOS-XE-native:native'], prefix='rfc7951:/', origin='openconfig')
    assert request['prefix'] == {'origin': 'rfc7951'}
    assert request['path'][0] == {'elem': [{'name': 'Cisco-IOS-XE-native:native'}]}
    request = gnmi.build_get_request(path=['hostname'], prefix='rfc7951:/Cisco-IOS-XE-native:native',
                                     origin='openconfig')
    assert request['prefix']['origin'] == 'rfc7951'
    assert request['prefix']['elem'][0]['name'] == 'Cisco-IOS-XE-native:native'
    assert 'origin' not in request['path'][0]


def test_build_set_request_origin():
    request = gnmi.build_set_request(update=[{'path': '/lldp/config/enabled', 'value': True}],
                                     replace=[{'path': 'rfc7951:/x', 'value': 1}],
                                     delete=['/system/config/motd-banner'], origin='openconfig')
    assert request['update'][0]['path']['origin'] == 'openconfig'
    assert request['replace'][0]['path']['origin'] == 'rfc7951'
    assert request['delete'][0]['origin'] == 'openconfig'


def test_build_subscription_list_origin():
    request = gnmi.build_subscription_list(subscription=[{'path': '/a'}, {'path': 'native:/b'}], origin='openconfig')
    assert [s['path']['origin'] for s in request['subscription']] == ['openconfig', 'native']


def test_build_requests_without_origin_are_unchanged():
    assert gnmi.build_get_request(path=['/oc:interfaces'])['path'][0]['origin'] == 'oc'
    assert 'origin' not in gnmi.build_set_request(delete=['/a'])['delete'][0]


@pytest.mark.parametrize('path', ['', '/'])
def test_encode_root(path):
    assert gnmi.encode_path(path) == {}


def test_encode_path_target():
    assert gnmi.encode_path('', target='dut') == {'target': 'dut'}


@pytest.mark.parametrize('path', ['/a[x=1', '/a[x]', '/a[=1]', '/[x=1]', '/a:b:c', '/oc:a/b:c:d', '/a/:b', '/a/b:'])
def test_encode_path_invalid(path):
    with pytest.raises(GnmiError):
        gnmi.encode_path(path)


@pytest.mark.parametrize('xpath, expected', [
    ('/interface[name=ethernet-1/1]/description', 'interface[name=ethernet-1/1]/description'),
    ('openconfig:/interfaces/interface[name=a]', 'openconfig:/interfaces/interface[name=a]'),
    ('/a[k=x\\]y]', 'a[k=x\\]y]'),
    ('/', ''),
])
def test_path_round_trip(xpath, expected):
    assert gnmi.decode_path(gnmi.encode_path(xpath)) == expected
    assert gnmi.encode_path(gnmi.decode_path(gnmi.encode_path(xpath))) == gnmi.encode_path(xpath)


def test_decode_legacy_element():
    assert gnmi.decode_path({'element': ['a', 'b']}) == 'a/b'


@pytest.mark.parametrize('value, encoding, expected', [
    ({'a': 1}, 'JSON_IETF', {'jsonIetfVal': b64({'a': 1})}),
    ('x', 'json', {'jsonVal': b64('x')}),
    ('x', 'ascii', {'asciiVal': 'x'}),
    (5, 'string', {'stringVal': '5'}),
    ('-3', 'int', {'intVal': '-3'}),
    (3, 'uint', {'uintVal': '3'}),
    ('True', 'bool', {'boolVal': True}),
    (False, 'bool', {'boolVal': False}),
    ('1.5', 'float', {'doubleVal': 1.5}),
    ('ab', 'bytes', {'bytesVal': 'YWI='}),
])
def test_encode_value(value, encoding, expected):
    assert gnmi.encode_value(value, encoding) == expected


@pytest.mark.parametrize('value, encoding', [(-1, 'UINT'), ('yes', 'BOOL'), (1, 'PROTO')])
def test_encode_value_invalid(value, encoding):
    with pytest.raises(GnmiError):
        gnmi.encode_value(value, encoding)


@pytest.mark.parametrize('val, expected', [
    ({'jsonIetfVal': b64({'a': [1]})}, {'a': [1]}),
    ({'jsonVal': b64(1)}, 1),
    ({'stringVal': 'x'}, 'x'),
    ({'asciiVal': 'x'}, 'x'),
    ({'boolVal': False}, False),
    ({'intVal': '-4'}, -4),
    ({'uintVal': '4'}, 4),
    ({'doubleVal': 0.5}, 0.5),
    ({'decimalVal': {'digits': '1234', 'precision': 2}}, 12.34),
    ({'leaflistVal': {'element': [{'stringVal': 'a'}, {'uintVal': '2'}]}}, ['a', 2]),
    ({}, None),
])
def test_decode_value(val, expected):
    assert gnmi.decode_value(val) == expected


def test_build_get_request_defaults():
    request = gnmi.build_get_request()
    assert request == {'path': [{}], 'type': 'ALL', 'encoding': 'JSON_IETF'}


def test_build_get_request_full():
    request = gnmi.build_get_request(path=['/a'], prefix='/x', target='t', model='m', type='state', encoding='json')
    assert request['prefix'] == {'elem': [{'name': 'x'}], 'target': 't'}
    assert request['type'] == 'STATE'
    assert request['encoding'] == 'JSON'
    assert request['use_models'] == [{'name': 'm'}]


def test_build_get_request_invalid_type():
    with pytest.raises(GnmiError):
        gnmi.build_get_request(type='RUNNING')


def test_build_set_request():
    request = gnmi.build_set_request(
        prefix='/configure',
        update=[{'path': 'system/name', 'value': 'r1'}, {'path': 'system/x', 'value': 2, 'encoding': 'UINT'}],
        replace=[{'path': 'system/y', 'value': {'a': 1}}],
        delete=['system/z'],
        encoding='JSON',
    )
    assert request['delete'] == [{'elem': [{'name': 'system'}, {'name': 'z'}]}]
    assert request['update'][0]['val'] == {'jsonVal': b64('r1')}
    assert request['update'][1]['val'] == {'uintVal': '2'}
    assert request['replace'][0]['val'] == {'jsonVal': b64({'a': 1})}


def test_build_set_request_value_false_is_kept():
    request = gnmi.build_set_request(update=[{'path': '/a', 'value': False}])
    assert request['update'][0]['val'] == {'jsonIetfVal': b64(False)}


@pytest.mark.parametrize('entry', [{'value': 1}, {'path': '/a'}, 'x'])
def test_build_set_request_invalid(entry):
    with pytest.raises(GnmiError):
        gnmi.build_set_request(update=[entry])


def test_load_set_request():
    data = gnmi.load_set_request({
        'updates': [{'path': '/a', 'value': 1, 'encoding': 'json'}],
        'replaces': [{'value': {'b': 2}}],
        'deletes': ['/c'],
    })
    assert data == {
        'update': [{'path': '/a', 'value': 1, 'encoding': 'json'}],
        'replace': [{'path': '/', 'value': {'b': 2}}],
        'delete': ['/c'],
    }


@pytest.mark.parametrize('data', [[], {'update': []}, {'updates': [{'path': '/a'}]}, {'deletes': '/a'}])
def test_load_set_request_invalid(data):
    with pytest.raises(GnmiError):
        gnmi.load_set_request(data)


def test_build_subscription_list_stream():
    request = gnmi.build_subscription_list(
        path=['/a', '/b'], mode='stream', stream_mode='on_change', sample_interval='10s',
        heartbeat_interval='1m', suppress_redundant=True, updates_only=True, qos=10, prefix='/p')
    assert request['mode'] == 'STREAM'
    assert request['subscription'][1] == {
        'path': {'elem': [{'name': 'b'}]},
        'mode': 'ON_CHANGE',
        'sample_interval': str(10 * 10 ** 9),
        'heartbeat_interval': str(60 * 10 ** 9),
        'suppress_redundant': True,
    }
    assert request['updates_only'] is True
    assert request['qos'] == {'marking': 10}
    assert request['prefix'] == {'elem': [{'name': 'p'}]}


def test_build_subscription_list_once_ignores_stream_fields():
    request = gnmi.build_subscription_list(path=['/a'], mode='ONCE', stream_mode='ON_CHANGE')
    assert request['subscription'] == [{'path': {'elem': [{'name': 'a'}]}}]


def test_build_subscription_list_qos_zero():
    assert gnmi.build_subscription_list(path=['/a'], qos=0)['qos'] == {'marking': 0}


def test_build_subscription_list_per_entry():
    request = gnmi.build_subscription_list(subscription=[
        {'path': '/a', 'stream_mode': 'SAMPLE', 'sample_interval': '1s'},
        {'path': '/b', 'stream_mode': 'ON_CHANGE', 'heartbeat_interval': '2s', 'suppress_redundant': True},
    ])
    assert request['subscription'][0]['sample_interval'] == str(10 ** 9)
    assert request['subscription'][1]['mode'] == 'ON_CHANGE'
    assert request['subscription'][1]['heartbeat_interval'] == str(2 * 10 ** 9)
    assert request['subscription'][1]['suppress_redundant'] is True


def test_build_subscription_list_removed_keys():
    with pytest.raises(GnmiError, match='removed in 2.0.0: mode, sampleInterval. Use stream_mode, sample_interval'):
        gnmi.build_subscription_list(subscription=[{'path': '/a', 'mode': 'SAMPLE', 'sampleInterval': 10 ** 9}])


def test_build_set_request_removed_val():
    with pytest.raises(GnmiError, match="'val' was renamed to 'value'"):
        gnmi.build_set_request(update=[{'path': '/a', 'val': 1}])


@pytest.mark.parametrize('kwargs', [
    {},
    {'path': ['/a'], 'subscription': [{'path': '/b'}]},
    {'path': ['/a'], 'mode': 'SAMPLE'},
    {'path': ['/a'], 'stream_mode': 'ONCE'},
    {'subscription': [{'mode': 'SAMPLE'}]},
])
def test_build_subscription_list_invalid(kwargs):
    with pytest.raises(GnmiError):
        gnmi.build_subscription_list(**kwargs)


def _update(path, value, prefix=None):
    notification = {'update': [{'path': gnmi.encode_path(path), 'val': {'jsonIetfVal': b64(value)}}]}
    if prefix:
        notification['prefix'] = gnmi.encode_path(prefix)
    return notification


def test_merge_notifications_lists_and_prefix():
    raw = [
        _update('/interface[name=e1]', {'description': 'a'}),
        _update('/interface[name=e2]/description', 'b'),
        _update('description', 'c', prefix='/interface[name=e1]'),
    ]
    assert gnmi.merge_notifications(raw) == {
        'interface': [{'name': 'e1', 'description': 'c'}, {'name': 'e2', 'description': 'b'}],
    }


def test_merge_notifications_root_value():
    assert gnmi.merge_notifications([_update('/', {'a': 1})]) == {'a': 1}


def test_merge_notifications_prefix_only():
    raw = [{'prefix': gnmi.encode_path('/system/name'),
            'update': [{'path': {}, 'val': {'stringVal': 'r1'}}]}]
    assert gnmi.merge_notifications(raw) == {'system': {'name': 'r1'}}


def test_merge_skips_sync_and_extension_only_messages():
    raw = [
        {'update': _update('/a', 1)},
        {'extension': [{'configSubscription': {'syncDone': {'done': True}}}]},
        {'syncResponse': True},
        {'update': _update('/b', 2)},
    ]
    assert gnmi.merge_notifications(raw) == {'a': 1, 'b': 2}


def test_notification_values():
    raw = [_update('/a', 1), _update('/b', {'c': 2})]
    assert gnmi.notification_values(raw) == [1, {'c': 2}]


def test_simplify_notification():
    entry = {'update': {
        'timestamp': '1700000000000000000',
        'prefix': gnmi.encode_path('/interface[name=e1]'),
        'update': [{'path': gnmi.encode_path('description'), 'val': {'stringVal': 'x'}}],
        'delete': [gnmi.encode_path('mtu')],
    }}
    result = gnmi.simplify_notification(entry)
    assert result['prefix'] == '/interface[name=e1]'
    assert result['values'] == {'description': 'x'}
    assert result['deletes'] == ['mtu']
    assert result['timestamp'].startswith('2023-11-1')


def test_simplify_notification_origin_prefix():
    entry = {'update': {'prefix': gnmi.encode_path('openconfig:/interfaces')}}
    assert gnmi.simplify_notification(entry)['prefix'] == 'openconfig:/interfaces'


def test_simplify_notification_ignores_sync():
    assert gnmi.simplify_notification({'syncResponse': True}) is None


def test_simplify_set_response():
    response = {
        'prefix': gnmi.encode_path('/configure'),
        'timestamp': '1700000000000000000',
        'response': [{'path': gnmi.encode_path('system/name'), 'op': 'UPDATE', 'timestamp': '1'}],
        'extension': [{'commit': {'id': 'c1'}}],
    }
    result = gnmi.simplify_set_response(response)
    assert result['prefix'] == 'configure'
    assert result['response'] == [{'path': 'system/name', 'op': 'UPDATE'}]
    assert 'extension' not in result
