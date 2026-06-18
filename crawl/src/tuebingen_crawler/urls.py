from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


def normalize_host(host: str | None) -> str:
    if not host:
        return ""
    return host.lower().removeprefix("www.")


# wrapper around canonical_url
def validate_start_url(url: str) -> str:
    canonical_start, is_valid = canonical_url(url, url)
    if not is_valid:
        raise ValueError(f"ERROR: invalid starting url {url}")
    return canonical_start

# normalizes url
def canonical_url(raw_url: str, base_url: str) -> tuple[str, bool]:
    absolute = urljoin(base_url, raw_url)
    parsed = urlparse(absolute)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "", False

    path = parsed.path
    if path != "/":
        path = path.rstrip("/")

    final_url = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        "",  # params
        "",  # query ignored
        "",  # fragment ignored
    ))
    return final_url, True


def url_slug(page_url: str) -> str:
    parsed = urlparse(page_url)

    slug = parsed.path.strip("/")
    if not slug:
        slug = "index"

    if parsed.query:
        slug += "-" + parsed.query

    for old in ["/", "?", "&", "=", ":", "@", "%", "#"]:
        slug = slug.replace(old, "-")

    slug = slug.strip("-._").lower()

    if len(slug) > 90:
        slug = slug[:90].strip("-._")

    return slug or "page"
