# 限流器找 bug

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 调试 · Python | ★☆☆☆☆ | 中等 | SWE · Infra Eng | debugging, concurrency, sliding-window, testing | 4 个 bug | 现场面 |
<!-- meta:end -->

## 题目

下面这个类本该按三档规则限制每个用户的请求量。一条*规则*（rule）是一个 `(max_requests, period_seconds)`
二元组；当这个用户已经被放行的请求里，仍然计入这条规则的不足 `max_requests` 条时，本次请求就算满足这条
规则——一条在时刻 `t` 被放行的请求，只要 `now - t <= period_seconds` 就一直计入，超过之后不再计入。
只有三条规则同时满足，请求才会被放行；被放行的请求随即记入全部三条规则，被拒绝的请求一条也不记。
同一个用户的两次调用落在不同线程上时，结果必须和它们一前一后跑出来的结果一样。

`rate_limited` 是一个装饰器，用来代替某个 web 框架的中间件——它包住一个视图函数，请求被拒绝时直接返回一个
`429` 响应，不再调用视图本身。`clock` 是一个不带参数、返回当前时间（秒）的可调用对象，这样测试就能手动把
时间往前推，不必真的等墙上时钟。`_within_window` 在判断出结果之后、记录任何东西之前会调用一次
`checkpoint`；`checkpoint` 默认什么也不做，除非测试把它换掉，于是测试可以把好几个线程按在这个位置上。

```python
import time
from collections import defaultdict
from functools import wraps


class FakeClock:
    """A clock a test can move by hand instead of waiting on the wall clock."""

    def __init__(self, start: float = 1_700_000_000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class RateLimiter:
    """Three tiers per user: minute_rule, hour_rule and day_rule, each a
    (max_requests, period_seconds) pair."""

    def __init__(self, minute_rule, hour_rule, day_rule, clock=time.time, checkpoint=lambda: None):
        self.minute_rule = minute_rule
        self.hour_rule = hour_rule
        self.day_rule = day_rule
        self.clock = clock
        self.checkpoint = checkpoint
        self.recent = defaultdict(list)     # user_id -> timestamps
        self.day_count = defaultdict(int)   # user_id -> request count

    def _within_window(self, user_id, now, max_requests, period):
        timestamps = self.recent[user_id]
        while timestamps and now - timestamps[0] > period:
            timestamps = timestamps[1:]
        would_pass = len(timestamps) < max_requests
        self.checkpoint()
        if not would_pass:
            return False
        timestamps.append(now)
        return True

    def should_allow_request(self, user_id):
        now = self.clock()
        if not self._within_window(user_id, now, *self.minute_rule):
            return False
        if not self._within_window(user_id, now, *self.hour_rule):
            return False
        max_requests, _period = self.day_rule
        self.day_count[user_id] += 1
        return self.day_count[user_id] <= max_requests


def rate_limited(limiter):
    """Stands in for a web framework's middleware: returns a 429 instead of calling the view."""
    def decorator(view):
        @wraps(view)
        def wrapped(user_id, *args, **kwargs):
            if not limiter.should_allow_request(user_id):
                return {"status": 429, "body": {"error": "rate limit exceeded"}}
            return view(user_id, *args, **kwargs)
        return wrapped
    return decorator


limiter = RateLimiter(minute_rule=(5, 60), hour_rule=(20, 3600), day_rule=(50, 86400))


@rate_limited(limiter)
def post_message(user_id, text):
    return {"status": 200, "body": {"echo": text}}


def test_allows_requests_under_the_limit():
    responses = [post_message("alice", "hi") for _ in range(3)]
    assert all(r["status"] == 200 for r in responses)


test_allows_requests_under_the_limit()
```

### 找出并修复四个 bug

`RateLimiter` 的行为与上面的描述不符：它有四个 bug，全都在这个类里面。
`test_allows_requests_under_the_limit` 能通过，是因为三次请求根本没有接近任何一档规则的上限；
它说明不了这个限流器到底有没有在限流。找出每一个 bug，写一个能在上面这份代码上失败、修好之后能通过的
测试，并说明这个 bug 让限流器的行为出了什么问题、为什么。保留这个类对外的样子——构造函数的参数、
`should_allow_request` 和那个装饰器——而不是换成一个自己设计的限流器。假设一旦你宣布某个 bug 修好了，
就会有更多从别的角度探测它的测试用例接着到来。

## 参考解答

<details>
<summary>展开参考解答</summary>

