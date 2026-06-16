"""共享记忆与时空状态测试"""

import json
from pathlib import Path
from context.memory import MemoryService


def test_shared_dir_exists(tmp_path):
    """共享目录存在且可写"""
    svc = MemoryService(root=tmp_path)
    assert svc.shared_dir.exists()
    assert svc.shared_dir.is_dir()


def test_state_path_exists(tmp_path):
    """状态文件路径可访问"""
    svc = MemoryService(root=tmp_path)
    assert svc.state_path == tmp_path / "state.json"
