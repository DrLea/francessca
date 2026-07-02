"""Scraper for the Munich Bar Association lawyer directory.

Source: https://www.rak-muenchen.de/anwaltsverzeichnis/

Design notes
------------
* The scraper is polite: it rate-limits requests and reuses a Redis-backed
  cache keyed by the page hash so previously parsed pages are not re-fetched
  or re-parsed unless their content actually changed.
* Parsing is isolated in `parse_profile` so it can be unit-tested against
  static HTML fixtures without any network access.
* Each parsed entry produces a deterministic `source_key` (a hash of the
  profile URL) and a `content_hash` (a hash of the parsed fields). The
  repository upsert uses these to skip unchanged records — see
  LawyerRepository.upsert.

This module intentionally does not run automatically. Synchronisation is
triggered explicitly via LawyerSyncService (admin endpoint or CLI), which lets
us run it on a schedule without it firing on every request.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.redis_client import redis_client

log = get_logger("francessca.scraper")

BASE_URL = "https://www.rak-muenchen.de"
DIRECTORY_PATH = "/anwaltsverzeichnis/"
_CACHE_TTL = 60 * 60 * 24  # 24h
_REQUEST_DELAY = 1.0  # seconds between requests (politeness)
_USER_AGENT = "FrancesscaBot/0.1 (+https://francessca.app; legal-prep assistant)"


@dataclass
class ParsedLawyer:
    source_key: str
    name: str
    law_firm: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    photo_url: str | None = None
    profile_url: str | None = None
    languages: str | None = None
    specializations: list[str] = field(default_factory=list)
    content_hash: str = ""

    def to_upsert_dict(self) -> dict:
        return {
            "source_key": self.source_key,
            "name": self.name,
            "law_firm": self.law_firm,
            "city": self.city,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "photo_url": self.photo_url,
            "profile_url": self.profile_url,
            "languages": self.languages,
            "content_hash": self.content_hash,
            "specializations": self.specializations,
        }


def _hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:32]


def _cache_key(url: str) -> str:
    return f"scraper:rak:page:{_hash(url)}"


class RakMuenchenScraper:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            headers={"User-Agent": _USER_AGENT}, timeout=20.0, follow_redirects=True
        )

    # -- fetching ---------------------------------------------------------
    def fetch(self, url: str, use_cache: bool = True) -> str | None:
        """Fetch a page, returning cached HTML when unchanged.

        Caching avoids unnecessary requests: we store the page hash and HTML
        in Redis; if a re-fetch returns identical content we skip re-parsing.
        """
        if use_cache:
            cached = redis_client.get(_cache_key(url))
            if cached is not None:
                log.info("scraper cache hit url=%s", url)
                return cached
        try:
            time.sleep(_REQUEST_DELAY)
            resp = self._client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("scraper fetch failed url=%s err=%s", url, exc)
            return None
        html = resp.text
        redis_client.setex(_cache_key(url), _CACHE_TTL, html)
        return html

    # -- parsing ----------------------------------------------------------
    @staticmethod
    def discover_profile_links(listing_html: str) -> list[str]:
        """Extract absolute profile URLs from a directory listing page."""
        soup = BeautifulSoup(listing_html, "lxml")
        links: list[str] = []
        for a in soup.select("a[href]"):
            href = a["href"]
            if "anwaltsverzeichnis" in href and any(
                tok in href for tok in ("/profil", "detail", "rechtsanwalt")
            ):
                links.append(href if href.startswith("http") else BASE_URL + href)
        return sorted(set(links))

    @staticmethod
    def parse_profile(html: str, profile_url: str) -> ParsedLawyer | None:
        """Parse a single lawyer profile page into a ParsedLawyer.

        Selectors are written defensively; missing fields are tolerated. The
        directory markup may change, so this function is the single place to
        adjust when that happens, and it is covered by fixture-based tests.
        """
        soup = BeautifulSoup(html, "lxml")

        def text_of(selector: str) -> str | None:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else None

        name = (
            text_of("h1")
            or text_of(".profile-name")
            or text_of("[itemprop=name]")
        )
        if not name:
            return None

        email_el = soup.select_one("a[href^=mailto]")
        email = email_el["href"].replace("mailto:", "").strip() if email_el else None
        phone_el = soup.select_one("a[href^=tel]")
        phone = phone_el["href"].replace("tel:", "").strip() if phone_el else None
        web_el = soup.select_one("a[href^=http][rel=external], a.website[href^=http]")
        website = web_el["href"].strip() if web_el else None
        img = soup.select_one(".profile-photo img, img[itemprop=image]")
        photo_url = img["src"] if img and img.has_attr("src") else None

        specializations = [
            el.get_text(strip=True)
            for el in soup.select(".specialization, [itemprop=specialty], .fachgebiet")
            if el.get_text(strip=True)
        ]
        languages_el = soup.select_one(".languages, .sprachen")
        languages = languages_el.get_text(strip=True) if languages_el else None

        parsed = ParsedLawyer(
            source_key=_hash(profile_url),
            name=name,
            law_firm=text_of(".law-firm, [itemprop=worksFor], .kanzlei"),
            city=text_of("[itemprop=addressLocality], .city, .ort"),
            email=email,
            phone=phone,
            website=website,
            address=text_of("[itemprop=streetAddress], .address, .anschrift"),
            photo_url=photo_url,
            profile_url=profile_url,
            languages=languages,
            specializations=specializations,
        )
        parsed.content_hash = _hash(
            parsed.name, parsed.law_firm, parsed.city, parsed.email,
            parsed.phone, parsed.website, parsed.address,
            tuple(sorted(parsed.specializations)), parsed.languages,
        )
        return parsed

    def crawl(self, max_pages: int = 5) -> list[ParsedLawyer]:
        """Crawl the directory listing and parse each discovered profile."""
        results: list[ParsedLawyer] = []
        listing = self.fetch(BASE_URL + DIRECTORY_PATH)
        if not listing:
            return results
        links = self.discover_profile_links(listing)[: max_pages * 50]
        for url in links:
            html = self.fetch(url)
            if not html:
                continue
            parsed = self.parse_profile(html, url)
            if parsed:
                results.append(parsed)
        log.info("scraper crawl produced %d profiles", len(results))
        return results
