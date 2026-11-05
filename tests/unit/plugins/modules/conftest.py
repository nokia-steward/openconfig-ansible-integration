# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json

import pytest

try:
    from ansible.module_utils.testing import patch_module_args
except ImportError:
    from contextlib import contextmanager
    from ansible.module_utils import basic

    @contextmanager
    def patch_module_args(args):
        previous = basic._ANSIBLE_ARGS
        basic._ANSIBLE_ARGS = json.dumps({'ANSIBLE_MODULE_ARGS': args}).encode('utf-8')
        try:
            yield
        finally:
            basic._ANSIBLE_ARGS = previous

from ansible_collections.nokia.openconfig.plugins.module_utils import gnmi_module


class MockConnection:
    """Stands in for the persistent connection; records every RPC."""

    def __init__(self):
        self.calls = []
        self.responses = {}

    def __call__(self, socket_path):
        return self

    def __getattr__(self, method):
        if method.startswith('_'):
            raise AttributeError(method)

        def rpc(**kwargs):
            self.calls.append((method, kwargs))
            response = self.responses.get(method)
            if isinstance(response, list):
                return response.pop(0)
            if callable(response):
                return response(**kwargs)
            return response
        return rpc

    def methods(self):
        return [c[0] for c in self.calls]


@pytest.fixture
def connection(monkeypatch):
    mock = MockConnection()
    monkeypatch.setattr(gnmi_module, 'Connection', mock)
    return mock


@pytest.fixture
def run_module(capsys):
    def run(main, args, check_mode=False, diff=False, socket_path='/nonexistent/ansible-connection.sock'):
        args = dict(args)
        if socket_path:
            args['_ansible_socket'] = socket_path
        if check_mode:
            args['_ansible_check_mode'] = True
        if diff:
            args['_ansible_diff'] = True
        with patch_module_args(args):
            with pytest.raises(SystemExit):
                main()
        return json.loads(capsys.readouterr().out)
    return run
