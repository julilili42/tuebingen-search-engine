import heapq
from .models import CrawlState

# pushes on the min-heap
def push_frontier(state: CrawlState, score: float, url: str, depth: int) -> None:
    state.counter += 1
    heapq.heappush(state.frontier, [-score, state.counter, url, depth])

# pops from the min-heap
def pop_frontier(state: CrawlState) -> tuple[str, int]:
    _, _, url, depth = heapq.heappop(state.frontier)
    return url, depth