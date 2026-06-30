from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class LinkFeatureConfig:
    resource_suffixes: tuple[str, ...] = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".css",
        ".js",
        ".pdf",
        ".zip",
        ".mp4",
        ".mp3",
        ".ico",
        ".woff",
        ".woff2",
        ".webp",
    )
    skip_path_words: frozenset[str] = frozenset(
        {
            "category",
            "appendix",
            "talk",
            "special",
            "contact",
            "cookie",
            "cookies",
            "impressum",
            "imprint",
            "kontakt",
            "login",
            "logout",
            "newsletter",
            "privacy",
            "search",
            "sitemap",
            "tag",
            "tags",
            "terms",
        }
    )
    non_english_language_prefixes: frozenset[str] = frozenset(
        {
            "cn",
            "de",
            "deutsch",
            "es",
            "fr",
            "it",
            "ja",
            "nl",
            "pl",
            "pt",
            "ru",
            "zh",
        }
    )
    blocked_hosts: frozenset[str] = frozenset(
        {
            "web.archive.org",
            "archive.today",
            "archive.is",
            "archive.ph",
            "atlasobscura.com",
            "bsky.app",
            "bsky.social",
            "facebook.com",
            "google.com",
            "google.de",
            "instagram.com",
            "linkedin.com",
            "maps.google.com",
            "maps.google.de",
            "pinterest.com",
            "pinterest.de",
            "plus.google.com",
            "tiktok.com",
            "x.com",
            "twitter.com",
            "www.google.com",
            "www.google.de",
            "www.atlasobscura.com",
            "youtube.com",
            "youtu.be",
        }
    )
    blocked_host_suffixes: tuple[str, ...] = (
        ".facebook.com",
        ".instagram.com",
        ".linkedin.com",
        ".pinterest.com",
        ".pinterest.de",
        ".tiktok.com",
        ".twitter.com",
        ".youtube.com",
        ".atlasobscura.com",
    )


DEFAULT_CONFIG = LinkFeatureConfig()


@dataclass(frozen=True)
class LinkVerdictInput:
    anchor: str
    target_url: str
    parent_url: str = ""
    parent_host: str = ""
    parent_depth: int | None = None
    parent_pageverdict_score: float | None = None
    parent_pageverdict_decision: str = ""
    parent_relevance: float | None = None
    target_host: str = ""
    target_depth: int | None = None
    raw_score: float | None = None


def normalize_host(host: str | None) -> str:
    if not host:
        return ""
    return host.lower().removeprefix("www.")


def normalize_space(value: str | None) -> str:
    return " ".join((value or "").split())


def host_from_url(url: str) -> str:
    try:
        return normalize_host(urlparse(url).hostname)
    except ValueError:
        return ""


def path_from_url(url: str) -> str:
    try:
        return unquote(urlparse(url).path).lower()
    except ValueError:
        return ""


def path_text(url: str) -> str:
    path = path_from_url(url)
    return " ".join(part for part in re.split(r"[/_.:-]+", path) if part)


def _blocked_host(host: str, config: LinkFeatureConfig) -> bool:
    return host in config.blocked_hosts or any(
        host.endswith(suffix) for suffix in config.blocked_host_suffixes
    )


def _is_skipable(url: str, config: LinkFeatureConfig = DEFAULT_CONFIG) -> bool:
    if _blocked_host(host_from_url(url), config):
        return True
    if url.lower().endswith(config.resource_suffixes):
        return True
    path = path_from_url(url)
    first_segment = next((segment for segment in path.split("/") if segment), "")
    first_language_token = re.split(r"[-_]", first_segment)[0]
    if first_language_token in config.non_english_language_prefixes:
        return True
    path_words = set(re.findall(r"[a-z]+", path))
    return bool(path_words & config.skip_path_words)


def is_skipable_link(url: str, config: LinkFeatureConfig = DEFAULT_CONFIG) -> bool:
    return _is_skipable(url, config)


def _bucket_float(value: float | None, *, step: float, missing: str = "missing") -> str:
    if value is None:
        return missing
    bucket = round(value / step) * step
    return f"{bucket:.2f}"


def _bucket_int(value: int | None) -> str:
    return "missing" if value is None else str(value)


def _flag(name: str, enabled: bool) -> str:
    return f"{name}:{'yes' if enabled else 'no'}"


def make_text(example: LinkVerdictInput, config: LinkFeatureConfig = DEFAULT_CONFIG) -> str:
    target_host = normalize_host(example.target_host) or host_from_url(example.target_url)
    parent_host = normalize_host(example.parent_host) or host_from_url(example.parent_url)

    flags = [
        _flag("hard_skipable_url", _is_skipable(example.target_url, config)),
    ]

    parts = [
        f"anchor: {normalize_space(example.anchor)}",
        f"target_url: {normalize_space(example.target_url)}",
        f"target_host: {target_host}",
        f"target_path: {path_text(example.target_url)}",
        f"parent_url: {normalize_space(example.parent_url)}",
        f"parent_host: {parent_host}",
        f"parent_depth: {_bucket_int(example.parent_depth)}",
        f"target_depth: {_bucket_int(example.target_depth)}",
        "parent_pageverdict_score_bucket: "
        f"{_bucket_float(example.parent_pageverdict_score, step=0.1)}",
        f"parent_pageverdict_decision: {normalize_space(example.parent_pageverdict_decision)}",
        f"parent_relevance_bucket: {_bucket_float(example.parent_relevance, step=0.5)}",
        "flags: " + " ".join(flags),
    ]
    return "\n".join(parts)
