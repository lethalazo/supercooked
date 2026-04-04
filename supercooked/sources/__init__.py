"""External content sources - video downloading and web scraping."""

from supercooked.sources.download import download_video, get_video_info
from supercooked.sources.scrape import extract_text, scrape_page

__all__ = [
    "download_video",
    "get_video_info",
    "scrape_page",
    "extract_text",
]
