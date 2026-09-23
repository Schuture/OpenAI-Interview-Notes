# Rate Limiter Bug Hunt

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Debugging · Python | ★☆☆☆☆ | Medium | SWE · Infra Eng | debugging, concurrency, sliding-window, testing | 4 bugs | Onsite |
<!-- meta:end -->

## Problem

The class below is meant to enforce per-user request limits under three tiers. A *rule* is a
`(max_requests, period_seconds)` pair, and a request fits under a rule when fewer than `max_requests` of
that user's already-admitted requests still count against it: an admitted request made at time `t`
counts while `now - t <= period_seconds` and stops counting after that. A request is admitted only when
it fits under all three rules at once; an admitted request is then recorded against all three rules, and
a rejected request is recorded against none. Two calls for the same user running on different threads
must come out the same as if one had run after the other.

`rate_limited` is a decorator standing in for a web framework's middleware — it wraps a view function
and turns a rejected request into a `429` response instead of calling the view. `clock` is a
zero-argument callable returning the current time in seconds, so a test can move time forward by hand
instead of waiting on the wall clock. `_within_window` calls `checkpoint` once it has decided and before
it records anything; `checkpoint` does nothing unless a test replaces it, so a test can hold several
threads at that exact point.

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

### Find and fix the four bugs

`RateLimiter` does not behave as described above: it has four bugs, all of them inside the class itself.
`test_allows_requests_under_the_limit` passes because three requests never get close to any of the three
caps; it says nothing about whether the limiter limits anything. Find each bug, write a test that fails
against the class above and passes once the bug is fixed, and say what the bug does to the limiter's
behaviour and why. Keep the class's surface — the constructor arguments, `should_allow_request` and the
decorator — rather than replacing it with a limiter of your own design. Assume that once you claim a bug
is fixed, more test cases will keep arriving that probe it from another angle.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Run the smoke test first and confirm it is the only test given, then read `_within_window` and
`should_allow_request` line by line before changing anything — every one of the four bugs is visible
from the code alone, without running anything. None of the tests below waits on real time or on a lucky
interleaving: `FakeClock` turns time into a number a test moves by hand, and `checkpoint` holds threads
at the instant after they have decided and before they record. Both hooks make each test give the same
answer on every run, which is what makes it worth keeping once the bug is fixed.

### The four bugs

Each row is one test written against the public API, so the same test can be run before and after the
fix. The measured column comes from running the class exactly as given.

| Test | The class as given | Points to |
| --- | --- | --- |
| cap of 3 per 60 s: fill it, let the window expire, then send 10 at one instant — at most 3 may pass | all 10 pass | bug 1, eviction |
| cap of 5 per day, one request a real day apart for 8 days — all 8 may pass | 5 pass, then blocked | bug 2, the daily counter |
| caps of 4 per minute and 2 per hour, 4 requests at one instant — 2 may pass | 1 passes | bug 3, the shared list |
| cap of 5 per minute, 20 threads all made to decide before any of them records — at most 5 may pass | all 20 pass | bug 4, no lock |

No row masks another: each test fails for its own reason. The code, though, is not as separable as the
table — bugs 1 and 3 are two readings of the same two lines, and it is only because the check and the
record sit in one function that the slice loses the record as well as the eviction.

**Bug 1: the slice in `_within_window`'s eviction loop.** `timestamps` starts out bound to the very list
stored in `self.recent[user_id]`; slicing it, `timestamps[1:]`, builds a *new* list with the first entry
gone and rebinds the local name to it, leaving `self.recent[user_id]` pointing at the original,
untouched list. Two things follow. The stored list never loses an entry, however much time passes, so it
only ever grows. And the `timestamps.append(now)` two lines down lands on the private copy whenever the
loop ran at least once, so a rule that has expired entries to prune stops recording altogether: it keeps
deciding against a copy of a stored list that no longer changes, and from the first expiry onwards it
admits everything. That is the first row of the table — ten requests through a cap of three. The line
that prunes has to reach the stored object; which container holds the timestamps is a separate
question, and a `deque` is chosen for the cost of the eviction, not for its correctness.

