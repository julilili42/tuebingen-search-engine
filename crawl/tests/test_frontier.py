from tuebingen_crawler.frontier import Frontier


def test_pop_returns_highest_priority_first():
    frontier = Frontier()
    frontier.push("https://a.com/low", 1.0)
    frontier.push("https://a.com/high", 5.0)
    frontier.push("https://a.com/mid", 3.0)

    order = [frontier.pop_ready(lambda host: True) for _ in range(3)]
    assert order == ["https://a.com/high", "https://a.com/mid", "https://a.com/low"]


def test_equal_priorities_are_fifo():
    frontier = Frontier()
    frontier.push("https://a.com/first", 1.0)
    frontier.push("https://a.com/second", 1.0)

    assert frontier.pop_ready(lambda host: True) == "https://a.com/first"


def test_push_deduplicates_urls():
    frontier = Frontier()
    assert frontier.push("https://a.com/x", 1.0)
    assert not frontier.push("https://a.com/x", 9.0)
    assert len(frontier) == 1


def test_pop_ready_skips_hosts_in_politeness_window():
    frontier = Frontier()
    frontier.push("https://busy.com/high", 5.0)
    frontier.push("https://idle.com/low", 1.0)

    url = frontier.pop_ready(lambda host: host != "busy.com")
    assert url == "https://idle.com/low"
    # The deferred entry is still queued.
    assert frontier.pop_ready(lambda host: True) == "https://busy.com/high"


def test_pop_ready_returns_none_when_no_host_ready():
    frontier = Frontier()
    frontier.push("https://busy.com/page", 1.0)
    assert frontier.pop_ready(lambda host: False) is None
    assert len(frontier) == 1


def test_state_roundtrip_preserves_order_and_seen():
    frontier = Frontier()
    frontier.push("https://a.com/1", 2.0)
    frontier.push("https://a.com/2", 7.0)
    frontier.pop_ready(lambda host: True)

    heap, next_seq, seen = frontier.to_state()
    restored = Frontier.from_state(heap, next_seq, seen)

    assert not restored.push("https://a.com/2", 1.0)  # still deduplicated
    assert restored.pop_ready(lambda host: True) == "https://a.com/1"
