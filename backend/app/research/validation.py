import hashlib
import re
from collections import Counter
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.app.schemas.research import ResearchRequest, ResearchSource


_STOP_WORDS = {
    "about", "after", "also", "and", "are", "for", "from", "help", "how",
    "into", "its", "learn", "learning", "more", "need", "that", "the",
    "their", "then", "this", "through", "using", "want", "what", "with",
}
_NOISE_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "pinterest.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
}
_TRACKING_PARAMETERS = re.compile(r"^(utm_.+|gclid|fbclid|ref_src)$", re.IGNORECASE)
_WORD_PATTERN = re.compile(r"[a-z0-9]{3,}")
_MAX_SOURCES_PER_DOMAIN = 2
_MIN_RELEVANCE = 0.08
_MIN_SNIPPET_LENGTH = 40


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _WORD_PATTERN.findall(value.casefold())
        if token not in _STOP_WORDS
    }


def canonicalize_url(value: str) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(value.strip())
        scheme = parsed.scheme.casefold()
        hostname = (parsed.hostname or "").casefold().removeprefix("www.")
        if scheme not in {"http", "https"} or not hostname or "." not in hostname:
            return None
        if parsed.username or parsed.password:
            return None
        port = parsed.port
        netloc = hostname if port is None else f"{hostname}:{port}"
        query = urlencode(
            sorted(
                (key, item)
                for key, item in parse_qsl(parsed.query, keep_blank_values=True)
                if not _TRACKING_PARAMETERS.match(key)
            )
        )
        path = parsed.path or "/"
        normalized = urlunsplit((scheme, netloc, path, query, ""))
        return normalized, hostname
    except (ValueError, UnicodeError):
        return None


def _relevance_score(request: ResearchRequest, title: str, snippet: str, url: str) -> float:
    request_text = " ".join(
        [
            request.learning_goal,
            request.task,
            request.learner_state,
            request.interest,
            request.current_topic.title,
            " ".join(concept.title for concept in request.current_topic.concepts),
        ]
    )
    terms = _tokens(request_text)
    if not terms:
        return 0.0
    title_terms = _tokens(title)
    content_terms = _tokens(snippet)
    url_terms = _tokens(url)
    weighted_matches = (
        3 * len(terms & title_terms)
        + len(terms & content_terms)
        + 0.5 * len(terms & url_terms)
    )
    total_weight = 3 * len(terms)
    return round(min(weighted_matches / total_weight, 1.0), 4)


def validate_and_rank_sources(
    request: ResearchRequest, candidates: list[dict[str, Any]]
) -> tuple[list[ResearchSource], int, int]:
    """Return ranked useful sources and duplicate/rejected counts."""
    seen_urls: set[str] = set()
    accepted: list[ResearchSource] = []
    duplicate_count = 0
    rejected_count = 0

    for candidate in candidates:
        raw_url = candidate.get("url")
        if not isinstance(raw_url, str):
            rejected_count += 1
            continue
        canonical = canonicalize_url(raw_url)
        if canonical is None:
            rejected_count += 1
            continue
        normalized_url, domain = canonical
        if normalized_url in seen_urls:
            duplicate_count += 1
            continue
        registrable_domain = ".".join(domain.split(".")[-2:])
        if registrable_domain in _NOISE_DOMAINS:
            rejected_count += 1
            continue
        path_parts = {part.casefold() for part in urlsplit(normalized_url).path.split("/") if part}
        if path_parts & {"search", "login", "signup", "register", "tag", "category"}:
            rejected_count += 1
            continue

        title = candidate.get("title")
        snippet = candidate.get("content") or candidate.get("snippet")
        if (
            not isinstance(title, str)
            or not title.strip()
            or not isinstance(snippet, str)
            or len(snippet.strip()) < _MIN_SNIPPET_LENGTH
        ):
            rejected_count += 1
            continue

        relevance = _relevance_score(
            request, title.strip(), snippet.strip(), normalized_url
        )
        if relevance < _MIN_RELEVANCE:
            rejected_count += 1
            continue

        seen_urls.add(normalized_url)
        digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:16]
        published_date = candidate.get("published_date")
        source_type = candidate.get("source_type")
        accepted.append(
            ResearchSource(
                source_id=f"src_{digest}",
                title=title.strip(),
                url=normalized_url,
                domain=domain,
                snippet=snippet.strip(),
                relevance_score=relevance,
                source_type=(
                    source_type.strip()
                    if isinstance(source_type, str) and source_type.strip()
                    else "unknown"
                ),
                published_date=(
                    published_date.strip()
                    if isinstance(published_date, str) and published_date.strip()
                    else None
                ),
            )
        )

    accepted.sort(
        key=lambda source: (
            -source.relevance_score,
            source.domain,
            source.url,
        )
    )
    per_domain: Counter[str] = Counter()
    selected: list[ResearchSource] = []
    for source in accepted:
        if len(selected) == 10:
            rejected_count += 1
            continue
        if per_domain[source.domain] >= _MAX_SOURCES_PER_DOMAIN:
            rejected_count += 1
            continue
        per_domain[source.domain] += 1
        selected.append(source)
    return selected, duplicate_count, rejected_count
