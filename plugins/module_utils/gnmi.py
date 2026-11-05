# (c) 2020-2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

"""
Protocol-independent helpers for gNMI.

Everything here works on the dict form of gNMI messages produced by
google.protobuf.json_format, so it can be unit-tested without grpcio,
protobuf or a device.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import datetime
import json
import re

ENCODINGS = ('JSON', 'JSON_IETF', 'ASCII', 'STRING', 'INT', 'UINT', 'BOOL', 'FLOAT', 'BYTES')
GET_TYPES = ('ALL', 'CONFIG', 'STATE', 'OPERATIONAL')
SUBSCRIBE_MODES = ('STREAM', 'ONCE', 'POLL')
STREAM_MODES = ('SAMPLE', 'ON_CHANGE', 'TARGET_DEFINED')
REMOVED_SUBSCRIPTION_KEYS = {
    'mode': 'stream_mode',
    'sampleInterval': 'sample_interval',
    'heartbeatInterval': 'heartbeat_interval',
    'suppressRedundant': 'suppress_redundant',
}

_DURATION_UNITS = {
    'ns': 1,
    'us': 10 ** 3,
    '\u00b5s': 10 ** 3,
    'ms': 10 ** 6,
    's': 10 ** 9,
    'm': 60 * 10 ** 9,
    'h': 3600 * 10 ** 9,
}
_DURATION_PART = re.compile(r'(\d+(?:\.\d*)?|\.\d+)(ns|us|\u00b5s|ms|s|m|h)')
_ORIGIN = re.compile(r'^([A-Za-z0-9_.-]+):(/.*)$')


class GnmiError(ValueError):
    """Invalid input for a gNMI request."""


# -----------------------------------------------------------------------------
# Durations


def parse_duration(value):
    """
    Converts a duration into nanoseconds.

    Accepts Go duration strings (30s, 1m30s, 1h, 500ms),
    as well as plain numbers, which are interpreted as seconds.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise GnmiError("Invalid duration: %r" % value)
    if isinstance(value, (int, float)):
        if value < 0:
            raise GnmiError("Invalid duration: %r" % value)
        return int(round(value * 10 ** 9))

    text = str(value).strip()
    if not text:
        raise GnmiError("Invalid duration: empty string")
    try:
        return parse_duration(float(text))
    except ValueError:
        pass

    total = 0
    pos = 0
    for match in _DURATION_PART.finditer(text):
        if match.start() != pos:
            break
        total += float(match.group(1)) * _DURATION_UNITS[match.group(2)]
        pos = match.end()
    if pos != len(text) or pos == 0:
        raise GnmiError("Invalid duration: %r (use Go format, e.g. 30s, 1m30s)" % value)
    return int(round(total))


def duration_to_proto(nanoseconds):
    """Renders nanoseconds as a google.protobuf.Duration JSON string."""
    seconds, nanos = divmod(int(nanoseconds), 10 ** 9)
    if nanos:
        return ('%d.%09d' % (seconds, nanos)).rstrip('0') + 's'
    return '%ds' % seconds


# -----------------------------------------------------------------------------
# Paths


def _split_elements(path):
    elements = []
    current = []
    depth = 0
    escaped = False
    for char in path:
        if escaped:
            current.append(char)
            escaped = False
        elif char == '\\':
            current.append(char)
            escaped = True
        elif char == '[':
            depth += 1
            current.append(char)
        elif char == ']':
            depth = max(depth - 1, 0)
            current.append(char)
        elif char == '/' and depth == 0:
            elements.append(''.join(current))
            current = []
        else:
            current.append(char)
    if depth:
        raise GnmiError("Invalid path, unbalanced brackets: %s" % path)
    elements.append(''.join(current))
    return [e for e in elements if e]


