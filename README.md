# goodenough

A small Python lib that helps one to pick items from their collections / storages.

```bash
pip install goodenough
```

It's designed for tasks where you need a random item that is also not complete garbage like selecting the next song from a songs database to play on the radio.

To use this lib you should tell it how to get the sample of items (`get_items`) and how to sort them from good to bad (`rules`).

Optionaly, you can also reflect on how the items got sorted and which item has won (`review_items`, `review_result`).

## Callbacks

All callbacks should be async in case you want to do I/O stuff (like talking to a storage).

Every callback's first argument should be `request` -- an opaque data passed to `.pick()` or `.async_pick()` (in case of a web server started by `.serve()`, the `request` is JSON-deserialized POST body).

Here we define `get_items` callback that selects random documents from Mongo (but it can be any data source of your choice):

```python
from motor.motor_asyncio import AsyncIOMotorClient
from goodenough import GoodEnough

async def get_items(request):
    client = AsyncIOMotorClient()
    collection = client.test.things  # assumed test.things is prepopulated
    pipeline = [{"$sample": {"size": request["size"]}}]
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(None)

g = GoodEnough(get_items)
print(g.pick(request={"size": 1}))  # should print a random document from test.things
```

In `request` we pass `"size"` equals to 1 to select one random document.

We could pass a greater size value, but `.pick()` and `.async_pick()` only return one result, so in this example it wouldn't be useful.

However, if we define one or more `rules` functions, it will make sense to select a bigger sample and then choose the "best" item.

Each rule function receives `request` and one `item` and is expected to return the `float` between `0.` and `1.`, where `0.` is "the worst" and `1.` is "the best".

Here we extend our previous example and write a rule that gives greater chance to documents whose `"foo"` field is closer to `request["foo"]`.

```python

#...

async def rule_foo(request, item):
    if item["foo"] == request["foo"]:
        return 1.
    else:
        return 1 / abs(item["foo"] - request["foo"])

g = GoodEnough(
    get_items,
    rules=[ rule_foo ],
)
print(g.pick(request={"size": 5, "foo": 15}))
```
Many rules can be supplied, in which case the resulting score of an item will be a product of scores returned from the `rules` functions.

`goodenough` also supports rules weights. See tests.

If a rule functions returns `0.`, the item is then never returned by `.pick()`.

If each item in a sample gains score `0.`, the `None` is returned, or if you supply `default=` parameter to `.pick()`, that is returned.

The `review_items` callback (if it's defined) is invoked after all rules are applied and the items got sorted from "best" to "worst" by their scores.

This callback can be used for example to communicate information back to the database about last resulting scores.

Its second argument `scored_items` is a list of named pairs `[... (item=item, score=score) ...]`.

The `is_successful` flag tells the callback whether any item is going to be returned (`True`) or it's going to by the default (`False`).

If `is_successful` is true, the picked item will be the first element in `scored_items`.

Here we extend our example to increment a `"pickedCount"` value in Mongo:

```python

#...

async def review_items(request, scored_items, is_successful):
    if is_successful:
        picked = scored_items[0]  # picked is a named pair (item=..., score=...)
        client = AsyncIOMotorClient()
        collection = client.test.things
        await collection.update_one(
            {"_id": picked.item["_id"]},
            {"$inc": {"pickedCount": 1}},
        )

g = GoodEnough(
    get_items,
    review_items=review_items,
    rules=[ rule_foo ],
)
print(g.pick(request={"size": 5, "foo": 15}))
```

Another optional callback is `review_result` that receives the picked item and can modify it.

This callback must return and the returned value must be a `GoodEnoughResult` object, see below.

Even if you're not going to modify the result in this callback, you have to explicitly write `return GoodEnoughResult(result)`.

Here we again extend the previous example by writing a callback that will add current datetime to the item before returning it from `.pick()`.

```python
import datetime
from goodenough import GoodEnough, GoodEnoughResult

# ...

async def review_result(request, result, is_successful):
    if is_successful:
        result["dtPicked"] = datetime.datetime.now(datetime.timezone.utc)
    return GoodEnoughResult(result)

g = GoodEnough(
    get_items,
    review_items=review_items,
    review_result=review_result,
    rules=[ rule_foo ],
)
print(g.pick(request={"size": 5, "foo": 15}))
```

## Web server

This lib has a small web server capable of returning a picked item in response to `POST /fetch`.

It requires `aiohttp`, so either `pip install aiohttp` or `pip install goodenough[web]`.

To start the web server call `.serve()`.

The `request` parameter to the callbacks will be constructed by JSON-deserializing of the web request's body.

The response body will be the JSON-serialized result from `*pick()`.

Let's again update our previous example:

(To avoid JSON error trying to serialize Mongo's ObjectId, we will convert it to `str` in a new version of the `review_result` callback.)

```python

#...

async def review_result(request, result, is_successful):
    if is_successful:
        result["dtPicked"] = str(datetime.datetime.now(datetime.timezone.utc))
        result["_id"] = str(result["_id"])
    return GoodEnoughResult(result)

#...

g.serve(port=9000)  # the default port is 4181 for no comprehensible reason
```

And here we call it:

```bash
$ curl -s -XPOST http://localhost:9000/fetch -d'{"size": 5, "foo": 15}' | jq .
{
  "_id": "5fcb503f107390ce97e7d04f",
  "foo": 16,
  "pickedCount": 9,
  "dtPicked": "2020-12-05 14:48:46.471336+00:00"
}
```
