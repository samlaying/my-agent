"""ws.cron_hook — cron 触发时推送通知到前端"""

from ws.protocol import BUBBLE_CRON
from ws.mood import set_mood
from ws.bubble import send_bubble


def on_cron_fired(job):
    """cron_autorun_loop 调用此函数。ws_server 为 None 时自动跳过。"""
    set_mood("alert", f"Scheduled: {job.prompt[:40]}")
    send_bubble(f"⏰ {job.prompt}", kind=BUBBLE_CRON, duration=10000)