def _parse_element(element, path):
    name_end = element.find('[')
    name = element if name_end < 0 else element[:name_end]
    if not name:
        raise GnmiError("Invalid path element '%s' in %s" % (element, path))

    keys = {}
    rest = '' if name_end < 0 else element[name_end:]
    while rest:
        if not rest.startswith('['):
            raise GnmiError("Invalid path element '%s' in %s" % (element, path))
        value = []
        i = 1
        while i < len(rest):
            if rest[i] == '\\' and i + 1 < len(rest):
                value.append(rest[i + 1])
                i += 2
                continue
            if rest[i] == ']':
                break
            value.append(rest[i])
            i += 1
        else:
            raise GnmiError("Invalid path element '%s' in %s" % (element, path))
        key, sep, val = ''.join(value).partition('=')
        if not sep or not key:
            raise GnmiError("Invalid key '%s' in %s" % (''.join(value), path))
        keys[key] = val
        rest = rest[i + 1:]

    entry = {'name': name}
    if keys:
        entry['key'] = keys
    return entry


def encode_path(xpath, target=None, origin=None, qualified=False):
    """
    Encodes an XPATH-like string into the dict form of gnmi.Path.

    The origin is given as "origin:/path", or as origin argument, which
    only applies if the path does not name one.

    Once an origin is known (from the path, the origin argument or with
    qualified=True), element names keep their YANG module prefix, as in
    "rfc7951:/Cisco-IOS-XE-native:native". Otherwise, for compatibility with
    1.0.0, a module prefix on an element name ("/oc:interfaces") sets the
    origin.
    """
    result = {}
    xpath = (xpath or '').strip()

    match = _ORIGIN.match(xpath)
    if match:
        result['origin'] = match.group(1)
        xpath = match.group(2)
    elif origin:
        result['origin'] = origin
    qualified = qualified or 'origin' in result

    elems = []
    for element in _split_elements(xpath):
        entry = _parse_element(element, xpath)
        if ':' in entry['name'] and not qualified:
            mod, sep, name = entry['name'].partition(':')
            if ':' in name or not mod or not name:
                raise GnmiError("Invalid path syntax: %s" % element)
            if not elems:
                result['origin'] = mod
            entry['name'] = name
        elems.append(entry)

    if elems:
        result['elem'] = elems
    if target:
        result['target'] = target
    return result


def _escape_key(value):
    return str(value).replace('\\', '\\\\').replace(']', '\\]')


def decode_path(path):
    """
    Decodes the dict form of gnmi.Path into a string.

    Paths without origin are returned without leading slash, as in 1.0.0.
    Paths with origin use the form "origin:/path".
    """
    if not path:
        return ''
    result = []
    for elem in path.get('elem', []):
        tmp = elem['name']
        for key, value in sorted(elem.get('key', {}).items()):
            tmp += '[%s=%s]' % (key, _escape_key(value))
        result.append(tmp)
    if not result and path.get('element'):
        result = list(path['element'])
    text = '/'.join(result)
    if path.get('origin'):
        return '%s:/%s' % (path['origin'], text)
    return text


# -----------------------------------------------------------------------------
# Values


def encode_value(data, encoding):
    """Encodes a value into the dict form of gnmi.TypedValue."""
    encoding = (encoding or 'JSON_IETF').upper()
    if encoding in ('JSON', 'JSON_IETF'):
        raw = base64.b64encode(json.dumps(data).encode()).decode()
        return {'jsonIetfVal' if encoding == 'JSON_IETF' else 'jsonVal': raw}
    if encoding == 'ASCII':
        return {'asciiVal': str(data)}
    if encoding == 'STRING':
        return {'stringVal': str(data)}
    if encoding == 'INT':
        return {'intVal': str(int(data))}
    if encoding == 'UINT':
        if int(data) < 0:
            raise GnmiError("Negative value %r for encoding UINT" % data)
        return {'uintVal': str(int(data))}
    if encoding == 'BOOL':
        if isinstance(data, str):
            if data.lower() not in ('true', 'false'):
                raise GnmiError("Invalid value %r for encoding BOOL" % data)
            data = data.lower() == 'true'
        return {'boolVal': bool(data)}
    if encoding == 'FLOAT':
        return {'doubleVal': float(data)}
    if encoding == 'BYTES':
        raw = data if isinstance(data, bytes) else str(data).encode()
        return {'bytesVal': base64.b64encode(raw).decode()}
    raise GnmiError("Unsupported encoding %s (one of %s)" % (encoding, ', '.join(ENCODINGS)))