先跑一遍这份 smoke test，确认给定的测试就只有这一个，然后在改动任何东西之前逐行读一遍 `_within_window`
和 `should_allow_request`——四个 bug 光看代码就能看出来，不需要真的运行任何东西。下面四个测试都不去等
真实时间，也不去等一次侥幸的线程交错：`FakeClock` 把时间变成一个可以手动往前推的数，`checkpoint` 把线程
按在“判断完了、还没记录”的那一刻。有了这两个钩子，每个测试每次运行都给出同一个答案，修好之后也就还值得
留在测试文件里。

### 四个 bug

每一行都是一个只用公开接口写出来的测试，所以同一个测试在修复前后都能跑。“给定的类”那一列，是原样运行
这个类测出来的。

| 测试 | 给定的类 | 指向 |
| --- | --- | --- |
| 每 60 秒 3 次：先打满，等窗口过期，再在同一瞬间发 10 次——最多只能过 3 次 | 10 次全过 | bug 1，淘汰逻辑 |
| 每天 5 次，现实中每隔一整天发一次，共 8 天——8 次都该过 | 过了 5 次，之后被拦住 | bug 2，每日计数器 |
| 每分钟 4 次加每小时 2 次，同一瞬间发 4 次——该过 2 次 | 只过了 1 次 | bug 3，共享的列表 |
| 每分钟 5 次，20 个线程都先判断完、谁都还没记录——最多只能过 5 次 | 20 个全过 | bug 4，没有加锁 |

没有哪一行会盖住另一行：每个测试失败都有它自己的原因。代码却不像表格这样能分开——bug 1 和 bug 3 是同样
那两行的两种读法，正因为“检查”和“记录”挤在同一个函数里，那次切片丢掉的才不只是淘汰，还有那次记录。

**Bug 1：`_within_window` 淘汰循环里的切片。** `timestamps` 一开始绑定的就是 `self.recent[user_id]`
存着的那个列表本身；对它切片，`timestamps[1:]`，会造出一个去掉了第一项的*新*列表，并把局部名字
`timestamps` 重新绑定到新列表上，而 `self.recent[user_id]` 仍然指向原来那个没被动过的列表。由此带来两件事。
一是存储里的记录无论过去多久都不会少一条，只会越积越多。二是只要循环至少切过一次，两行之后的
`timestamps.append(now)` 就落在那份私有副本上——于是一条有过期记录要清的规则干脆不再记录任何东西：
它一直拿一份“存储的副本”去判断，而存储从此不再变化，所以从第一次过期开始，它就放行一切。表格第一行
就是这样来的：上限 3 次，10 次请求全部通过。真正要改的是让做淘汰的这一行落到存储的那个对象上；时间戳装在
哪种容器里是另一个问题，选 `deque` 是为了淘汰的代价，不是为了淘汰的正确性。

```py
while window and now - window[0] > period:
    window.popleft()                   # NOTE: mutates the stored deque in place; a rebind would not
```

**Bug 2：`should_allow_request` 里的 `self.day_count[user_id] += 1`。** 没有任何地方会给 `day_count`
减量或者把它清零，所以它装的是这个用户有生以来被放行过的全部请求数：这个检查拿一个终身累计值去比固定上限，
而不是去数最近 `day_rule` 秒里发生了多少次。这样的检查只可能从“通过”变成“不通过”，不会再变回来。
表格第二行里的用户现实中每隔一整天才发一次，86,400 秒的窗口里从来不会同时有超过一条记录，可他从第 6 次
起还是被拦住了，两次请求之间隔多久都一样。每日这一档也得像另外两档那样存时间戳、按窗口来算。

```py
fits_day = self._fits(w["day"], now, *self.day_rule)  # NOTE: a window like the other two, not a total
```

**Bug 3：`self.recent[user_id]` 是两条带窗口的规则共用的一个列表，而 `_within_window` 一旦自己这条规则
通过，就立刻往里追加一条。** 在共享的存储上一条规则一条规则地“先检查、再记录”，错了两层。一次被放行的
请求被记了两次——分钟检查记一次，小时检查记一次——两条规则的额度都以差不多两倍的速度被耗掉。更糟的是第二层：
小时检查读这个列表的时候，分钟检查那次追加早已发生；如果小时检查接着拒绝了这次请求，那次追加也不会被撤销，
一次被拒的请求照样花掉了用户的额度。取 `minute_rule=(4, 60)`、`hour_rule=(2, 3600)`，就是表格第三行：
第一次请求被放行并且记了两次；第二次请求本该还能过——真正成功的只有一次，小时上限是 2——却被一个在这同一次
调用里刚被推到长度 2 的列表挡了回去。把一次调用拆成“判断阶段”和“记录阶段”，两层错一起就没了：每条规则
各有各的存储，一条规则的记录不再算到另一条头上；三条都点头之后才记录，被拒的请求也就什么都不会留下。

