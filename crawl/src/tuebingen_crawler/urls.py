from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

# File extensions that are never HTML pages worth fetching.
SKIPPED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt",
    ".zip", ".gz", ".tar", ".rar", ".7z", ".dmg", ".exe", ".apk",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ogg", ".wav", ".webm",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
}

# Large sites that never contribute indexable Tübingen content.
BLOCKED_HOSTS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "linkedin.com", "pinterest.com", "tiktok.com", "amazon.com", "amazon.de",
    "google.com", "maps.google.com", "play.google.com", "apple.com",
    "doubleclick.net", "paypal.com", "booking.com", "vimeo.com",
}


def host_of(url: str) -> str:
    host = urlparse(url).hostname
    return host.lower() if host else ""


def is_blocked_host(host: str) -> bool:
    return any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_HOSTS)


def normalize_url(raw_url: str, base_url: str = "") -> str | None:
    """Resolve and canonicalize a URL; return None if it is not crawlable.

    Normalization: lowercase host, drop fragments and query strings (avoids
    session-id and calendar crawler traps), strip trailing slashes and default
    ports, skip non-HTML file extensions and blocked hosts.
    """
    absolute = urljoin(base_url, raw_url.strip()) if base_url else raw_url.strip()
    parsed = urlparse(absolute)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    host = parsed.hostname.lower()
    if is_blocked_host(host):
        return None

    path = parsed.path or "/"
    last_segment = path.rsplit("/", 1)[-1]
    if "." in last_segment:
        extension = "." + last_segment.rsplit(".", 1)[-1].lower()
        if extension in SKIPPED_EXTENSIONS:
            return None

    if path != "/":
        path = path.rstrip("/")

    netloc = host
    if parsed.port and not (
        (parsed.scheme == "http" and parsed.port == 80)
        or (parsed.scheme == "https" and parsed.port == 443)
    ):
        netloc = f"{host}:{parsed.port}"

    return urlunparse((parsed.scheme, netloc, path, "", "", ""))


def url_slug(page_url: str) -> str:
    parsed = urlparse(page_url)

    slug = parsed.path.strip("/") or "index"
    for old in ["/", "?", "&", "=", ":", "@", "%", "#"]:
        slug = slug.replace(old, "-")

    slug = slug.strip("-._").lower()
    if len(slug) > 90:
        slug = slug[:90].strip("-._")

    return slug or "page"
