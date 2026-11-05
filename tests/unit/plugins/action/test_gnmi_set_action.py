# (c) 2026 Nokia
#
# Licensed under the BSD 3 Clause license
# SPDX-License-Identifier: BSD-3-Clause
#

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock

import pytest

from ansible.playbook.play_context import PlayContext
from ansible.plugins.action.normal import ActionModule as NormalAction

from ansible_collections.nokia.openconfig.plugins.action.gnmi_set import ActionModule


@pytest.mark.parametrize('check_mode, task_args', [
    (True, {'backup': True, 'update': [{'path': '/a', 'value': 1}]}),
    (True, {'backup': True}),
    (False, {'backup': True, 'dry_run': True, 'delete': ['/a']}),
])
def test_gnmi_set_action_backup_skips_when_backup_payload_absent(monkeypatch, tmp_path, check_mode, task_args):
    task = MagicMock()
    task.args = dict(task_args)
    task._role = None
    pc = PlayContext()
    pc.connection = 'nokia.openconfig.grpc'
    pc.check_mode = check_mode
    loader = MagicMock()
    loader.get_basedir.return_value = str(tmp_path)
    monkeypatch.setattr(NormalAction, 'run', lambda self, tmp=None, task_vars=None: {'changed': False, 'request': {}})
    action = ActionModule(task=task, connection=MagicMock(), play_context=pc,
                          loader=loader, templar=MagicMock(), shared_loader_obj=MagicMock())
    res = action.run(task_vars={'inventory_hostname': 'dut'})
    assert res.get('failed') is not True
    assert 'backup_path' not in res
    assert not (tmp_path / 'backup').exists()