```py
fits_minute = self._fits(w["minute"], now, *self.minute_rule)
fits_hour = self._fits(w["hour"], now, *self.hour_rule)
fits_day = self._fits(w["day"], now, *self.day_rule)  # NOTE: a window like the other two, not a total
self.checkpoint()
if not (fits_minute and fits_hour and fits_day):      # NOTE: every rule decides before any records
    return False
w["minute"].append(now)
w["hour"].append(now)
w["day"].append(now)
```

**Bug 4：没有任何东西拦着两个线程同时进来。** 读出 `len(timestamps)`、做判断、再追加，是三个各自独立的
步骤，所以两个线程可以都在计数还没到上限时读到那个数，然后都被放行，而实际上只有一个名额。把 `checkpoint`
换成一个 `threading.Barrier`，这件事就从碰运气变成必然——20 个线程都判断完了，谁都还没记录——结果 20 个
全部通过，而上限是 5。修法是给整段“先检查、再记录”加一把锁，并且把读时钟也放进锁里：两个线程如果在拿锁
之前各自读时钟，记下的时间戳就可能前后颠倒，而淘汰循环永远只看窗口最前面那一条，颠倒进去的那一条就再也
清不掉了。并发的正确性没法靠“跑了一次刚好是对的”来说明，所以验证从两头来：把锁拿掉、用屏障把竞态逼出来，
证明这个测试确实会失败；再把锁装回去，几百个线程去抢同一个上限，放行数正好等于上限。

```py
with self._lock:                                      # NOTE: one lock over the check and the record
    now = self.clock()                                # NOTE: read inside the lock, so the recorded
    w = self.windows[user_id]                         #       timestamps come out non-decreasing
```

四个都修好之后，每条规则各有一个自己的时间戳双端队列，过期记录就从这个队列本身里清掉，三条规则全部判断完
才会有任何一条去记录，整个决定过程都在同一把锁里完成。

### 追问

- `deque` 的 `popleft()` 是 $O(1)$；同样的淘汰写在普通列表上，`del timestamps[:i]`，代价是 $O(n)$，
  n 是留下来的那些记录条数，因为它们都要整体往前挪。
- 把三条规则的检查都放在一把锁里，会让所有用户的所有请求互相串行，不只是同一个用户的；按用户（或者按用户
  分片）各自加一把锁，能让不相关用户的请求并发通过。
- 墙上时钟被校正时 `time.time` 可能往回跳，那会让窗口里的时间戳失去顺序，效果和在锁外读时钟一样；
  限流器只关心流逝的时间，用 `time.monotonic` 作默认更稳妥。
- 没有任何地方会把用户从 `self.windows` 里删掉，它会随着见过的不同用户数一直涨；一个用户三个队列都空了
  之后这一项就可以删掉，但那需要再加一趟清扫或者一个 LRU。
- 分布式部署下，这份状态根本不能只放在一个进程的内存里：通常的做法是把滑动窗口挪进 Redis 之类的存储，并把
  “检查并记录”这一步做成单个原子脚本，因为两台应用服务器，不过是又多了两个在抢同一个 bug 的线程。

<details>
<summary>给定的类原样运行的结果、修复后的完整文件与验证代码（可运行）</summary>

