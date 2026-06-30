import sqlite3

from tuebingen_labeling.server import init_schema, link_candidates, upsert_link_results


def make_connection() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    init_schema(con)
    return con


def link_record(host: str, index: int, raw_score: float = 9.0) -> dict[str, object]:
    target_url = f"https://{host}/page-{index}"
    return {
        "parent_url": f"https://parent.example/{host}/{index}",
        "parent_host": "parent.example",
        "parent_depth": 0,
        "parent_pageverdict_score": 0.9,
        "parent_pageverdict_label": "positive",
        "parent_pageverdict_decision": "index_strong",
        "parent_relevance": 8.0,
        "anchor": f"Tuebingen link {index}",
        "target_url": target_url,
        "target_host": host,
        "target_depth": 1,
        "raw_score": raw_score,
        "should_enqueue": True,
        "selected": True,
        "rejection_reason": None,
        "target_status": None,
        "target_status_code": None,
        "target_content_type": None,
        "target_language": None,
        "target_relevance": None,
        "target_token_count": None,
        "target_pageverdict_score": 0.52,
        "target_pageverdict_label": "positive",
        "target_pageverdict_decision": "index_cautious",
        "target_exclusion_reason": None,
        "target_fetched_at": None,
        "source": "crawler_linkverdict",
        "notes": "",
    }


def test_link_candidates_round_robins_hosts_before_repeating_a_dominant_host():
    con = make_connection()
    dominant = [link_record("dominant.example", index) for index in range(10)]
    diverse = [
        link_record("b.example", 1, raw_score=8.0),
        link_record("c.example", 1, raw_score=7.0),
        link_record("d.example", 1, raw_score=6.0),
    ]
    with con:
        upsert_link_results(con, [*dominant, *diverse])

    results = link_candidates(con, limit=4, unlabeled_only=True)

    assert len(results) == 4
    assert len({result.target_host for result in results}) == 4


def test_link_candidates_push_navigation_noise_behind_content_links():
    con = make_connection()
    navigation = link_record("nav.example", 1, raw_score=10.0)
    navigation["parent_url"] = navigation["target_url"]
    navigation["anchor"] = "Jump to content"
    navigation["rejection_reason"] = "seen_url"

    content = link_record("content.example", 1, raw_score=5.0)
    content["anchor"] = "Tuebingen city history"

    with con:
        upsert_link_results(con, [navigation, content])

    [first] = link_candidates(con, limit=1, unlabeled_only=True)

    assert first.target_host == "content.example"
