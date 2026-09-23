# Binary Search with Delayed Answers

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE · RE | binary-search, interaction, algorithm-design | 3 parts | Phone screen |
<!-- meta:end -->

## Problem

### Part 1 — One secret, one guess per call

There is a hidden integer `secret` in the closed interval `[1, n]`. The only way to learn anything
about it is `check(x)`, whose answer is delayed by exactly one call:

- `x` must lie in `[1, n]` and must never repeat a value passed to an earlier `check` call in this
  game.
- The very first call to `check` returns `None` — there is no earlier guess yet to compare.
- Every call after that returns the comparison of the **previous** call's argument against
  `secret`: `-1` if that previous `x` was less than `secret`, `0` if it was equal, `1` if it was
  greater. The comparison for the `x` you are passing *right now* only comes back on the *next*
  call.
- As soon as the comparisons revealed so far leave a single possible `secret`, `check` must not be
  called again; with `n = 1` that is already the case before the first call.
- Because of the delay, there is always at most one call whose comparison you have not yet seen.
  You may spend one further call — with any `x` in `[1, n]` that has not been used yet — purely to
  retrieve it.

```py
def check(x: int) -> int | None:
    """Provided. x must lie in [1, n] and must not repeat an earlier call's x in this game.
    Returns None on the very first call. On every later call, returns -1, 0, or 1: the
    comparison of the PREVIOUS call's argument against the hidden secret, never of x itself."""

def find_secret(n: int, check) -> int:
    """Returns secret, calling check at most 2 * ceil(log2(n)) + 1 times."""
```

For example, with `n = 7` and `secret = 5`:

```text
check(3) -> None    # no earlier guess to compare yet
check(6) -> -1      # compares 3 to secret: 3 < 5
check(4) -> 1       # compares 6 to secret: 6 > 5, so secret is in {4, 5}
check(7) -> -1      # compares 4 to secret: 4 < 5, so secret = 5
```

At this point `secret = 5` is already the only possibility, so calling `check` again (with `2`, or
any other unused number) would be rejected.

### Part 2 — Two guesses per call, same secret

`check_batch` replaces `check` with the same one-call delay, now applied to a whole list at once:

- Every `x` used across every call in the game — in any batch — must be distinct and lie in
  `[1, n]`, and every call must carry at least one guess.
- The first call returns `None`.
- Every later call returns a list the same length as the **previous** call's list, holding the
  comparison of each of those `x`'s against `secret`, in the same order.
- The same "one more call to retrieve the last batch" allowance and the same "stop once `secret`
  is determined" rule apply.

```py
def check_batch(xs: list[int]) -> list[int] | None:
    """Provided. Every x used across every call in the game must be distinct and lie in [1, n],
    and xs must be non-empty. Returns None on the first call. On every later call, returns a list
    the same length as the PREVIOUS call's xs, comparing each of those guesses to secret (same
    -1/0/1 sense as check), in the same order."""

def find_secret_batched(n: int, check_batch) -> int:
    """Returns secret, calling check_batch at most 2 * ceil(log(n, 3)) + 1 times."""
```

For example, with `n = 13` and `secret = 9`:

```text
check_batch([4, 10]) -> None       # no earlier batch to compare yet
check_batch([2])     -> [-1, 1]    # compares 4, then 10, to secret: 4 < 9, 10 > 9
```

### Part 3 — Many independent games, minimize the number of rounds

There are several independent games running behind the *same* channel, each identified by a game
id, each with its own bound `n[g]` and its own hidden `secret[g]`. Each round you submit a dict
mapping some subset of the ids — possibly none of them — to one guess for that game; `check_round`
answers by echoing back the **previous round's whole submission**, comparison by comparison —
regardless of which ids the current round itself contains:

- Within one game id, every guess ever submitted for it must be distinct and lie in `[1, n[g]]`.
- The first round returns `None`.
- Every later round returns a dict with exactly the keys that were submitted in the **previous**
  round, each mapped to the comparison of that guess against its own game's secret.
- A game id must not be guessed again once its own secret is already determined.
- What is to be minimized now is the total number of rounds (calls to `check_round`), not the
  total number of individual guesses.

