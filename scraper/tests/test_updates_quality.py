"""Event-quality checks with CMOD-shaped fixtures (sprint 043-007, issue 76)."""

import json
from datetime import date

from partner_scrape.storage import LocalStore
from partner_scrape.updates import quality as Q
from partner_scrape.updates.quality import run_quality

TODAY = date(2026, 10, 8)
YOUNG_TEXT = "Toddlers and preschoolers explore"


def ev(title, start="2026-10-13T10:00:00-07:00", **kw):
    e = {"title": title, "description": "", "link": "", "date_start": start,
         "date_end": "", "age_grade_level": ["Pre-K", "Family"], "cost_range": "Free"}
    e.update(kw)
    return e


def checks(findings):
    return [f.check for f in findings]


def test_non_events():
    evs = [ev("Member's Only Hours"), ev("Member\u2019s Only Hours"), ev("Holiday Hours"), ev("Museum Early Closure"),
           ev("Closed"), ev("Space Night"), ev("Closed Captioning Workshop")]
    got = Q.check_non_events("cmod", evs)
    assert [f.title for f in got] == ["Member's Only Hours", "Member\u2019s Only Hours", "Holiday Hours",
                                      "Museum Early Closure", "Closed"]


def test_duplicate_prefix_same_start_only():
    a = ev("Jimbo's Garden Workshop")
    b = ev("Jimbo's Garden Workshop: Strawberry Banana Snake")
    later = ev("Jimbo's Garden Workshop", start="2026-10-14T10:00:00-07:00")
    got = Q.check_duplicates("cmod", [a, b, later])
    assert len(got) == 1 and got[0].title == "Jimbo's Garden Workshop"
    assert "Strawberry" in got[0].detail
    assert Q.check_duplicates("cmod", [ev("Space Night"), ev("Space Nights Extra")]) == []


def test_date_link_mismatch():
    bad = ev("Member's Only Hours", link="https://visitcmod.org/event/members-only-hours/2026-10-27/")
    ok = ev("Space Night", link="https://visitcmod.org/e/space-night-2026-10-13-10-00")
    nodate = ev("Other", link="https://visitcmod.org/e/other")
    got = Q.check_date_link_mismatch("cmod", [bad, ok, nodate])
    assert [f.title for f in got] == ["Member's Only Hours"]
    assert "2026-10-27" in got[0].detail


def test_past_in_current_uses_end_date():
    past = ev("Old", start="2026-08-30T10:00:00-07:00")
    running = ev("Running", start="2026-10-01T10:00:00", date_end="2026-10-20T10:00:00")
    got = Q.check_past_in_current("cmod", [past, running], TODAY)
    assert [f.title for f in got] == ["Old"]


def test_age_toddler_text_with_teen_bands():
    e = ev("Tot Time", description=YOUNG_TEXT, age_grade_level=["Grades 6-8", "Grades 9-12"])
    fine = ev("Tot Time 2", description=YOUNG_TEXT, age_grade_level=["Pre-K"])
    got = Q.check_age_tags("cmod", [e, fine], [e, fine])
    assert [f.title for f in got] == ["Tot Time"]


def test_age_family_text_only_teen_bands_and_partner_comparison():
    fam = ev("Family Day", description="fun for kids", age_grade_level=["Grades 9-12"])
    teen = ev("Teen Night", description="for high school students",
              age_grade_level=["Grades 9-12"])
    assert checks(Q.check_age_tags("cmod", [fam, teen], [fam, teen])) == ["age_implausible"]
    # partner comparison needs >= 3 other events, mostly young
    odd = ev("Garden Workshop", age_grade_level=["Grades 6-8", "Grades 9-12"])
    others = [ev(f"E{i}") for i in range(3)]
    assert checks(Q.check_age_tags("cmod", [odd], [odd] + others)) == ["age_implausible"]
    assert Q.check_age_tags("cmod", [odd], [odd, others[0]]) == []


def test_missing_cost():
    blank = ev("Space Night", description="Tickets $20/$17/$13/$7", cost_range="")
    free = ev("Garden", description="Included with $17 admission", cost_range="Free")
    truly_free = ev("Open Day", description="Free admission for all", cost_range="Free")
    priced = ev("Camp", description="$50 fee", cost_range="Less than $100")
    got = Q.check_missing_cost("cmod", [blank, free, truly_free, priced])
    assert [f.title for f in got] == ["Space Night", "Garden"]


def test_recurring_collapsed():
    one = ev("Garden Workshop", description="Sessions at 11:00 am and 2:00 pm")
    both = [ev("Garden Workshop", description="at 11 am and 2 pm", start="2026-10-13T11:00:00"),
            ev("Garden Workshop", description="at 11 am and 2 pm", start="2026-10-13T14:00:00")]
    single_time = ev("Story", description="at 11 am")
    assert checks(Q.check_recurring_collapsed("cmod", [one, single_time])) == ["recurring_collapsed"]
    assert Q.check_recurring_collapsed("cmod", both) == []


def envelope(events):
    return {"partner_slug": "cmod", "kind": "current", "event_count": len(events), "events": events}


def test_run_quality_reads_store_groups_and_never_writes(tmp_path):
    store = LocalStore(tmp_path)
    store.write_json("partners/cmod/events.json", envelope([
        ev("Member's Only Hours", link="https://x.org/2026-10-27"),
        ev("Old", start="2026-08-30T10:00:00")]))
    store.write_json("partners/cmod/past-events.json", envelope([]))
    store.write_json("opportunities.json", [dict(ev("Space Night", description="$20 tickets",
                                                    cost_range=""), partner_id=2)])
    roster = [{"slug": "cmod", "id": 1}, {"slug": "other", "id": 2}, {"slug": "empty", "id": 3}]
    before = {k: store.read_text(k) for k in store.list("")}
    rep = run_quality(roster, store, today=TODAY)
    assert {k: store.read_text(k) for k in store.list("")} == before
    assert rep.partners_examined == 3 and rep.events_examined == 3
    assert list(rep.by_partner()) == ["cmod", "other"]  # fallback to opportunities.json
    assert rep.counts["non_event"] == 1 and rep.counts["date_link_mismatch"] == 1
    assert rep.counts["past_in_current"] == 1 and rep.counts["missing_cost"] == 1
    d = rep.to_dict()
    assert d["total"] == len(rep.findings) and set(d["counts"]) == set(Q.CHECKS)
    assert set(d["partners"]["cmod"][0]) == {"slug", "check", "title", "url", "detail"}
    assert rep.lines()[-1].startswith("event-quality: partners=3 events=3 findings=")
    assert run_quality(roster, store, today=TODAY, slug="other").partners_examined == 1
