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


def test_get_state_default(tmp_path):
    """无状态文件时返回空 dict"""
    svc = MemoryService(root=tmp_path)
    assert svc.get_state() == {}


def test_set_and_get_state(tmp_path):
    """set_state 写入后 get_state 能读取"""
    svc = MemoryService(root=tmp_path)
    svc.set_state("day_type", "weekend")
    svc.set_state("work_mode", "false")
    state = svc.get_state()
    assert state["day_type"] == "weekend"
    assert state["work_mode"] == "false"


def test_set_state_persists(tmp_path):
    """set_state 写入的内容持久化到 state.json"""
    svc = MemoryService(root=tmp_path)
    svc.set_state("location", "home")
    raw = json.loads((tmp_path / "state.json").read_text())
    assert raw["location"] == "home"
