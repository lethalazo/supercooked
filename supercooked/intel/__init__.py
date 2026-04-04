"""Content intelligence - trends, ideation, analytics, strategy."""

from supercooked.intel.analytics import (
    get_platform_stats,
    get_top_content,
    record_performance,
    update_platform_followers,
)
from supercooked.intel.ideate import generate_ideas
from supercooked.intel.strategy import recommend_strategy
from supercooked.intel.trends import scan_trends

__all__ = [
    "scan_trends",
    "generate_ideas",
    "record_performance",
    "get_top_content",
    "get_platform_stats",
    "update_platform_followers",
    "recommend_strategy",
]
