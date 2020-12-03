from pytest import raises

from goodenough import GoodEnough


def test_minimal_example():

    async def get_items(request):  # we just return a list, but get_items() can do anything like selecting records from a database etc
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_items)
    assert ge.pick({}) == 1  # since we didn't provide rules, the first item is returned


def test_get_items_should_be_coro_func():

    def get_items(request):  # forgot async!
        return [1, 2, 3, 4, 5]

    with raises(AssertionError, match=r"Expected coroutine function.*get_items"):
        GoodEnough(get_items)


def test_rules():

    async def rule_greatest(request, item):     # rule #1
        return 1 - 1 / item

    async def rule_even(request, item):         # rule #2
        return item % 2 == 0

    async def get_items(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_items, rules=[rule_greatest, rule_even])
    assert ge.pick({}) == 4  # greatest even


def test_rules_should_be_coro_funcs():

    def rule_greatest(request, item):  # forgot async!
        return 1 - 1 / item

    async def get_items(request):
        return [1, 2, 3, 4, 5]

    with raises(AssertionError, match=r"Expected coroutine function.*rule_greatest"):
        GoodEnough(get_items, rules=[rule_greatest])


def test_clamped_coefs():

    async def rule_greatest_done_wrong(request, item):
        return item  # will get clamped inside 0..1, so in case of [1,2,3,4,5] will always be 1.

    async def get_items(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_items, rules=[rule_greatest_done_wrong])
    assert ge.pick({}) == 1  # and not 5


def test_request_in_rules():

    async def rule_close_to_request(request, item):  # request can be anything, it's a number in this example
        return 1 - abs(request - item)

    async def get_items(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_items, rules=[rule_close_to_request])
    assert ge.pick(request=2.8) == 3  # item 3 is the closest to 2.8


def test_request_in_get_items():

    async def get_items(request):
        return range(request["from"], request["to"])  # request can be anything, it's a dict in this example

    ge = GoodEnough(get_items, rules=[])
    assert ge.pick(request={"from": 7, "to": 11}) == 7  # no rules -- return the first


def test_review_items():
    wi = None

    async def rule_one_tenth(request, item):  # not a meaningful rule, just illustrating example
        return item / 10

    async def get_items(request):
        return [1, 2, 3, 4, 5]

    async def review_items(request, weighed_items):  # a good place for saving the info about the picked item (the first in weighed_items) back to a database
        nonlocal wi
        wi = weighed_items

    ge = GoodEnough(get_items, review_items, rules=[rule_one_tenth])
    assert ge.pick({}) == 5
    assert wi[0] == (5, 0.5)
    assert wi[1] == (4, 0.4)
    assert wi[2] == (3, 0.3)
    assert wi[3] == (2, 0.2)
    assert wi[4] == (1, 0.1)


def test_xxxxxxxx():


    55/0



# never return items w 0 coef (or let define strategy: retry n times, raise, still return)
# rules weights
# silent clamp? shouldn't we complain / throw warning?