```py
while window and now - window[0] > period:
    window.popleft()                   # NOTE: mutates the stored deque in place; a rebind would not
```

**Bug 2: `self.day_count[user_id] += 1` in `should_allow_request`.** Nothing ever subtracts from
`day_count` or resets it, so it holds every request the user has ever had admitted: the check compares a
lifetime total against a fixed cap instead of counting the requests made in the last `day_rule` seconds.
A check like that can only ever go from passing to failing, never back. The user in the second row sends
one request a real day apart, is never more than one deep inside the 86,400-second window, and is still
blocked from the sixth request on, whatever the gap between requests. The day rule needs timestamps and
a window like the other two.

```py
fits_day = self._fits(w["day"], now, *self.day_rule)  # NOTE: a window like the other two, not a total
```

**Bug 3: `self.recent[user_id]` is one list for both windowed rules, and each call to `_within_window`
appends to it the moment its own rule passes.** Checking and recording one rule at a time on shared
storage goes wrong twice over. A single admitted request is recorded twice — once by the minute check,
once by the hour check — so both rules run out about twice as fast as their numbers promise. Worse, the
minute check's append has already happened by the time the hour check reads the list; if the hour check
then rejects, that append is never undone, and a request that was refused has still cost the user
budget. With `minute_rule=(4, 60)` and `hour_rule=(2, 3600)` that is the third row: the first request is
admitted and recorded twice, and the second — which should still fit, one real success so far against an
hourly cap of 2 — is rejected by a list this same call had already pushed to length 2. Splitting the call
into a decide phase and a record phase is what fixes both halves at once: per-rule storage stops one
rule's record from counting against another, and recording only after all three have said yes means a
rejected request leaves nothing behind.

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

**Bug 4: nothing keeps two threads out of each other's way.** Reading `len(timestamps)`, deciding, and
appending are three separate steps, so two threads can both read a count under the cap before either one
appends, and both are admitted where there was room for one. Replacing `checkpoint` with a
`threading.Barrier` makes that certain instead of lucky — all 20 threads finish deciding before any of
them records — and all 20 are admitted against a cap of 5. One lock around the whole check-then-record
is the fix, and the clock is read inside it as well: two threads reading the clock before taking the
lock can record their timestamps in the wrong order, and since the eviction loop only ever looks at the
head of the window, an entry that lands out of order is never removed. Concurrency cannot be argued from
one run that happened to come out right, so the checks do it from both ends: with the lock taken away and
the barrier in place, the over-admission is forced and the test is shown to be able to fail; with the
lock back, a few hundred threads against the same cap admit exactly the cap.

```py
with self._lock:                                      # NOTE: one lock over the check and the record
    now = self.clock()                                # NOTE: read inside the lock, so the recorded
    w = self.windows[user_id]                         #       timestamps come out non-decreasing
```

With all four fixed, each rule keeps its own deque of timestamps, expiry is pruned from that deque
itself, all three rules decide before any of them records, and the whole decision happens under one
lock.

### Follow-ups

- `popleft()` on a `deque` is $O(1)$; the same eviction written on a plain list, `del timestamps[:i]`,
  costs $O(n)$ in the number of entries that survive it, because they all shift down.
- Holding the lock for all three rule checks serializes every request from every user, not just from one
  user; a lock per user (or per shard of users) would let unrelated users' requests through
  concurrently.
- `time.time` can jump backwards when the wall clock is corrected, which leaves a window's timestamps
  out of order exactly the way an unlocked clock read does; `time.monotonic` is the safer default for a
  limiter that only ever measures elapsed time.
- Nothing removes a user from `self.windows`, so it grows with the number of distinct users ever seen; an
  entry can be dropped once all three of that user's deques are empty, which needs a sweep or an LRU on top.
- A distributed deployment cannot keep this state in one process's memory at all: the usual fix is
  moving the sliding window into a store like Redis and making the check-and-record step a single
  atomic script, since two application servers are exactly two more threads racing the same bug.

<details>
<summary>What the class as given does, the complete file after the four fixes, and the checks (runnable)</summary>

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