def decode_value(val):
    """Decodes the dict form of gnmi.TypedValue into a Python value."""
    for key in ('jsonIetfVal', 'jsonVal'):
        if key in val:
            return json.loads(base64.b64decode(val[key]))
    for key in ('stringVal', 'asciiVal', 'boolVal', 'doubleVal', 'floatVal'):
        if key in val:
            return val[key]
    for key in ('intVal', 'uintVal'):
        if key in val:
            return int(val[key])
    if 'decimalVal' in val:
        digits = int(val['decimalVal'].get('digits', 0))
        precision = int(val['decimalVal'].get('precision', 0))
        return digits / (10 ** precision)
    if 'leaflistVal' in val:
        return [decode_value(v) for v in val['leaflistVal'].get('element', [])]
    if 'bytesVal' in val:
        return val['bytesVal']
    if 'protoBytes' in val:
        return val['protoBytes']
    if 'anyVal' in val:
        return val['anyVal']
    if not val:
        return None
    raise GnmiError("Unsupported value encoding: %s" % json.dumps(val))


# -----------------------------------------------------------------------------
# Requests


def _prefix(prefix, target, origin=None):
    """
    Encodes the prefix and returns it with a function that encodes the
    paths below it.

    gNMI allows the origin in the prefix or in the paths, not in both. A
    default origin goes to a non-empty prefix, otherwise to each path.
    Paths that name their own origin keep it.
    """
    explicit_prefix_origin = bool(_ORIGIN.match((prefix or '').strip()))
    encoded = encode_path(prefix, target, qualified=bool(origin))
    path_origin = origin
    if encoded.get('origin'):
        path_origin = None
    elif origin and encoded.get('elem'):
        encoded['origin'] = origin
        path_origin = None
    qualified = bool(origin) or explicit_prefix_origin
    prefix_origin = bool(encoded.get('origin'))

    def encode(path):
        item = encode_path(path, origin=path_origin, qualified=qualified)
        if prefix_origin and not _ORIGIN.match((path or '').strip()):
            item.pop('origin', None)
        return item

    return encoded or None, encode


def _models(model):
    return [{'name': model}] if model else None


def _compact(request):
    return dict((k, v) for k, v in request.items() if v not in (None, [], {}, ''))


def build_get_request(path=None, prefix=None, target=None, model=None, type=None, encoding=None, origin=None):
    """Builds the dict form of gnmi.GetRequest."""
    data_type = (type or 'ALL').upper()
    if data_type not in GET_TYPES:
        raise GnmiError("Invalid type %s (one of %s)" % (type, ', '.join(GET_TYPES)))
    encoded_prefix, encode = _prefix(prefix, target, origin)
    return _compact({
        'prefix': encoded_prefix,
        'path': [encode(p) for p in (path or [''])],
        'type': data_type,
        'encoding': (encoding or 'JSON_IETF').upper(),
        'use_models': _models(model),
    })


def _set_entries(entries, default_encoding, kind, encode):
    result = []
    for entry in entries or []:
        if not isinstance(entry, dict) or 'path' not in entry:
            raise GnmiError("Each %s entry needs 'path' and 'value'" % kind)
        if 'value' in entry:
            value = entry['value']
        elif 'val' in entry:
            raise GnmiError("The %s key 'val' was renamed to 'value' in 2.0.0" % kind)
        else:
            raise GnmiError("Missing 'value' for %s path %s" % (kind, entry['path']))
        encoding = entry.get('encoding') or default_encoding
        result.append({'path': encode(entry['path']), 'val': encode_value(value, encoding)})
    return result


def build_set_request(prefix=None, target=None, update=None, replace=None, delete=None, encoding=None,
                      origin=None):
    """Builds the dict form of gnmi.SetRequest (without extensions)."""
    encoded_prefix, encode = _prefix(prefix, target, origin)
    return _compact({
        'prefix': encoded_prefix,
        'delete': [encode(p) for p in (delete or [])],
        'replace': _set_entries(replace, encoding, 'replace', encode),
        'update': _set_entries(update, encoding, 'update', encode),
    })


