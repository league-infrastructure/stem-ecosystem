from pathlib import Path

from partner_scrape.profiles.discover import discover_profile_pages
from partner_scrape.profiles.extract import extract_facts

FIX = Path(__file__).parent / "fixtures" / "profiles"
HOME = "https://visitcmod.org/"


def _cmod() -> str:
    return (FIX / "cmod_home.html").read_text()


def test_discover_picks_one_about_one_contact_same_site():
    d = discover_profile_pages(HOME, _cmod())
    assert d.about == "https://visitcmod.org/about-us"  # shallower than /about-us/careers
    assert d.contact == "https://visitcmod.org/contact-us/"  # contact beats visit
    assert all("other.example.com" not in c.url for c in d.candidates)


def test_discover_is_deterministic():
    a = discover_profile_pages(HOME, _cmod(), ["https://visitcmod.org/our-story"])
    b = discover_profile_pages(HOME, _cmod(), ["https://visitcmod.org/our-story"])
    assert a == b


def test_discover_visit_is_contact_fallback():
    html = '<a href="/plan-your-visit">Visit Us</a>'
    assert discover_profile_pages(HOME, html).contact == "https://visitcmod.org/plan-your-visit"


def test_discover_from_sitemap_only_and_www_same_site():
    d = discover_profile_pages(
        HOME, "<html></html>",
        ["https://www.visitcmod.org/who-we-are", "https://evil.example/contact",
         "https://visitcmod.org/contact"],
    )
    assert d.about == "https://www.visitcmod.org/who-we-are"
    assert d.contact == "https://visitcmod.org/contact"


def test_discover_anchor_beats_sitemap_and_skips_junk():
    html = '<a href="mailto:a@b.c">Contact</a><a href="/files/about.pdf">About</a><a href="#about">About</a>'
    d = discover_profile_pages(HOME, html, ["https://visitcmod.org/about"])
    assert d.about == "https://visitcmod.org/about"
    assert d.contact is None


def test_discover_malformed_html():
    d = discover_profile_pages(HOME, '<a href="/about>About<div <<a href=/contact>Contact')
    assert isinstance(d.candidates, list)
    assert discover_profile_pages(HOME, "").about is None


def test_extract_cmod_facts():
    f = extract_facts(_cmod())
    assert f.title == "Children's Museum of Discovery | San Diego"
    assert f.og_site_name == "Children's Museum of Discovery"
    assert len(f.jsonld) == 1  # WebSite is not an organization type
    org = f.jsonld[0]
    assert org["name"] == "Children's Museum of Discovery"
    assert org["telephone"] == "+1-619-233-5437"
    assert org["email"] == "info@visitcmod.org"
    assert org["address"]["streetAddress"] == "200 W Island Ave"
    assert org["logo"] == "https://visitcmod.org/logo.png"
    assert "https://www.instagram.com/visitcmod/" in org["sameAs"]
    assert f.socials == {
        "twitter": "https://x.com/visitcmod",
        "facebook": "https://www.facebook.com/visitcmod",
        "instagram": "https://instagram.com/visitcmod",
        "linkedin": "https://www.linkedin.com/company/cmod",
    }
    assert f.emails == ["info@visitcmod.org", "press@visitcmod.org"]
    assert f.phones == ["+16192335437"]
    assert f.to_dict()["og_site_name"] == f.og_site_name


def test_extract_malformed_never_raises():
    html = (
        '<title>Hi<script type="application/ld+json">{bad json</script>'
        '<script type="application/ld+json">[{"@type":"Organization","name":"Ok","sameAs":"https://a.b"},5,null]</script>'
        '<a href="mailto:">x</a><a href="http://[bad">y</a><footer><a href'
    )
    f = extract_facts(html)
    assert f.jsonld[0]["name"] == "Ok"
    assert f.jsonld[0]["sameAs"] == ["https://a.b"]
    assert extract_facts("").title == ""
    assert extract_facts(None).socials == {}  # type: ignore[arg-type]
