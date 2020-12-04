import asyncio
import collections
import inspect


def clamp(x, low, high):
    return min(high, max(low, x))


ScoredItem = collections.namedtuple("ScoredItem", "item, score")


class GoodEnough:
    """Class that picks items (see async_pick for the main logic)."""

    def __init__(self, get_items, review_items=None, *, rules=None):
        rules = rules or {}
        for function in filter(None.__ne__, [get_items, review_items, *rules]):
            assert inspect.iscoroutinefunction(function), f"Expected coroutine function, got {function!r}"
        self.get_items = get_items
        self.review_items = review_items
        try:
            self.rules = dict(rules)
        except TypeError:
            self.rules = dict((r, 1.) for r in rules)

    def pick(self, request):
        """Call async_pick inside asyncio loop."""
        return asyncio.run(self.async_pick(request))

    async def async_pick(self, request):
        """Pick the best item from a sample."""
        scored_items = [
            ScoredItem(item, score=1.) for item in await self.get_items(request)
        ]
        for rule, rule_weight in self.rules.items():
            for idx in range(len(scored_items)):
                scored_item = scored_items[idx]
                if scored_item.score == 0:
                    continue
                score = await rule(request, scored_item.item)
                score = clamp(score, 0., 1.)
                score **= rule_weight
                score *= scored_item.score
                scored_items[idx] = scored_item._replace(score=score)
        scored_items.sort(key=lambda i: i.score, reverse=True)
        if self.review_items:
            await self.review_items(request, scored_items)
        return scored_items[0].item
