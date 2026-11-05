# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

"""Shared helpers for the gnmi_* modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.connection import Connection, ConnectionError

COLLECTION = 'nokia.openconfig'


def to_json(data):
    """Renders data the way 1.0.0 returned C(output): a JSON string."""
    return json.dumps(data, indent=4, sort_keys=True)


def normalize_enum(module, name, choices, value=None):
    """Upper-cases an enum parameter and validates it against the protobuf enum names."""
    if value is None:
        value = module.params.get(name)
    if value is None:
        return None
    upper = str(value).upper()
    if upper not in choices:
        module.fail_json(msg="Invalid value %r for %s, expected one of: %s" % (value, name, ', '.join(choices)))
    return upper


class Rpc:
    """Calls methods on the persistent nokia.openconfig.grpc connection."""

    def __init__(self, module):
        self._module = module
        self._connection = None

    def __call__(self, method, **kwargs):
        return self.call(method, kwargs)

    def call(self, method, kwargs, fail=True):
        """Returns the RPC result. On error, fails the module, or returns
        None and warns if fail is false."""
        if self._connection is None and not self._module._socket_path:
            self._module.fail_json(msg="This module requires the persistent connection %s.grpc, "
                                       "set ansible_connection: %s.grpc" % (COLLECTION, COLLECTION))
        try:
            if self._connection is None:
                self._connection = Connection(self._module._socket_path)
            return getattr(self._connection, method)(**kwargs)
        except ConnectionError as exc:
            msg = to_text(exc, errors='surrogate_then_replace')
            if fail:
                self._module.fail_json(msg=msg, code=getattr(exc, 'code', -1))
            self._module.warn(msg)
            return None