def load_set_request(data):
    """
    Normalizes a set-request file document (already parsed from JSON/YAML).

    Returns a dict with update, replace and delete lists in module form.
    """
    if not isinstance(data, dict):
        raise GnmiError("request_file must contain a mapping with updates, replaces and/or deletes")
    unknown = set(data) - set(('updates', 'replaces', 'deletes'))
    if unknown:
        raise GnmiError("Unsupported keys in request_file: %s" % ', '.join(sorted(unknown)))

    def entries(name):
        result = []
        for entry in data.get(name) or []:
            if not isinstance(entry, dict) or 'value' not in entry:
                raise GnmiError("Each entry in %s needs a 'value'" % name)
            item = {'path': entry.get('path') or '/', 'value': entry['value']}
            if entry.get('encoding'):
                item['encoding'] = entry['encoding']
            result.append(item)
        return result

    deletes = data.get('deletes') or []
    if not isinstance(deletes, list) or not all(isinstance(d, str) for d in deletes):
        raise GnmiError("deletes in request_file must be a list of paths")
    return {'update': entries('updates'), 'replace': entries('replaces'), 'delete': list(deletes)}


def build_subscription_list(path=None, subscription=None, prefix=None, target=None, model=None,
                            mode=None, stream_mode=None, sample_interval=None, heartbeat_interval=None,
                            suppress_redundant=None, updates_only=None, allow_aggregation=None,
                            qos=None, encoding=None, origin=None):
    """Builds the dict form of gnmi.SubscriptionList."""
    mode = (mode or 'STREAM').upper()
    if mode not in SUBSCRIBE_MODES:
        raise GnmiError("Invalid mode %s (one of %s)" % (mode, ', '.join(SUBSCRIBE_MODES)))
    if path and subscription:
        raise GnmiError("path and subscription are mutually exclusive")
    if not path and not subscription:
        raise GnmiError("One of path or subscription is required")
    encoded_prefix, encode = _prefix(prefix, target, origin)

    def one(entry_path, entry_stream_mode, entry_sample, entry_heartbeat, entry_suppress):
        item = {'path': encode(entry_path)}
        if mode == 'STREAM':
            sm = (entry_stream_mode or 'SAMPLE').upper()
            if sm not in STREAM_MODES:
                raise GnmiError("Invalid stream_mode %s (one of %s)" % (sm, ', '.join(STREAM_MODES)))
            item['mode'] = sm
            if entry_sample:
                item['sample_interval'] = str(entry_sample)
            if entry_heartbeat:
                item['heartbeat_interval'] = str(entry_heartbeat)
            if entry_suppress:
                item['suppress_redundant'] = True
        return item

    items = []
    if path:
        for p in path:
            items.append(one(p, stream_mode, parse_duration(sample_interval),
                             parse_duration(heartbeat_interval), suppress_redundant))
    else:
        for entry in subscription:
            if 'path' not in entry:
                raise GnmiError("Each subscription entry needs a 'path'")
            removed = sorted(set(entry) & set(REMOVED_SUBSCRIPTION_KEYS))
            if removed:
                raise GnmiError("Subscription keys removed in 2.0.0: %s. Use %s" % (
                    ', '.join(removed), ', '.join(REMOVED_SUBSCRIPTION_KEYS[k] for k in removed)))
            items.append(one(entry['path'], entry.get('stream_mode'),
                             parse_duration(entry.get('sample_interval')),
                             parse_duration(entry.get('heartbeat_interval')),
                             entry.get('suppress_redundant')))

    return _compact({
        'prefix': encoded_prefix,
        'subscription': items,
        'mode': mode,
        'encoding': (encoding or 'JSON_IETF').upper(),
        'use_models': _models(model),
        'qos': {'marking': qos} if qos is not None else None,
        'updates_only': True if updates_only else None,
        'allow_aggregation': True if allow_aggregation else None,
    })


# -----------------------------------------------------------------------------
# Responses


def _timestamp(value):
    return datetime.datetime.fromtimestamp(float(value) / 10 ** 9).isoformat()