```py
def check_round(guesses: dict[str, int]) -> dict[str, int] | None:
    """Provided. guesses maps a subset of game ids to one guess each, guesses[g] in [1, n[g]];
    within one id, guesses must never repeat. Returns None on the first call. On every later
    call, returns a dict with exactly the keys submitted in the PREVIOUS call, each mapped to the
    -1/0/1 comparison of that guess against ITS OWN game's secret -- independent of which ids the
    CURRENT call itself contains."""

def solve_games(bounds: dict[str, int], check_round) -> dict[str, int]:
    """Returns every game's secret. Calls check_round at most
    2 * ceil(log2(max(bounds.values()))) + 1 times, regardless of how many games there are."""
```

For example, with games `"A"` (`n = 5`, `secret = 4`) and `"B"` (`n = 20`, `secret = 15`):

```text
check_round({"A": 2, "B": 8}) -> None                 # no earlier round to compare yet
check_round({})               -> {"A": -1, "B": -1}   # echoes round 1's guesses, though this round asks nothing new
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming first: this assumes `check` (and its batched and multi-game variants) must be
called strictly one at a time. If the real system instead lets several requests fly concurrently,
the delay disappears and plain binary search is enough.

### Part 1

Because the argument passed to call $i$ is fixed before call $i$'s own return value exists, you
never know the comparison for the guess you *just* made — only for the one before it. The sequence
of calls therefore has to alternate two roles: a *real* probe, the midpoint of the current
`[lo, hi]`, and a *filler*, whose only job is to make the next call happen so the real probe's
comparison comes back. Whichever value the filler takes becomes the *next* pending guess, so
its own comparison is processed on equal footing with a real probe's. The very first filler has no
choice but to land inside `[lo, hi]`, since nothing has been ruled out yet; later ones go to the
untouched ends of `[1, n]`, where the answer is already known. Either way the loop narrows on
whatever comes back and needs no special case.

```python
def find_secret(n, check):
    if n == 1:
        return 1                        # only one candidate: nothing to compare
    lo, hi = 1, n
    used = set()
    right_scan, left_scan = n, 1        # frontiers for filler values outside [lo, hi]

    def real_probe():
        mid = (lo + hi) // 2
        for delta in range(hi - lo + 1):           # NOTE: nudge off mid if a stray filler already used it
            for cand in (mid - delta, mid + delta):
                if lo <= cand <= hi and cand not in used:
                    return cand

    def filler():
        nonlocal right_scan, left_scan
        while right_scan > hi:                       # values above hi are provably irrelevant
            cand, right_scan = right_scan, right_scan - 1
            if cand not in used:
                return cand
        while left_scan < lo:                        # then values below lo
            cand, left_scan = left_scan, left_scan + 1
            if cand not in used:
                return cand
        for x in range(lo, hi + 1):      # NOTE: the first filler always lands here (nothing is
            if x not in used:            # outside [lo, hi] yet), and so do fillers once [1, n] runs dry
                return x

    pending = real_probe()
    used.add(pending)
    check(pending)
    is_real = True                      # role of `pending`: was it this round's bisection probe?

    while True:
        if lo == hi:
            return lo
        nxt = filler() if is_real else real_probe()
        used.add(nxt)
        r = check(nxt)
        # NOTE: narrow on ANY revealed comparison, real or filler -- a filler forced inside
        # [lo, hi] (only for tiny n) is still honest information about secret.
        if r == 0:
            return pending
        elif r == -1:
            lo = max(lo, pending + 1)
        elif r == 1:
            hi = min(hi, pending - 1)
        pending = nxt
        is_real = not is_real
        if lo == hi:
            return lo
```

Real probes land on calls $1, 3, 5, \dots$ and each is revealed by the filler right after it, on
calls $2, 4, 6, \dots$. So after $2k$ calls, exactly $k$ real probes have been revealed, and each
one either finds `secret` exactly or halves `[lo, hi]`; $k = \lceil \log_2 n \rceil$ of them
therefore leave at most one candidate, which fits in $2\lceil \log_2 n \rceil$ calls. A probe
nudged off the midpoint because a filler already took that value cuts a little less, so the checks
below measure the count directly — every secret for every $n$ below 400, then 54 sizes up to
$10^9$ — and it never exceeds $2\lceil \log_2 n \rceil$: the call the signature allows for
retrieving a pending comparison is never spent.

### Part 2

The same alternation works with a batch of two: submitting the two points that cut `[lo, hi]`
into thirds, `lo + (hi - lo)//3` and `lo + 2*(hi - lo)//3`, and reading their comparisons back one
round later narrows to whichever third contains `secret`, instead of whichever half. Once at most
two candidates are left a single probe already settles them, so a real round there submits one
point — exactly Part 1's bisection — which is also what keeps a value free for the next filler
when `n` itself is as small as 2.