```python
# ---- the four tests of the table, run here against the class exactly as given ----
import contextlib
import threading


def run_threads(limiter, user_id, count):    # one call per thread; the main thread does the asserting
    results = [None] * count

    def race(i):
        results[i] = limiter.should_allow_request(user_id)

    workers = [threading.Thread(target=race, args=(i,), daemon=True) for i in range(count)]
    for t in workers:
        t.start()
    for t in workers:
        t.join(timeout=15)
    assert all(r is not None for r in results)          # no thread died or timed out
    return sum(1 for r in results if r)


def admitted_after_the_window_rolls(cls):               # row 1: three rules, all of period 60
    clock = FakeClock()
    limiter = cls((3, 60), (10_000, 60), (10_000, 60), clock=clock)
    for _ in range(3):
        limiter.should_allow_request("ana")
    clock.advance(61)
    return sum(1 for _ in range(10) if limiter.should_allow_request("ana"))


def admitted_one_request_a_day(cls):                    # row 2: never more than 1 deep in the day window
    clock = FakeClock()
    limiter = cls((10_000, 60), (10_000, 3600), (5, 86_400), clock=clock)
    admitted = 0
    for _ in range(8):
        admitted += limiter.should_allow_request("bruno")
        clock.advance(86_401)
    return admitted


def admitted_under_the_hour_rule(cls):                  # row 3: the hour rule binds before the minute one
    limiter = cls((4, 60), (2, 3600), (10_000, 86_400), clock=FakeClock())
    return sum(1 for _ in range(4) if limiter.should_allow_request("chidi"))


def admitted_by_racing_threads(cls, count=20):          # row 4: all of them decide before any records
    limiter = cls((5, 60), (10_000, 3600), (10_000, 86_400), clock=FakeClock(),
                  checkpoint=threading.Barrier(count, timeout=10).wait)
    return run_threads(limiter, "dora", count)


as_given = {
    "eviction": admitted_after_the_window_rolls(RateLimiter),
    "daily quota": admitted_one_request_a_day(RateLimiter),
    "shared list": admitted_under_the_hour_rule(RateLimiter),
    "racing threads": admitted_by_racing_threads(RateLimiter),
}
assert as_given == {"eviction": 10, "daily quota": 5, "shared list": 1, "racing threads": 20}, as_given
```

```python
import time
import threading
from collections import defaultdict, deque
from functools import wraps


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class RateLimiter:
    def __init__(self, minute_rule, hour_rule, day_rule, clock=time.time, checkpoint=lambda: None):
        self.minute_rule = minute_rule
        self.hour_rule = hour_rule
        self.day_rule = day_rule
        self.clock = clock
        self.checkpoint = checkpoint
        self.windows = defaultdict(lambda: {"minute": deque(), "hour": deque(), "day": deque()})
        self._lock = threading.Lock()

    def _fits(self, window, now, max_requests, period):
        while window and now - window[0] > period:
            window.popleft()                   # NOTE: mutates the stored deque in place; a rebind would not
        return len(window) < max_requests   # NOTE: strict; this request is not in the window yet

    def should_allow_request(self, user_id):
        with self._lock:                                      # NOTE: one lock over the check and the record
            now = self.clock()                                # NOTE: read inside the lock, so the recorded
            w = self.windows[user_id]                         #       timestamps come out non-decreasing
            fits_minute = self._fits(w["minute"], now, *self.minute_rule)
            fits_hour = self._fits(w["hour"], now, *self.hour_rule)
            fits_day = self._fits(w["day"], now, *self.day_rule)  # NOTE: a window like the other two, not a total
            self.checkpoint()
            if not (fits_minute and fits_hour and fits_day):      # NOTE: every rule decides before any records
                return False
            w["minute"].append(now)
            w["hour"].append(now)
            w["day"].append(now)
            return True


def rate_limited(limiter):
    def decorator(view):
        @wraps(view)
        def wrapped(user_id, *args, **kwargs):
            if not limiter.should_allow_request(user_id):
                return {"status": 429, "body": {"error": "rate limit exceeded"}}
            return view(user_id, *args, **kwargs)
        return wrapped
    return decorator


if __name__ == "__main__":
    limiter = RateLimiter(minute_rule=(5, 60), hour_rule=(20, 3600), day_rule=(50, 86400))

    @rate_limited(limiter)
    def post_message(user_id, text):
        return {"status": 200, "body": {"echo": text}}

    for _ in range(3):
        assert post_message("alice", "hi")["status"] == 200
    print("smoke test passed")
```

