"""Tests for the rak-muenchen profile parser (no network)."""
from __future__ import annotations

from app.scraper.rak_muenchen import RakMuenchenScraper

_PROFILE_HTML = """
<html><body>
  <h1>Dr. Anna Müller</h1>
  <div class="kanzlei">Müller &amp; Partner Rechtsanwälte</div>
  <span class="ort">München</span>
  <div class="anschrift">Maximilianstraße 12, 80539 München</div>
  <a href="mailto:a.mueller@example.com">Email</a>
  <a href="tel:+49891234567">Call</a>
  <span class="fachgebiet">Employment</span>
  <span class="fachgebiet">Labour Law</span>
  <div class="sprachen">German, English</div>
</body></html>
"""


def test_parse_profile_extracts_fields():
    parsed = RakMuenchenScraper.parse_profile(
        _PROFILE_HTML, "https://example.com/profil/mueller"
    )
    assert parsed is not None
    assert parsed.name == "Dr. Anna Müller"
    assert parsed.city == "München"
    assert parsed.email == "a.mueller@example.com"
    assert parsed.phone == "+49891234567"
    assert "Employment" in parsed.specializations
    assert "Labour Law" in parsed.specializations
    assert parsed.content_hash  # computed


def test_parse_profile_is_deterministic():
    a = RakMuenchenScraper.parse_profile(_PROFILE_HTML, "https://example.com/x")
    b = RakMuenchenScraper.parse_profile(_PROFILE_HTML, "https://example.com/x")
    assert a.source_key == b.source_key
    assert a.content_hash == b.content_hash


def test_parse_profile_missing_name_returns_none():
    assert RakMuenchenScraper.parse_profile("<html></html>", "u") is None
