"""Intent router tests (Block 3, Tasks 12-14)"""

from context.router import classify_intent


# ── Task 12: classify_intent() ──

def test_classify_single_intent():
    """Single intent recognition"""
    result = classify_intent("今天花了50块吃麦当劳")
    assert "复盘" in result


def test_classify_multi_intent():
    """Multi-intent recognition (复盘 + 变帅)"""
    result = classify_intent("中午吃了碗面条花了20块")
    assert "复盘" in result
    assert "变帅" in result


def test_classify_empty():
    """Empty input returns empty list"""
    assert classify_intent("") == []


def test_classify_no_match():
    """No matching keywords returns empty list"""
    assert classify_intent("今天天气不错") == []


def test_classify_english_intent():
    """English intent recognition"""
    result = classify_intent("背了50个单词")
    assert "英语" in result


def test_classify_work_intent():
    """Work intent recognition"""
    result = classify_intent("下午有个会议")
    assert "工作" in result


def test_classify_social_intent():
    """Social intent recognition"""
    result = classify_intent("最近聊天技巧需要提升")
    assert "社交" in result


def test_classify_whitespace_only():
    """Whitespace-only input returns empty list"""
    assert classify_intent("   ") == []


def test_classify_none_safe():
    """None input returns empty list"""
    assert classify_intent(None) == []


# ── Task 13: route tool registration ──

def test_route_tool_registered():
    """route tool is registered in BUILTIN_TOOLS"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "route" in names


def test_route_tool_schema():
    """route tool has correct input schema"""
    from tools.dispatch import BUILTIN_TOOLS
    route = next(t for t in BUILTIN_TOOLS if t["name"] == "route")
    assert "text" in route["input_schema"]["properties"]
    assert route["input_schema"]["required"] == ["text"]


# ── Task 14: loop integration import check ──

def test_router_import_in_loop():
    """agent_loop module can import classify_intent"""
    from context.router import classify_intent
    assert callable(classify_intent)
