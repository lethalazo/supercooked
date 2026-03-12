"""Web scraping via requests + BeautifulSoup.

Provides simple web scraping utilities for extracting content
from web pages — used for research and content sourcing.
"""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15


def scrape_page(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Scrape a web page and return structured data.

    Args:
        url: URL to scrape.
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys:
            url, title, meta_description, headings, links, images, text_content.

    Raises:
        requests.HTTPError: If the request fails.
        requests.ConnectionError: If the URL is unreachable.
    """
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Extract meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")

    # Extract headings
    headings: list[dict[str, str]] = []
    for level in range(1, 7):
        for h in soup.find_all(f"h{level}"):
            text = h.get_text(strip=True)
            if text:
                headings.append({"level": f"h{level}", "text": text})

    # Extract links
    links: list[dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if href and text:
            links.append({"href": href, "text": text})

    # Extract images
    images: list[dict[str, str]] = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src:
            images.append({"src": src, "alt": alt})

    # Extract main text content
    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text_content = soup.get_text(separator="\n", strip=True)

    # Clean up excessive newlines
    lines = [line.strip() for line in text_content.splitlines() if line.strip()]
    text_content = "\n".join(lines)

    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "links": links[:50],  # Limit to first 50 links
        "images": images[:30],  # Limit to first 30 images
        "text_content": text_content[:10000],  # Limit text to 10k chars
    }


def extract_text(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Extract clean text content from a web page.

    Strips all HTML, scripts, styles, navigation, and returns
    only the meaningful text content.

    Args:
        url: URL to extract text from.
        timeout: Request timeout in seconds.

    Returns:
        Clean text content as a string.

    Raises:
        requests.HTTPError: If the request fails.
        requests.ConnectionError: If the URL is unreachable.
    """
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Try to find main content area
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", {"role": "main"})
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"class": "content"})
        or soup.body
        or soup
    )

    text = main_content.get_text(separator="\n", strip=True)

    # Clean up
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