```python
from collections import Counter
import random

# ---- the same three single-threaded tests, now against the fixed class ----
assert admitted_after_the_window_rolls(RateLimiter) == 3 < as_given["eviction"]
assert admitted_one_request_a_day(RateLimiter) == 8 > as_given["daily quota"]
assert admitted_under_the_hour_rule(RateLimiter) == 2 > as_given["shared list"]

decorated = RateLimiter((2, 60), (10_000, 3600), (10_000, 86_400), clock=FakeClock())


@rate_limited(decorated)
def echo_message(user_id, text):
    return {"status": 200, "body": {"echo": text}}


assert [echo_message("ana", "hi")["status"] for _ in range(3)] == [200, 200, 429]
assert echo_message("ana", "hi")["body"] == {"error": "rate limit exceeded"}


# ---- cross-check against an independent reading of the rules: keep every admitted timestamp and
#      count by scanning, with no eviction and no per-rule bookkeeping at all ----
class NaiveLimiter:
    def __init__(self, rules, clock):
        self.rules = list(rules)
        self.clock = clock
        self.admitted = defaultdict(list)

    def should_allow_request(self, user_id):
        now = self.clock()
        times = self.admitted[user_id]
        for max_requests, period in self.rules:
            if sum(1 for t in times if now - t <= period) >= max_requests:
                return False
        times.append(now)
        return True


RULES = [(2, 3), (3, 10), (5, 30)]         # tiny caps and periods, so every rule binds often
rng = random.Random(4)
coverage = Counter()
for _ in range(400):                       # a fresh pair of limiters per episode keeps the scan cheap
    clock, naive_clock = FakeClock(), FakeClock()
    lim = RateLimiter(*RULES, clock=clock)
    naive = NaiveLimiter(RULES, naive_clock)
    for _ in range(60):
        user = rng.choice(["ana", "bruno"])
        step = rng.choice([0, 0, 1, 3, 10, 30])    # 3, 10 and 30 land exactly on a period boundary
        clock.advance(step)
        naive_clock.advance(step)
        now = clock()
        if any(now - t == period for t in naive.admitted[user] for _, period in RULES):
            coverage["exactly on a boundary"] += 1
        before = sum(len(w) for w in lim.windows[user].values())
        got, want = lim.should_allow_request(user), naive.should_allow_request(user)
        assert got == want, (user, now, got, want)
        coverage["admitted" if got else "rejected"] += 1
        if sum(len(w) for w in lim.windows[user].values()) < before + 3 * got:
            coverage["entries evicted"] += 1
assert all(coverage[k] > 200 for k in
           ("admitted", "rejected", "entries evicted", "exactly on a boundary")), coverage


# ---- bug 4: forced over-admission without the lock, exact caps with it ----
unlocked = RateLimiter((5, 60), (10_000, 3600), (10_000, 86_400), clock=FakeClock(),
                       checkpoint=threading.Barrier(20, timeout=10).wait)
unlocked._lock = contextlib.nullcontext()  # negative control: the fixed class with its lock taken away
unlocked.windows["petra"]                  # created up front, so only should_allow_request races
assert run_threads(unlocked, "petra", 20) == 20         # all 20 admitted against a cap of 5

# the same barrier would deadlock against a real lock, so the locked runs force a thread switch
# between deciding and recording instead
locked = RateLimiter((5, 60), (10_000, 3600), (10_000, 86_400), clock=FakeClock(),
                     checkpoint=lambda: time.sleep(0))
assert run_threads(locked, "petra", 200) == 5
assert [len(locked.windows["petra"][k]) for k in ("minute", "hour", "day")] == [5, 5, 5]

# several users filling several rules at once: per user 3 by the minute rule, 2 more by the hour rule,
# none while the hour window is still full, then 1 more up to the daily cap
USERS = ["ana", "bruno", "chidi", "dora"]
clock = FakeClock()
tiers = RateLimiter((3, 60), (5, 3600), (6, 86_400), clock=clock, checkpoint=lambda: time.sleep(0))
admitted, running = Counter(), 0
for advance, expected in [(0, 3), (61, 2), (61, 0), (3601, 1)]:
    clock.advance(advance)
    running += expected
    for user in USERS:
        admitted[user] += run_threads(tiers, user, 8)
    assert all(admitted[u] == running for u in USERS), (running, admitted)
assert running == 6
for user in USERS:                                   # the eviction loop only looks at the head, so the
    for window in tiers.windows[user].values():      # recorded timestamps have to be non-decreasing
        assert list(window) == sorted(window)


class _LockHeldClock:
    """Readable only while the limiter holds its lock -- no thread race needed to catch a read
    taken before it."""

    def __init__(self, limiter):
        self.limiter = limiter

    def __call__(self):
        assert self.limiter._lock.locked(), "the clock was read outside the lock"
        return 1_700_000_000.0


watched = RateLimiter((5, 60), (20, 3600), (50, 86_400))
watched.clock = _LockHeldClock(watched)
assert watched.should_allow_request("petra") is True

# and why the order matters: a window whose head is newer than its tail keeps the stale entry forever
out_of_order = deque([1_700_000_100.0, 1_700_000_000.0])
assert watched._fits(out_of_order, 1_700_000_100.0, 10, 60) is True
assert list(out_of_order) == [1_700_000_100.0, 1_700_000_000.0]   # 100 seconds stale and still there

print("all checks passed")
```

</details>

</details>
