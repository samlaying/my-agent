"""reminders.manager — 提醒数据模型、持久化、调度"""

import json
import random
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

from core.config import REMINDERS_PATH

# ── 北京时间 ──
BJT = timezone(timedelta(hours=8))


@dataclass
class Reminder:
    id: str
    message: str        # 提醒内容
    cron: str           # 5-field cron (北京时间)
    snooze_min: int     # 稍后再弹间隔（分钟）
    enabled: bool       # 独立开关


# ── 内存状态 ──
_reminders: dict[str, Reminder] = {}
_lock = threading.Lock()
_last_fired: dict[str, str] = {}          # id -> "YYYY-MM-DD HH:MM"
_snooze_timers: dict[str, float] = {}     # id -> fire timestamp (epoch)
_disabled_today: set[str] = set()         # 今天禁用的 reminder id（每天自动清零）


# ── 持久化 ──

def _save():
    data = [asdict(r) for r in _reminders.values()]
    REMINDERS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _load():
    if not REMINDERS_PATH.exists():
        return
    try:
        for item in json.loads(REMINDERS_PATH.read_text()):
            _reminders[item["id"]] = Reminder(**item)
    except (json.JSONDecodeError, KeyError):
        pass


# ── CRUD ──

def create_reminder(message: str, cron: str, snooze_min: int = 10, enabled: bool = True) -> Reminder | str:
    """创建提醒，返回 Reminder 或错误字符串"""
    from scheduler.cron import validate_cron
    err = validate_cron(cron)
    if err:
        return err
    rid = f"rem_{random.randint(0, 999999):06d}"
    r = Reminder(id=rid, message=message, cron=cron, snooze_min=snooze_min, enabled=enabled)
    with _lock:
        _reminders[rid] = r
        _save()
    return r


def list_reminders() -> list[Reminder]:
    with _lock:
        return list(_reminders.values())


def get_reminder(rem_id: str) -> Reminder | None:
    with _lock:
        return _reminders.get(rem_id)


def toggle_reminder(rem_id: str, enabled: bool) -> Reminder | str:
    with _lock:
        r = _reminders.get(rem_id)
        if not r:
            return f"Reminder {rem_id} not found"
        r.enabled = enabled
        _save()
        return r


def delete_reminder(rem_id: str) -> str:
    with _lock:
        if rem_id not in _reminders:
            return f"Reminder {rem_id} not found"
        del _reminders[rem_id]
        _last_fired.pop(rem_id, None)
        _snooze_timers.pop(rem_id, None)
        _save()
    return f"Deleted {rem_id}"


def snooze_reminder(rem_id: str, minutes: int | str | None = None) -> str:
    """设置 snooze。minutes 可以是数字（分钟）或 'today'（今天禁用）"""
    with _lock:
        r = _reminders.get(rem_id)
        if not r:
            return f"Reminder {rem_id} not found"
        if minutes == "today":
            _disabled_today.add(rem_id)
            _snooze_timers.pop(rem_id, None)
            return f"Reminder {rem_id} disabled for today"
        delay = minutes if isinstance(minutes, int) and minutes > 0 else r.snooze_min
        _snooze_timers[rem_id] = time.time() + delay * 60
    return f"Snoozed {rem_id} for {delay} min"


def disable_today(rem_id: str | None = None) -> str:
    """今天不再提醒。rem_id=None 则禁用全部。"""
    with _lock:
        if rem_id:
            if rem_id not in _reminders:
                return f"Reminder {rem_id} not found"
            _disabled_today.add(rem_id)
            return f"Reminder {rem_id} disabled for today"
        else:
            _disabled_today.update(_reminders.keys())
            return "All reminders disabled for today"


def enable_all() -> str:
    """重新启用所有提醒（取消今天的禁用）"""
    with _lock:
        _disabled_today.clear()
        for r in _reminders.values():
            r.enabled = True
        _save()
    return "All reminders enabled"


# ── 调度循环 ──

def _cron_field_matches(field: str, value: int) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_matches(p.strip(), value) for p in field.split(","))
    if "-" in field:
        lo, hi = field.split("-", 1)
        return int(lo) <= value <= int(hi)
    return value == int(field)


def _cron_matches(cron_expr: str, dt: datetime) -> bool:
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7
    if not (_cron_field_matches(minute, dt.minute) and _cron_field_matches(hour, dt.hour)
            and _cron_field_matches(month, dt.month)):
        return False
    if dom == "*" and dow == "*":
        return True
    if dom == "*":
        return _cron_field_matches(dow, dow_val)
    if dow == "*":
        return _cron_field_matches(dom, dt.day)
    return _cron_field_matches(dom, dt.day) or _cron_field_matches(dow, dow_val)


# ── 触发回调（由 ws/reminder_hook 注入）──
_on_fire = None  # callable(reminder: Reminder)


def set_fire_callback(fn):
    global _on_fire
    _on_fire = fn


def reminder_scheduler_loop():
    """守护线程：每秒检查 cron 匹配 + snooze 到期 + 午夜清零"""
    last_reset_day = None
    while True:
        time.sleep(1)
        now = datetime.now(BJT)
        marker = now.strftime("%Y-%m-%d %H:%M")
        now_epoch = time.time()

        # 午夜清零：每天新一天重置 disabled_today
        today_str = now.strftime("%Y-%m-%d")
        if today_str != last_reset_day:
            with _lock:
                _disabled_today.clear()
            last_reset_day = today_str

        with _lock:
            for r in list(_reminders.values()):
                if not r.enabled or r.id in _disabled_today:
                    continue

                fired = False

                # snooze 到期检查
                snooze_at = _snooze_timers.get(r.id)
                if snooze_at and now_epoch >= snooze_at:
                    fired = True
                    del _snooze_timers[r.id]

                # cron 匹配检查（避免和 snooze 重复触发同一分钟）
                if not fired and _cron_matches(r.cron, now):
                    if _last_fired.get(r.id) != marker:
                        fired = True

                if fired:
                    _last_fired[r.id] = marker
                    if _on_fire:
                        try:
                            _on_fire(r)
                        except Exception:
                            pass


# ── 启动 ──
_load()
threading.Thread(target=reminder_scheduler_loop, daemon=True).start()
