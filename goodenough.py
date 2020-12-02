import asyncio
import collections
import inspect


def clamp(x, low, high):
    return min(high, max(low, x))


WeighedItem = collections.namedtuple("WeighedItem", "item, coef")


class GoodEnough:
    """The class where all 'good enough' magic happens."""

    def __init__(self, get_sample, *, rules=None):
        rules = rules or []
        for function in [get_sample, *rules]:
            assert inspect.iscoroutinefunction(function), f"Expected coroutine function, got {function!r}"
        self.get_sample = get_sample
        self.rules = rules

    def pick(self, request):
        """Call async_pick inside asyncio loop."""
        return asyncio.run(self.async_pick(request))

    async def async_pick(self, request):
        """Pick the best item from a sample."""
        weighed_items = [
            WeighedItem(item, coef=1.) for item in await self.get_sample(request)
        ]
        for rule in self.rules:
            for idx in range(len(weighed_items)):
                weighed_item = weighed_items[idx]
                coef = await rule(request, weighed_item.item)
                coef = clamp(coef, 0., 1.)
                coef *= weighed_item.coef
                weighed_items[idx] = weighed_item._replace(coef=coef)
        weighed_items.sort(key=lambda w: w.coef, reverse=True)

        # call updater

        return weighed_items[0].item