```python
def find_secret_batched(n, check_batch):
    if n == 1:
        return 1
    lo, hi = 1, n
    used = set()
    right_scan, left_scan = n, 1

    def nudge(target, avoid):
        for delta in range(hi - lo + 1):
            for cand in (target - delta, target + delta):
                if lo <= cand <= hi and cand not in used and cand not in avoid:
                    return cand
        return None

    def real_points():
        if hi - lo + 1 <= 2:                  # NOTE: one point already settles two candidates,
            p = nudge((lo + hi) // 2, set())  # and for tiny n it leaves the filler a value to use
            return [p] if p is not None else []
        t1, t2 = lo + (hi - lo) // 3, lo + 2 * (hi - lo) // 3
        p1 = nudge(t1, set())
        p2 = nudge(t2, {p1} if p1 is not None else set())
        return [p for p in (p1, p2) if p is not None]

    def filler():
        nonlocal right_scan, left_scan
        while right_scan > hi:
            cand, right_scan = right_scan, right_scan - 1
            if cand not in used:
                return cand
        while left_scan < lo:
            cand, left_scan = left_scan, left_scan + 1
            if cand not in used:
                return cand
        for x in range(lo, hi + 1):
            if x not in used:
                return x

    def apply(xs, rs):
        nonlocal lo, hi
        found = None
        for x, r in zip(xs, rs):
            if r == -1: lo = max(lo, x + 1)
            elif r == 1: hi = min(hi, x - 1)
            else: found = x
        return found

    pending = real_points()
    used.update(pending)
    check_batch(pending)
    is_real = True

    while True:
        if lo == hi:
            return lo
        nxt = [filler()] if is_real else real_points()
        used.update(nxt)
        rs = check_batch(nxt)
        found = apply(pending, rs)
        if found is not None:
            return found
        pending = nxt
        is_real = not is_real
        if lo == hi:
            return lo
```

The same accounting applies with 3 in place of 2: $k = \lceil \log_3 n \rceil$ revealed real
rounds always leave at most one candidate, so at most $2\lceil \log_3 n \rceil$ calls. Since
$\lceil \log_3 n \rceil \le \lceil \log_2 n \rceil$ for every $n$, this never loses to Part 1, and
the two pull apart by the factor $\log_2 3 \approx 1.58$ as $n$ grows: at $n = 10^9$ the checks
below measure 38 calls against Part 1's 58.

### Part 3

With several games sharing the channel, a round no longer needs an artificial filler value at
all: submit every still-unsolved game's own midpoint in one round, then submit nothing (an empty
dict) the round after, purely to let that round's comparisons come back. Every game rides the same
two-round rhythm and drops out of the dict the moment its own `[lo, hi]` collapses, so the number
of rounds is fixed only by whichever game needs the most halvings -- exactly Part 1's bound
applied to the largest `n[g]`; every smaller game finishes for free along the way.

```python
def solve_games(bounds, check_round):
    lo = {g: 1 for g in bounds}
    hi = dict(bounds)
    solved = {g: lo[g] == hi[g] for g in bounds}     # n[g] == 1: nothing to ask

    def apply(batch, results):
        if not results:
            return
        for g, r in results.items():
            x = batch[g]
            if r == -1: lo[g] = max(lo[g], x + 1)
            elif r == 1: hi[g] = min(hi[g], x - 1)
            else: lo[g] = hi[g] = x
            solved[g] = lo[g] == hi[g]

    pending, is_real = {}, True
    while not all(solved.values()):
        # NOTE: recomputed fresh every real round, so a game that just finished simply drops out
        guesses = {g: (lo[g] + hi[g]) // 2 for g in bounds if not solved[g]} if is_real else {}
        results = check_round(guesses)
        apply(pending, results)
        pending, is_real = guesses, not is_real
    return {g: lo[g] for g in bounds}
```

