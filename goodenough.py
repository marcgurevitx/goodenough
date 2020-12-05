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

class GoodEnoughResult:
    """Simple wrapper for values returned by `review_result` callback."""

    def __init__(self, value, /):
        self.value = value


class GoodEnough:
    """
    The class that knows how to pick items.

    See async_pick() for the core logic.
    Call serve() to run a simple web server.
    """

    def __init__(self, get_items, review_items=None, review_result=None, *, rules=None):
        rules = rules or {}
        for function in [get_items, review_items, review_result, *rules]:
            if function:
                assert inspect.iscoroutinefunction(function), f"Expected coroutine function, got {function!r}"
        self.get_items = get_items
        self.review_items = review_items
        self.review_result = review_result
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
        await self._apply_rules(request, scored_items)
        scored_items.sort(key=lambda i: i.score, reverse=True)
        result = await self._pick_result(request, scored_items, default)
        return result

    async def _apply_rules(self, request, scored_items):
        """Apply rules functions to the array of selected items.

        The array of items is modified in place.
        """
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

    async def _pick_result(self, request, scored_items, default):
        """Review the items after rules applied and choose the best result."""
        if self.review_items:
            _throw_away = await self.review_items(request, scored_items, is_successful=(scored_items[0].score > 0.))
            if _throw_away is not None:
                raise Exception(f"You should not return things other than None from review_items(); got {_throw_away!r}")
        first = scored_items[0]
        is_successful = first.score > 0.
        if is_successful:
            result = first.item
        else:
            result = default
        if self.review_result:
            wrapped_result = await self.review_result(request, result, is_successful=is_successful)
            if not isinstance(wrapped_result, GoodEnoughResult):
                raise Exception(f"You must return GoodEnoughResult() from review_result(); got {wrapped_result!r}")
            result = wrapped_result.value
        return result

    def serve(self, *, port=GEW_PORT):
        """Runs aiohttp web server that responds to POST /fetch with an item."""
        assert web, AssertionError("Install aiohttp or goodenough[web]")
        app = web.Application()
        app.add_routes([web.post("/fetch", self._fetch)])
        web.run_app(app, port=port)

    async def _fetch(self, web_request):
        """Calls async_pick() on a POST /fetch."""
        assert web, AssertionError("Install aiohttp or goodenough[web]")
        try:
            request_data = await web_request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Got bad JSON")
        response_data = await self.async_pick(request_data)
        return web.json_response(response_data)
