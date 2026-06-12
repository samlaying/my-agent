"""scheduler.cron — 持久化定时任务"""

import json
import time
import random
import threading
from dataclasses import dataclass, asdict
from datetime import datetime

from core.config import DURABLE_PATH
from utils.terminal import terminal_print


@dataclass
class CronJob:
    id: str; cron: str; prompt: str; recurring: bool; durable: bool

scheduled_jobs: dict[str, CronJob] = {}
cron_queue: list[CronJob] = []
cron_lock = threading.Lock()
_last_fired: dict[str, str] = {}


def _cron_field_matches(field: str, value: int) -> bool:
    if field == "*": return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_matches(p.strip(), value) for p in field.split(","))
    if "-" in field:
        lo, hi = field.split("-", 1)
        return int(lo) <= value <= int(hi)
    return value == int(field)


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    fields = cron_expr.strip().split()
    if len(fields) != 5: return False
    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7
    if not (_cron_field_matches(minute, dt.minute) and _cron_field_matches(hour, dt.hour)
            and _cron_field_matches(month, dt.month)): return False
    if dom == "*" and dow == "*": return True
    if dom == "*": return _cron_field_matches(dow, dow_val)
    if dow == "*": return _cron_field_matches(dom, dt.day)
    return _cron_field_matches(dom, dt.day) or _cron_field_matches(dow, dow_val)


def validate_cron(cron_expr: str) -> str | None:
    fields = cron_expr.strip().split()
    if len(fields) != 5: return f"Expected 5 fields, got {len(fields)}"
    return None


def save_durable_jobs():
    durable = [asdict(j) for j in scheduled_jobs.values() if j.durable]
    DURABLE_PATH.write_text(json.dumps(durable, indent=2))


def load_durable_jobs():
    if not DURABLE_PATH.exists(): return
    try:
        for item in json.loads(DURABLE_PATH.read_text()):
            job = CronJob(**item)
            if not validate_cron(job.cron): scheduled_jobs[job.id] = job
    except: pass


def schedule_job(cron: str, prompt: str, recurring: bool = True, durable: bool = True) -> CronJob | str:
    err = validate_cron(cron)
    if err: return err
    job = CronJob(id=f"cron_{random.randint(0,999999):06d}", cron=cron, prompt=prompt,
                  recurring=recurring, durable=durable)
    with cron_lock: scheduled_jobs[job.id] = job
    if durable: save_durable_jobs()
    return job


def cancel_job(job_id: str) -> str:
    with cron_lock: job = scheduled_jobs.pop(job_id, None)
    if not job: return f"Job {job_id} not found"
    if job.durable: save_durable_jobs()
    return f"Cancelled {job_id}"


def cron_scheduler_loop():
    while True:
        time.sleep(1)
        now = datetime.now()
        marker = now.strftime("%Y-%m-%d %H:%M")
        with cron_lock:
            for job in list(scheduled_jobs.values()):
                try:
                    if cron_matches(job.cron, now) and _last_fired.get(job.id) != marker:
                        cron_queue.append(job)
                        _last_fired[job.id] = marker
                        if not job.recurring:
                            scheduled_jobs.pop(job.id, None)
                            if job.durable: save_durable_jobs()
                except Exception as e:
                    terminal_print(f"  \033[31m[cron error] {job.id}: {e}\033[0m")


def consume_cron_queue() -> list[CronJob]:
    with cron_lock:
        fired = list(cron_queue)
        cron_queue.clear()
    return fired


def run_schedule_cron(cron: str, prompt: str, recurring: bool = True, durable: bool = True) -> str:
    result = schedule_job(cron, prompt, recurring, durable)
    if isinstance(result, str): return f"Error: {result}"
    return f"Scheduled {result.id}: '{cron}' -> {prompt}"


def run_list_crons() -> str:
    with cron_lock: jobs = list(scheduled_jobs.values())
    if not jobs: return "No cron jobs."
    return "\n".join(
        f"  {j.id}: '{j.cron}' -> {j.prompt[:40]} [{'recurring' if j.recurring else 'one-shot'}]"
        for j in jobs)


def run_cancel_cron(job_id: str) -> str:
    return cancel_job(job_id)


load_durable_jobs()
threading.Thread(target=cron_scheduler_loop, daemon=True).start()