Let $k = \lceil \log_2(\max_g n[g]) \rceil$. The largest game alone costs Part 1's $2k$ calls, and
`solve_games` spends exactly those $2k$ rounds however many games ride along. No protocol can beat
$\lceil \log_2(n + 1) \rceil$ rounds on a game of size $n$: after $r$ rounds at most $r - 1$ of its
comparisons have come back, and $c$ three-way comparisons separate at most $2^{c+1} - 1$ values, so
$n \le 2^r - 1$. The checks below put numbers on both ends: 30 games with $n$ up to $10^9$ finish
together in 58 rounds against that floor of 30, versus 1694 calls solving them one at a time.

### Follow-ups

- If `check` can be called concurrently (several requests in flight before any reply), the delay
  disappears and plain binary search suffices in $\lceil \log_2 n \rceil$ calls.
- Part 2's idea generalizes to $b - 1$ points per round, cutting `[lo, hi]` by a factor of $b$ per
  revealed round; push $b$ too far and the batch size itself, not the round count, becomes the
  bottleneck.
- A Fibonacci/golden-ratio strategy can in principle approach $1.44 \log_2 n$ calls for Part 1 by
  letting a probe's role depend on a ratio of consecutive Fibonacci numbers instead of the exact
  midpoint; constructing and proving it correct under this exact delay is considerably more
  involved than the bound above.
- Part 3's lockstep round can also submit Part 2's ternary points per game instead of a single
  midpoint, combining both speedups into about $2\lceil \log_3(\max_g n[g]) \rceil$ rounds.
- A network failure that silently drops one call has no signal in this protocol; the two-role
  alternation would need a sequence number or a timeout-and-retry rule bolted onto `check`.

<details>
<summary>Checks (runnable)</summary>

