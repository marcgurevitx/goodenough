import asyncio
import collections
import inspect
import json

try:
    from aiohttp import web
except ImportError:
    web = None

GEW_PORT = 4181


def clamp(x, low, high):
    return min(high, max(low, x))


ScoredItem = collections.namedtuple("ScoredItem", "item, score")


class GoodEnough:
    """
    The class that knows how to pick items.

    See async_pick() for the core logic.
    Call serve() to run a simple web server.
    """

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

    def pick(self, request, *, default=None):
        """Call async_pick inside asyncio loop."""
        return asyncio.run(self.async_pick(request, default=default))

    async def async_pick(self, request, *, default=None):
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
        first = scored_items[0]
        if self.review_items:
            await self.review_items(request, scored_items, is_successful=(first.score > 0.))
        if first.score > 0.:
            result = first.item
        else:
            result = default
        return result

    def serve(self, *, port=GEW_PORT):
        """Runs aiohttp web server that responds to POST /fetch with an item."""
        assert web, AssertionError("Install aiohttp or goodenough[web]")
        app = web.Application()
        app.add_routes([web.post("/fetch", self.fetch)])
        web.run_app(app, port=port)

    async def fetch(self, web_request):
        """Calls async_pick() on a POST /fetch."""
        assert web, AssertionError("Install aiohttp or goodenough[web]")
        try:
            request_data = await web_request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Got bad JSON")
        response_data = await self.async_pick(request_data)
        return web.json_response(response_data)
