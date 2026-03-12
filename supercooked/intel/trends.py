"""Trend scanning via requests + BeautifulSoup.

Scrapes trending topics from multiple public sources to identify
content opportunities for digital beings.
"""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

TREND_SOURCES = {
    "google_trends": "https://trends.google.com/trending?geo=US",
    "reddit_popular": "https://old.reddit.com/r/popular/",
    "hackernews": "https://news.ycombinator.com/",
    "github_trending": "https://github.com/trending",
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _scrape_reddit_popular() -> list[dict[str, str]]:
    """Scrape trending posts from Reddit /r/popular."""
    resp = requests.get(
        TREND_SOURCES["reddit_popular"],
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    trends: list[dict[str, str]] = []

    for link in soup.select("a.title"):
        title = link.get_text(strip=True)
        href = link.get("href", "")
        if title and href:
            if href.startswith("/"):
                href = f"https://old.reddit.com{href}"
            trends.append({
                "source": "reddit",
                "title": title,
                "url": href,
            })
        if len(trends) >= 20:
            break

    return trends


def _scrape_hackernews() -> list[dict[str, str]]:
    """Scrape top stories from Hacker News."""
    resp = requests.get(
        TREND_SOURCES["hackernews"],
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    trends: list[dict[str, str]] = []

    for item in soup.select(".titleline > a"):
        title = item.get_text(strip=True)
        href = item.get("href", "")
        if title and href:
            if href.startswith("item?"):
                href = f"https://news.ycombinator.com/{href}"
            trends.append({
                "source": "hackernews",
                "title": title,
                "url": href,
            })
        if len(trends) >= 20:
            break

    return trends


def _scrape_github_trending() -> list[dict[str, str]]:
    """Scrape trending repositories from GitHub."""
    resp = requests.get(
        TREND_SOURCES["github_trending"],
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    trends: list[dict[str, str]] = []

    for article in soup.select("article.Box-row"):
        name_el = article.select_one("h2 a")
        desc_el = article.select_one("p")
        if name_el:
            repo_name = name_el.get_text(strip=True).replace("\n", "").replace(" ", "")
            href = name_el.get("href", "")
            description = desc_el.get_text(strip=True) if desc_el else ""
            trends.append({
                "source": "github",
                "title": repo_name,
                "url": f"https://github.com{href}" if href.startswith("/") else href,
                "description": description,
            })
        if len(trends) >= 20:
            break

    return trends


def _scrape_google_trends() -> list[dict[str, str]]:
    """Scrape trending searches from Google Trends."""
    resp = requests.get(
        TREND_SOURCES["google_trends"],
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    trends: list[dict[str, str]] = []

    # Google Trends uses various selectors; target the trending now items
    for item in soup.select("[class*='trending'] a, .feed-item a, .details-top a"):
        title = item.get_text(strip=True)
        href = item.get("href", "")
        if title and len(title) > 2:
            if href.startswith("/"):
                href = f"https://trends.google.com{href}"
            trends.append({
                "source": "google_trends",
                "title": title,
                "url": href,
            })
        if len(trends) >= 20:
            break

    return trends


# Map source names to their scraper functions
_SCRAPERS = {
    "reddit": _scrape_reddit_popular,
    "hackernews": _scrape_hackernews,
    "github": _scrape_github_trending,
    "google_trends": _scrape_google_trends,
}


def scan_trends(
    categories: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Scan trending topics from multiple sources.

    Args:
        categories: Optional list of sources to scan. Defaults to all.
            Valid: "reddit", "hackernews", "github", "google_trends".

    Returns:
        List of trend dicts with 'source', 'title', 'url' keys.

    Raises:
        ValueError: If an invalid category is specified.
        requests.HTTPError: If a scrape request fails.
    """
    sources = categories or list(_SCRAPERS.keys())

    # Validate categories
    invalid = set(sources) - set(_SCRAPERS.keys())
    if invalid:
        raise ValueError(
            f"Invalid trend sources: {', '.join(invalid)}. "
            f"Valid sources: {', '.join(_SCRAPERS.keys())}"
        )

    all_trends: list[dict[str, Any]] = []
    errors: list[str] = []

    for source in sources:
        scraper = _SCRAPERS[source]
        try:
            trends = scraper()
            all_trends.extend(trends)
        except Exception as e:
            errors.append(f"{source}: {e}")

    if errors and not all_trends:
        raise RuntimeError(
            "All trend sources failed:\n" + "\n".join(errors)
        )

    return all_trends
