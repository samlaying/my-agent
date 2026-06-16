"""Tests for utils.renderer — MultimodalRenderer (Tasks 8-11)"""

from pathlib import Path

from utils.renderer import MultimodalRenderer


# ── Task 8: MultimodalRenderer 基础 + render_image ──

def test_renderer_detect_terminal():
    """渲染器能检测终端类型"""
    r = MultimodalRenderer()
    assert r.terminal_type in ("iterm2", "wezterm", "other")


def test_render_image_returns_string(tmp_path):
    """render_image 对不存在文件返回 fallback 路径"""
    r = MultimodalRenderer()
    result = r.render_image(str(tmp_path / "nonexistent.png"))
    assert isinstance(result, str)
    assert "nonexistent.png" in result


def test_render_image_existing_file(tmp_path):
    """render_image 对存在的文件返回包含路径的字符串"""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n")
    r = MultimodalRenderer()
    result = r.render_image(str(img))
    assert isinstance(result, str)
    assert "test.png" in result


# ── Task 9: speak() TTS 播放 ──

def test_speak_returns_string():
    """speak 返回字符串（即使 edge-tts 未安装也返回 fallback）"""
    r = MultimodalRenderer()
    result = r.speak("你好世界")
    assert isinstance(result, str)
    assert len(result) > 0


def test_speak_mentions_edge_tts_when_not_installed():
    """edge-tts 未安装时返回包含提示的字符串"""
    r = MultimodalRenderer()
    result = r.speak("测试")
    # Either edge-tts is not installed (returns hint) or it is (returns path)
    assert "edge-tts" in result or "TTS" in result or "mp3" in result


# ── Task 10: render_handbook() 手账体 ──

def test_render_handbook_creates_file(tmp_path):
    """render_handbook 生成 HTML 文件"""
    r = MultimodalRenderer()
    output = str(tmp_path / "handbook.html")
    result = r.render_handbook("# 测试标题\n\n一段内容。", output)
    assert Path(result).exists()
    html = Path(result).read_text()
    assert "测试标题" in html


def test_render_handbook_html_structure(tmp_path):
    """render_handbook 生成的 HTML 包含基本结构"""
    r = MultimodalRenderer()
    output = str(tmp_path / "out.html")
    content = "# 标题\n\n正文内容\n\n## 子标题\n\n- 列表项1\n- 列表项2"
    r.render_handbook(content, output)
    html = Path(output).read_text()
    assert "<h1>" in html
    assert "<h2>" in html
    assert "<li>" in html
    assert "<p>" in html


def test_render_handbook_xss_protection(tmp_path):
    """render_handbook 对 HTML 特殊字符做转义"""
    r = MultimodalRenderer()
    output = str(tmp_path / "xss.html")
    r.render_handbook("# <script>alert('x')</script>", output)
    html = Path(output).read_text()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ── Task 11: 工具注册 ──

def test_multimodal_tools_registered():
    """render_image 和 speak 工具已注册到 BUILTIN_TOOLS"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "render_image" in names
    assert "speak" in names