def _notifications(raw):
    """
    Yields gnmi.Notification dicts from GetResponse.notification entries or
    from SubscribeResponse messages. Sync responses and messages that only
    carry extensions are skipped.
    """
    for entry in raw:
        if 'syncResponse' in entry:
            continue
        if isinstance(entry.get('update'), dict):
            yield entry['update']
        elif isinstance(entry.get('update'), list) or 'delete' in entry:
            yield entry


def _child(context, elem):
    name = elem['name']
    if 'key' in elem:
        key = json.dumps(elem['key'], sort_keys=True)
        entries = context.setdefault('___' + name, {})
        if key not in entries:
            entries[key] = dict(elem['key'])
        return entries[key]
    if not isinstance(context.get(name), dict):
        context[name] = {}
    return context[name]


def _dict_to_list(data):
    for key in list(data):
        if key.startswith('___'):
            data[key[3:]] = [_dict_to_list(v) if isinstance(v, dict) else v for v in data[key].values()]
            del data[key]
        elif isinstance(data[key], dict):
            data[key] = _dict_to_list(data[key])
    return data


def merge_notifications(raw):
    """
    Merges notifications into a single object tree, keyed list entries
    becoming lists, like the 1.0.0 output of gnmi_get and ONCE subscriptions.
    """
    result = {}
    for notification in _notifications(raw):
        prefix_elems = notification.get('prefix', {}).get('elem', [])
        context = result
        for elem in prefix_elems:
            context = _child(context, elem)

        for upd in notification.get('update', []):
            if 'val' not in upd:
                continue
            elems = upd.get('path', {}).get('elem', [])
            target = context
            if not elems:
                if not prefix_elems:
                    value = decode_value(upd['val'])
                    if isinstance(value, dict) and isinstance(result, dict):
                        result.update(value)
                    else:
                        result = value
                    continue
                elems = prefix_elems
                target = result
            for elem in elems[:-1]:
                target = _child(target, elem)
            leaf = elems[-1]
            value = decode_value(upd['val'])
            if 'key' in leaf:
                entries = target.setdefault('___' + leaf['name'], {})
                key = json.dumps(leaf['key'], sort_keys=True)
                if isinstance(value, dict):
                    merged = dict(leaf['key'])
                    merged.update(value)
                    value = merged
                entries[key] = value
            elif isinstance(value, dict) and isinstance(target.get(leaf['name']), dict):
                target[leaf['name']].update(value)
            else:
                target[leaf['name']] = value

    if isinstance(result, dict):
        return _dict_to_list(result)
    return result


def notification_values(raw):
    """Returns only the decoded values of the notifications."""
    values = []
    for notification in _notifications(raw):
        for upd in notification.get('update', []):
            if 'val' in upd:
                values.append(decode_value(upd['val']))
    return values


def simplify_notification(entry):
    """Converts one SubscribeResponse dict into the 1.0.0 stream output form."""
    notification = entry.get('update')
    if not isinstance(notification, dict):
        return None
    result = {}
    if 'prefix' in notification:
        prefix = decode_path(notification['prefix'])
        result['prefix'] = prefix if notification['prefix'].get('origin') else '/' + prefix
    if 'timestamp' in notification:
        result['timestamp'] = _timestamp(notification['timestamp'])
    if 'update' in notification:
        result['values'] = dict(
            (decode_path(u.get('path', {})), decode_value(u['val']))
            for u in notification['update'] if 'val' in u
        )
    if 'delete' in notification:
        result['deletes'] = [decode_path(p) for p in notification['delete']]
    return result


def simplify_set_response(response):
    """Converts a SetResponse dict into the 1.0.0 gnmi_config output form."""
    output = dict(response)
    output.pop('extension', None)
    if 'timestamp' in output:
        output['timestamp'] = _timestamp(output['timestamp'])
    if 'prefix' in output:
        output['prefix'] = decode_path(output['prefix'])
    for item in output.get('response', []):
        item['path'] = decode_path(item.get('path', {}))
        item.pop('timestamp', None)
    return output
