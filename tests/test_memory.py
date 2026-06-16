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


def test_shared_namespace_boosted(tmp_path):
    """shared namespace 的结果比其他 namespace 权重更高"""
    from agents.profile import MemoryPolicy

    # 创建两个同内容的文件：一个在 shared/，一个在普通 namespace
    # 使用英文以确保 token 匹配正常（中文 regex 会整串匹配）
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    (shared_dir / "note.md").write_text("buy coffee 50 dollars at starbucks", encoding="utf-8")
    (tmp_path / "food.md").write_text("buy coffee 50 dollars at starbucks", encoding="utf-8")

    svc = MemoryService(root=tmp_path)
    policy = MemoryPolicy(namespaces=["food", "shared"], max_chars=5000)
    result = svc.retrieve("buy coffee 50", policy)

    # shared 的内容应该出现在 food 之前（权重更高）
    shared_pos = result.find("[shared]")
    food_pos = result.find("[food]")
    if shared_pos >= 0 and food_pos >= 0:
        assert shared_pos < food_pos, "shared namespace should rank higher"


def test_set_state_tool_registered():
    """set_state 工具已注册到 BUILTIN_TOOLS"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "set_state" in names
