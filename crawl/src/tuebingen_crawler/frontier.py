from __future__ import annotations

import heapq
from collections.abc import Callable

from .urls import host_of

# How many queued entries a single pop may inspect while looking for a host
# that is polite to contact right now.
MAX_POP_SCAN = 50


class Frontier:
    """Priority queue of URLs to crawl.

    Entries are ``[-priority, seq, url]``: highest priority first, FIFO among
    equal priorities. ``seen`` contains every URL ever pushed, so a URL is
    enqueued at most once over the whole (resumable) crawl.
    """

    def __init__(self) -> None:
        self._heap: list[list] = []
        self._next_seq = 0
        self.seen: set[str] = set()

    def __len__(self) -> int:
        return len(self._heap)

    def push(self, url: str, priority: float) -> bool:
        if url in self.seen:
            return False
        self.seen.add(url)
        heapq.heappush(self._heap, [-priority, self._next_seq, url])
        self._next_seq += 1
        return True

    def pop_ready(self, host_is_ready: Callable[[str], bool]) -> str | None:
        """Pop the best URL whose host may be contacted now.

        Inspects at most MAX_POP_SCAN entries; deferred entries are re-queued.
        Returns None if no inspected host is ready yet.
        """
        deferred: list[list] = []
        result: str | None = None

        for _ in range(min(MAX_POP_SCAN, len(self._heap))):
            entry = heapq.heappop(self._heap)
            if host_is_ready(host_of(entry[2])):
                result = entry[2]
                break
            deferred.append(entry)

        for entry in deferred:
            heapq.heappush(self._heap, entry)
        return result

    def to_state(self) -> tuple[list[list], int, list[str]]:
        return sorted(self._heap), self._next_seq, sorted(self.seen)

    @classmethod
    def from_state(cls, heap: list[list], next_seq: int, seen: list[str]) -> Frontier:
        frontier = cls()
        frontier._heap = [list(entry) for entry in heap]
        heapq.heapify(frontier._heap)
        frontier._next_seq = next_seq
        frontier.seen = set(seen)
        return frontier
