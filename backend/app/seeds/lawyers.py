"""Sample lawyer seed data (Munich / Germany).

This realistic-but-fictional dataset lets the directory and search features
work end-to-end without running the live scraper. Real data is populated by
LawyerService.sync_live(). The records are shaped exactly like scraper output
so they exercise the same upsert path.
"""
from __future__ import annotations

import hashlib

from app.scraper.rak_muenchen import ParsedLawyer


def _key(profile_url: str) -> str:
    return hashlib.sha256(profile_url.encode()).hexdigest()[:32]


_RAW = [
    {
        "name": "Dr. Anna Müller",
        "law_firm": "Müller & Partner Rechtsanwälte",
        "city": "München",
        "email": "a.mueller@mueller-partner.example",
        "phone": "+49 89 1234567",
        "website": "https://mueller-partner.example",
        "address": "Maximilianstraße 12, 80539 München",
        "languages": "German, English",
        "specializations": ["Employment", "Labour Law"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/mueller",
    },
    {
        "name": "Stefan Becker",
        "law_firm": "Becker Legal",
        "city": "München",
        "email": "becker@becker-legal.example",
        "phone": "+49 89 7654321",
        "website": "https://becker-legal.example",
        "address": "Sendlinger Str. 5, 80331 München",
        "languages": "German, English, Turkish",
        "specializations": ["Immigration", "Family"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/becker",
    },
    {
        "name": "Dr. Laura Schneider",
        "law_firm": "Schneider Mietrecht",
        "city": "München",
        "email": "schneider@schneider-mietrecht.example",
        "phone": "+49 89 2223344",
        "website": "https://schneider-mietrecht.example",
        "address": "Leopoldstraße 50, 80802 München",
        "languages": "German",
        "specializations": ["Rental", "Tenancy Law"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/schneider",
    },
    {
        "name": "Michael Hoffmann",
        "law_firm": "Hoffmann & Co.",
        "city": "Augsburg",
        "email": "m.hoffmann@hoffmann-co.example",
        "phone": "+49 821 998877",
        "website": "https://hoffmann-co.example",
        "address": "Maximilianstraße 40, 86150 Augsburg",
        "languages": "German, English",
        "specializations": ["Consumer", "Insurance"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/hoffmann",
    },
    {
        "name": "Dr. Julia Wagner",
        "law_firm": "Wagner Verkehrsrecht",
        "city": "München",
        "email": "wagner@wagner-verkehr.example",
        "phone": "+49 89 4455667",
        "website": "https://wagner-verkehr.example",
        "address": "Schwanthalerstr. 10, 80336 München",
        "languages": "German, French",
        "specializations": ["Traffic", "Insurance"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/wagner",
    },
    {
        "name": "Thomas Fischer",
        "law_firm": "Fischer Steuer & Recht",
        "city": "München",
        "email": "fischer@fischer-steuer.example",
        "phone": "+49 89 5566778",
        "website": "https://fischer-steuer.example",
        "address": "Brienner Str. 25, 80333 München",
        "languages": "German, English",
        "specializations": ["Tax", "Business"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/fischer",
    },
    {
        "name": "Dr. Petra Klein",
        "law_firm": "Klein Familienrecht",
        "city": "Nürnberg",
        "email": "klein@klein-familie.example",
        "phone": "+49 911 334455",
        "website": "https://klein-familie.example",
        "address": "Königstraße 60, 90402 Nürnberg",
        "languages": "German, English, Spanish",
        "specializations": ["Family", "Employment"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/klein",
    },
    {
        "name": "Andreas Weber",
        "law_firm": "Weber Wirtschaftskanzlei",
        "city": "München",
        "email": "weber@weber-wirtschaft.example",
        "phone": "+49 89 6677889",
        "website": "https://weber-wirtschaft.example",
        "address": "Promenadeplatz 8, 80333 München",
        "languages": "German, English, Italian",
        "specializations": ["Business", "Consumer"],
        "profile_url": "https://www.rak-muenchen.de/anwaltsverzeichnis/profil/weber",
    },
]


def sample_lawyers() -> list[ParsedLawyer]:
    out: list[ParsedLawyer] = []
    for raw in _RAW:
        url = raw["profile_url"]
        content_hash = hashlib.sha256(
            (raw["name"] + raw["city"] + ",".join(raw["specializations"])).encode()
        ).hexdigest()[:32]
        out.append(
            ParsedLawyer(
                source_key=_key(url),
                name=raw["name"],
                law_firm=raw["law_firm"],
                city=raw["city"],
                email=raw["email"],
                phone=raw["phone"],
                website=raw["website"],
                address=raw["address"],
                profile_url=url,
                languages=raw["languages"],
                specializations=raw["specializations"],
                content_hash=content_hash,
            )
        )
    return out
