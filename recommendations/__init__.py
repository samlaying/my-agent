"""recommendations — 定时推荐系统。

由若干原子化 recommender 组成，每个独立读取一个数据源（任务 / Loop / Cron /
工具 / 记忆），产出结构化 Recommendation 卡片。engine 聚合、去重、排序后持久化到
``.agent/recommendations.json``，可由 cron 定时刷新，也可由 web 前端展示。
"""

from recommendations.contract import Recommendation, Recommender, stable_id

__all__ = ["Recommendation", "Recommender", "stable_id"]
