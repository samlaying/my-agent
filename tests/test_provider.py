"""Ollama provider 接入测试 — Tasks 5, 6, 7"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ── Task 5: model_providers.json 包含 ollama ──


def test_ollama_provider_exists():
    """model_providers.json 包含 ollama provider"""
    providers_path = Path(__file__).parent.parent / "model_providers.json"
    data = json.loads(providers_path.read_text())
    names = [p["name"] for p in data["providers"]]
    assert "ollama" in names


def test_ollama_provider_fields():
    """ollama provider 包含所有必需字段"""
    providers_path = Path(__file__).parent.parent / "model_providers.json"
    data = json.loads(providers_path.read_text())
    ollama = next(p for p in data["providers"] if p["name"] == "ollama")
    assert ollama["protocol"] == "openai"
    assert "11434" in ollama["base_url"]
    assert ollama["model_id"]
    assert ollama["api_key"]


# ── Task 6: _make_client 支持 OpenAI 协议 ──


def test_make_openai_client():
    """protocol=openai 时创建 OpenAI client 而非 Anthropic"""
    from core.config import _make_client

    provider = {
        "name": "test",
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
        "protocol": "openai",
    }
    client = _make_client(provider)
    # OpenAI client 有 chat 属性，Anthropic client 有 messages 属性
    assert hasattr(client, "chat"), "Should be OpenAI client"


def test_make_anthropic_client_unchanged():
    """没有 protocol 字段时仍创建 Anthropic client"""
    from core.config import _make_client

    provider = {
        "name": "test-anthropic",
        "api_key": "test-key",
        "base_url": "",
    }
    client = _make_client(provider)
    assert hasattr(client, "messages"), "Should be Anthropic client"


def test_openai_call_dispatch():
    """LLMGateway 对 OpenAI client 走 chat.completions.create 路径"""
    from core.config import _make_client

    anthropic_provider = {
        "name": "test-anthropic",
        "api_key": "test-key",
        "base_url": "",
    }
    openai_provider = {
        "name": "test-openai",
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
        "protocol": "openai",
    }
    a_client = _make_client(anthropic_provider)
    o_client = _make_client(openai_provider)
    assert hasattr(a_client, "messages"), "Anthropic client should have messages"
    assert hasattr(o_client, "chat"), "OpenAI client should have chat"


# ── Task 7: LLMGateway 双协议调用 ──


def test_llmgateway_calls_openai_for_openai_protocol():
    """LLMGateway 对 OpenAI 协议走 _call_openai 路径"""
    from agents.runtime import LLMGateway, RuntimeSession

    # Mock 响应
    mock_message = SimpleNamespace(content="Hello!", tool_calls=None)
    mock_choice = SimpleNamespace(message=mock_message, finish_reason="stop")
    mock_resp = SimpleNamespace(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with patch("agents.runtime.cfg") as mock_cfg:
        mock_cfg.client = mock_client
        mock_cfg._current_provider = {"protocol": "openai", "model_id": "qwen2.5:latest"}

        session = RuntimeSession(messages=[{"role": "user", "content": "hi"}])
        gateway = LLMGateway()
        result = gateway.call(
            session, tools=[], state=SimpleNamespace(current_model="qwen2.5:latest"),
            max_tokens=100,
        )

    # 验证走了 chat.completions.create
    mock_client.chat.completions.create.assert_called_once()
    # 验证返回结构兼容 Anthropic response
    assert hasattr(result, "content")
    assert hasattr(result, "stop_reason")
    assert result.stop_reason == "end_turn"
    assert len(result.content) == 1
    assert result.content[0].text == "Hello!"


def test_llmgateway_calls_openai_with_tool_calls():
    """LLMGateway 正确转换 OpenAI tool_calls 为 Anthropic 格式"""
    from agents.runtime import LLMGateway, RuntimeSession

    mock_tool_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(
            name="bash",
            arguments='{"command": "ls"}',
        ),
    )
    mock_message = SimpleNamespace(content=None, tool_calls=[mock_tool_call])
    mock_choice = SimpleNamespace(message=mock_message, finish_reason="stop")
    mock_resp = SimpleNamespace(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with patch("agents.runtime.cfg") as mock_cfg:
        mock_cfg.client = mock_client
        mock_cfg._current_provider = {"protocol": "openai", "model_id": "qwen2.5:latest"}

        session = RuntimeSession(messages=[{"role": "user", "content": "run ls"}])
        gateway = LLMGateway()
        result = gateway.call(
            session, tools=[], state=SimpleNamespace(current_model="qwen2.5:latest"),
            max_tokens=100,
        )

    assert len(result.content) == 1
    block = result.content[0]
    assert block.type == "tool_use"
    assert block.name == "bash"
    assert block.input == {"command": "ls"}


def test_llmgateway_anthropic_path_unchanged():
    """LLMGateway 对 Anthropic 协议仍走原有路径"""
    from agents.runtime import LLMGateway, RuntimeSession

    mock_resp = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="Hi")],
        stop_reason="end_turn",
    )

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_resp

    with patch("agents.runtime.cfg") as mock_cfg:
        mock_cfg.client = mock_client
        mock_cfg._current_provider = {}  # no protocol = Anthropic

        session = RuntimeSession(messages=[{"role": "user", "content": "hi"}])
        gateway = LLMGateway()
        result = gateway.call(
            session, tools=[], state=SimpleNamespace(current_model="claude-sonnet-4-20250514"),
            max_tokens=100,
        )

    # 验证走了 messages.create（Anthropic 路径）
    mock_client.messages.create.assert_called_once()
    assert result.content[0].text == "Hi"
