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
        return item  # will get clamped inside 0..1, so in this case will always be 1.

    async def get_sample(request):
        return [1, 2, 3, 4, 5]

    ge = GoodEnough(get_sample, rules=[rule_greatest_the_wrong])
    assert ge.pick({}) == 1  # and not 5


def test_xxxxxxxxx():

    55/0



# request
# updater
# never return items w 0 coef (or let define strategy: retry n times, raise, still return)
# rules weights