```python
import random
import time


def ceil_log(n, base):
    """ceil(log_base(n)) by integer arithmetic -- math.log(n, 3) can round the wrong way."""
    k, v = 0, 1
    while v < n:
        v, k = v * base, k + 1
    return k


def cmp3(x, secret):
    """The judges' three-way comparison: -1 below the secret, 0 on it, 1 above."""
    return -1 if x < secret else (1 if x > secret else 0)


def expect_rejected(call, *args):
    try:
        call(*args)
    except ValueError:
        return
    raise AssertionError("the judge accepted a call it should have rejected")


class Judge:
    """Strictly enforces Part 1's protocol against the real secret."""
    def __init__(self, n, secret):
        self.n, self.secret = n, secret
        self.used, self.pending = set(), None
        self.lo, self.hi, self.calls = 1, n, 0

    def check(self, x):
        if not (1 <= x <= self.n):
            raise ValueError(f"guess {x} out of bounds [1,{self.n}]")
        if x in self.used:
            raise ValueError(f"guess {x} repeats a previous guess")
        if self.lo == self.hi:
            raise ValueError("secret is already determined; no further guesses allowed")
        self.calls += 1
        self.used.add(x)
        result = None if self.pending is None else cmp3(self.pending, self.secret)
        if result == -1: self.lo = max(self.lo, self.pending + 1)
        elif result == 1: self.hi = min(self.hi, self.pending - 1)
        elif result == 0: self.lo = self.hi = self.pending
        self.pending = x
        return result


class BatchJudge:
    """Strictly enforces Part 2's protocol against the real secret, recording every batch size."""
    def __init__(self, n, secret):
        self.n, self.secret = n, secret
        self.used, self.pending, self.sizes = set(), None, []
        self.lo, self.hi, self.calls = 1, n, 0

    def check_batch(self, xs):
        xs = list(xs)
        if not xs:
            raise ValueError("a batch must contain at least one guess")
        seen = set()
        for x in xs:
            if not (1 <= x <= self.n):
                raise ValueError(f"guess {x} out of bounds [1,{self.n}]")
            if x in self.used or x in seen:
                raise ValueError(f"guess {x} repeats a previous guess")
            seen.add(x)
        if self.lo == self.hi:
            raise ValueError("secret is already determined; no further guesses allowed")
        self.calls += 1
        self.sizes.append(len(xs))
        self.used |= seen
        if self.pending is None:
            result = None
        else:
            result = []
            for x in self.pending:
                r = cmp3(x, self.secret)
                result.append(r)
                if r == -1: self.lo = max(self.lo, x + 1)
                elif r == 1: self.hi = min(self.hi, x - 1)
                else: self.lo = self.hi = x
        self.pending = xs
        return result


class GamesJudge:
    """Strictly enforces Part 3's protocol against the real per-game secrets."""
    def __init__(self, bounds, secrets):
        self.n, self.secret = dict(bounds), dict(secrets)
        self.used = {g: set() for g in bounds}
        self.lo = {g: 1 for g in bounds}
        self.hi = dict(bounds)
        self.pending, self.calls = None, 0

    def check_round(self, guesses):
        for g, x in guesses.items():
            if g not in self.n:
                raise ValueError(f"unknown game {g!r}")
            if not (1 <= x <= self.n[g]):
                raise ValueError(f"guess {x} out of bounds for game {g!r}")
            if x in self.used[g]:
                raise ValueError(f"guess {x} repeats a previous guess in game {g!r}")
            if self.lo[g] == self.hi[g]:
                raise ValueError(f"game {g!r} is already solved")
        self.calls += 1
        for g, x in guesses.items():
            self.used[g].add(x)
        if self.pending is None:
            result = None
        else:
            result = {}
            for g, x in self.pending.items():
                r = cmp3(x, self.secret[g])
                result[g] = r
                if r == -1: self.lo[g] = max(self.lo[g], x + 1)
                elif r == 1: self.hi[g] = min(self.hi[g], x - 1)
                else: self.lo[g] = self.hi[g] = x
        self.pending = guesses
        return result


def find_secret_linear(n, check):
    """Independent O(n) reference for Part 1: tries 1, 2, 3, ... in increasing order, never
    calling find_secret or any of its helpers."""
    if n == 1:
        return 1
    pending = 1
    check(1)
    for x in range(2, n + 1):
        r = check(x)
        if r == 0:
            return pending
        pending = x
    return n   # every one of 1..n-1 compared "less than secret", so secret must be n


t0 = time.time()

# --- the transcripts in the problem statement, replayed against the judges ---
j = Judge(7, 5)
assert [j.check(x) for x in (3, 6, 4, 7)] == [None, -1, 1, -1]
assert (j.lo, j.hi) == (5, 5)
expect_rejected(j.check, 2)          # secret is pinned down: no further call is allowed

jb = BatchJudge(13, 9)
assert jb.check_batch([4, 10]) is None and jb.check_batch([2]) == [-1, 1]

jr = GamesJudge({"A": 5, "B": 20}, {"A": 4, "B": 15})
assert jr.check_round({"A": 2, "B": 8}) is None
assert jr.check_round({}) == {"A": -1, "B": -1}

# --- Part 1: every (n, secret) for small n, then every magnitude up to 1e9 ---
slacks = set()                       # calls - 2*ceil(log2 n); 0 means the bound was reached exactly
for n in range(1, 400):
    for secret in range(1, n + 1):
        j = Judge(n, secret)
        assert find_secret(n, j.check) == secret
        slacks.add(j.calls - 2 * ceil_log(n, 2))

rng = random.Random(0)
sizes = ([10 ** e for e in range(2, 10)] + [2 ** e for e in range(7, 30)]
         + [2 ** e + 1 for e in range(7, 30)])
for n in sizes:
    for secret in [1, 2, n // 2, n // 2 + 1, n - 1, n] + [rng.randint(1, n) for _ in range(40)]:
        j = Judge(n, secret)
        assert find_secret(n, j.check) == secret
        slacks.add(j.calls - 2 * ceil_log(n, 2))
print(f"Part 1: exhaustive for n < 400, then {len(sizes)} sizes up to 1e9 -- worst case exactly "
      f"2*ceil(log2 n) calls and never more (a lucky exact hit can end {-min(slacks)} calls sooner)")
assert max(slacks) == 0          # the bound is reached, so it is tight, and never exceeded

# naive linear-scan cross-check, independent of find_secret
rng = random.Random(1)
for _ in range(400):
    n = rng.randint(1, 500)
    secret = rng.randint(1, n)
    j_fast, j_lin = Judge(n, secret), Judge(n, secret)
    fast, lin = find_secret(n, j_fast.check), find_secret_linear(n, j_lin.check)
    assert fast == secret == lin
print("Part 1: naive linear-scan cross-check agrees on 400 random cases")

# --- Part 2: same structure, base 3; the batch sizes show when the one-point fallback fires ---
n_fallback = 0
for n in range(1, 350):
    for secret in range(1, n + 1):
        j = BatchJudge(n, secret)
        assert find_secret_batched(n, j.check_batch) == secret
        assert j.calls <= 2 * ceil_log(n, 3)
        # a filler is always one guess, so two one-guess calls in a row means a real round fell back
        n_fallback += any(a == b == 1 for a, b in zip(j.sizes, j.sizes[1:]))

rng = random.Random(2)
for n in sizes:
    for secret in [1, n // 2, n] + [rng.randint(1, n) for _ in range(20)]:
        j = BatchJudge(n, secret)
        assert find_secret_batched(n, j.check_batch) == secret
        assert j.calls <= 2 * ceil_log(n, 3)
print(f"Part 2: exhaustive for n < 350 ({n_fallback} of them fell back to a one-point batch) plus the "
      f"same sizes up to 1e9 -- never above 2*ceil(log3 n) calls")
assert n_fallback > 5000

n, rng = 10 ** 9, random.Random(6)
worst_1, worst_3 = 0, 0
for secret in [rng.randint(1, n) for _ in range(50)]:
    j1, j3 = Judge(n, secret), BatchJudge(n, secret)
    assert find_secret(n, j1.check) == find_secret_batched(n, j3.check_batch) == secret
    worst_1, worst_3 = max(worst_1, j1.calls), max(worst_3, j3.calls)
print(f"Part 2: over 50 secrets at n = 1e9 the worst case is {worst_3} calls, Part 1's is {worst_1}")
assert worst_3 < worst_1

# --- Part 3: small multi-game batches, then many games of wildly different sizes ---
n_mixed = 0                      # batches mixing a one-round game with a thirty-round one
for seed in range(800):
    rng = random.Random(seed)
    small = seed < 500
    count = rng.randint(1, 5 if small else 60)
    bounds = {i: rng.randint(1, 10 if small else 10 ** rng.randint(0, 9)) for i in range(count)}
    secrets = {i: rng.randint(1, bounds[i]) for i in bounds}
    j = GamesJudge(bounds, secrets)
    assert solve_games(bounds, j.check_round) == secrets
    ks = [ceil_log(b, 2) for b in bounds.values()]
    assert j.calls <= 2 * max(ks)
    n_mixed += max(ks) - min(ks) >= 10
print(f"Part 3: 800 batches up to 60 games, n<=1e9 -- rounds never above 2*ceil(log2 max n) "
      f"({n_mixed} batches mixed games differing by 10 or more halvings)")
assert n_mixed > 200

# quantify the pipelining benefit against solving the same games one at a time
rng = random.Random(5)
bounds = {i: rng.randint(500_000_000, 10**9) for i in range(30)}
secrets = {i: rng.randint(1, bounds[i]) for i in range(30)}
jg = GamesJudge(bounds, secrets)
assert solve_games(bounds, jg.check_round) == secrets
separate = 0
for i in bounds:
    ji = Judge(bounds[i], secrets[i])
    assert find_secret(bounds[i], ji.check) == secrets[i]
    separate += ji.calls
print(f"Part 3: 30 games, n up to 1e9 -- together {jg.calls} rounds against a floor of "
      f"{ceil_log(max(bounds.values()) + 1, 2)} for any protocol, one at a time {separate} calls")
assert jg.calls * 10 < separate

# --- negative paths: the judges reject every protocol violation ---
j = Judge(10, 6)
j.check(5)
expect_rejected(j.check, 5)                         # a repeated guess
expect_rejected(Judge(10, 6).check, 11)             # outside [1, n]
expect_rejected(Judge(1, 1).check, 1)               # n == 1: determined before any call

jb = BatchJudge(10, 6)
jb.check_batch([3, 7])
expect_rejected(jb.check_batch, [3])                # a repeat in a later batch
expect_rejected(jb.check_batch, [8, 8])             # a repeat inside one batch
expect_rejected(jb.check_batch, [])                 # every call carries at least one guess

jr = GamesJudge({"A": 10, "B": 20}, {"A": 5, "B": 15})
jr.check_round({"A": 5, "B": 10})
expect_rejected(jr.check_round, {"A": 5})
expect_rejected(jr.check_round, {"B": 25})
print("negative paths: repeat / out-of-bounds / empty batch / already-determined all rejected")

print("total elapsed", round(time.time() - t0, 2), "s")
```

</details>

</details>
