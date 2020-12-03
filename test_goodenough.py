from pytest import raises

from goodenough import GoodEnough


def test_minimal_example():

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_sample)
    assert ge.pick({}) == 1  # since we didn't provide rules, the first item is returned


def test_get_sample_should_be_coro_func():

    def get_sample(request):  # forgot async!
        return [1, 2, 3, 4, 5]

    with raises(AssertionError, match=r"Expected coroutine function.*get_sample"):
        GoodEnough(get_sample)


def test_rules():

    async def rule_greatest(request, item):     # rule #1
        return 1 - 1 / item

    async def rule_even(request, item):         # rule #2
        return item % 2 == 0

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_sample, rules=[rule_greatest, rule_even])
    assert ge.pick({}) == 4  # greatest even


def test_rules_should_be_coro_funcs():

    def rule_greatest(request, item):  # forgot async!
        return 1 - 1 / item

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    with raises(AssertionError, match=r"Expected coroutine function.*rule_greatest"):
        GoodEnough(get_sample, rules=[rule_greatest])


def test_clamped_coefs():

    async def rule_greatest_the_wrong(request, item):
        return item  # will get clamped inside 0..1, so in case of [1,2,3,4,5] will always be 1.

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_sample, rules=[rule_greatest_the_wrong])
    assert ge.pick({}) == 1  # and not 5


def test_request_in_rules():

    async def rule_close_to_request(request, item):  # request can be anything, it's a number in this example
        return 1 - abs(request - item)

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_sample, rules=[rule_close_to_request])
    assert ge.pick(request=2.8) == 3  # item 3 is the closest to 2.8


def test_request_in_get_sample():

    async def get_sample(request):
        return range(request["from"], request["to"])  # request can be anything, it's a dict in this example

    ge = GoodEnough(get_sample, rules=[])
    assert ge.pick(request={"from": 7, "to": 11}) == 7  # no rules -- return the first


def test_xxxxxxxxxxx():







    55/0



# updater
# never return items w 0 coef (or let define strategy: retry n times, raise, still return)
# rules weights
# silent clamp? shouldn't we complain / throw warning?
