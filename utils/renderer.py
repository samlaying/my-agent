"""utils.renderer — 多模态终端输出渲染器

MultimodalRenderer 与 terminal_print() 并列，不侵入现有代码。
支持 iTerm2/WezTerm inline image protocol、edge-tts TTS、手账体 HTML 渲染。
"""

import base64
import html as html_mod
import os
import platform
import subprocess
from pathlib import Path


class MultimodalRenderer:
    """终端多模态输出。检测终端类型，graceful fallback。"""

    def __init__(self):
        self.terminal_type = self._detect_terminal()

    def _detect_terminal(self) -> str:
        """检测终端类型：iterm2 / wezterm / other。"""
        term_program = os.environ.get("TERM_PROGRAM", "")
        if "iTerm" in term_program:
            return "iterm2"
        if "WezTerm" in term_program:
            return "wezterm"
        return "other"

    # ── Task 8: render_image ──

    def render_image(self, path: str, width: int = 60) -> str:
        """在终端显示图片。iTerm2/WezTerm: inline image protocol；其他: 打印路径。"""
        p = Path(path)
        if not p.exists():
            return f"[图片不存在: {path}]"

        if self.terminal_type in ("iterm2", "wezterm"):
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            # iTerm2 inline image protocol
            osc = f"\033]1337;File=inline=1;width={width}ch;preserveAspectRatio=1:{data}\a"
            print(osc, end="", flush=True)
            return f"[已在终端显示: {path}]"

        return f"[终端不支持图片显示，文件路径: {path}]"

    # ── Task 9: speak ──

    def speak(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str:
        """TTS 播放。edge-tts 生成 .mp3 -> afplay/mpv 播放。返回音频文件路径。"""
        output_path = Path("/tmp") / "agent_tts_output.mp3"

        try:
            import asyncio
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            asyncio.run(communicate.save(str(output_path)))
        except ImportError:
            return "[edge-tts 未安装，运行: pip install edge-tts]"

        if platform.system() == "Darwin":
            subprocess.Popen(["afplay", str(output_path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                subprocess.Popen(["mpv", "--no-video", str(output_path)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                return f"[音频已生成: {output_path}，无可用播放器]"

        return f"[TTS 播放中: {output_path}]"

    # ── Task 10: render_handbook ──

    def render_handbook(self, content: str, output_path: str) -> str:
        """结构化 markdown -> 手账体 HTML。返回输出文件路径。"""
        lines = content.split("\n")
        body_parts = []
        for line in lines:
            if line.startswith("# "):
                body_parts.append(f"<h1>{html_mod.escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body_parts.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
            elif line.startswith("- "):
                body_parts.append(f"<li>{html_mod.escape(line[2:])}</li>")
            elif line.strip():
                body_parts.append(f"<p>{html_mod.escape(line)}</p>")

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Courier New', monospace; max-width: 600px; margin: 40px auto; padding: 20px;
         background: #fdf6e3; color: #333; line-height: 1.8; }}
  h1 {{ border-bottom: 2px dashed #888; padding-bottom: 8px; }}
  h2 {{ color: #555; }}
  li {{ margin-left: 20px; }}
  p {{ text-indent: 2em; }}
</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>"""

        Path(output_path).write_text(html_content, encoding="utf-8")
        return output_path
