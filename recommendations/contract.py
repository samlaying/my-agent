"""Recommendation contracts — 原子卡片 + 原子 recommender 基类。

一张 Recommendation 是推荐系统的最小展示/操作单元；一个 Recommender 是最小生产单元。
两者都刻意保持无外部依赖（除 dataclasses / 标准库），便于独立测试与替换。
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone


def stable_id(*parts: object) -> str:
    """跨进程稳定的短 id（hash() 在不同 PYTHONHASHSEED 下不稳定，这里用 md5）。"""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


@dataclass
class Recommendation:
    """一张推荐卡片。"""

    id: str
    source: str                       # 生产者 id: task / loop / cron / tool / memory
    kind: str                         # task / fix / schedule / tool / memory / note
    title: str
    reason: str
    priority: int = 3                 # 1(低) .. 5(紧急)
    action: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    status: str = "new"               # new / dismissed / done

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Recommendation":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


class Recommender:
    """原子 recommender 基类。

    每个子类只读一个数据源，``source`` 标识来源，``recommend`` 返回 0..N 张卡片。
    新增推荐源 = 新增一个文件 + 在 engine 注册，无需改动既有逻辑。
    """

    source: str = "base"

    def recommend(self) -> list[Recommendation]:
        raise NotImplementedError
