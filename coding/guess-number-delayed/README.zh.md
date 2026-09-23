# 反馈延迟一轮的二分查找

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE · RE | binary-search, interaction, algorithm-design | 3 个部分 | 电话面 |
<!-- meta:end -->

## 题目

### Part 1 —— 一个秘密数字，每次调用猜一个数

闭区间 `[1, n]` 中有一个秘密整数 `secret`。了解它的唯一途径是 `check(x)`，但它的回答总是延迟整整一次调用：

- `x` 必须落在 `[1, n]` 内，并且不能与这局游戏里任何一次更早调用的 `x` 相同。
- 第一次调用 `check` 返回 `None`——此时还没有更早的猜测可以比较。
- 从第二次调用开始，每次返回的都是**上一次**调用参数与 `secret` 的比较结果：如果那个上一次的 `x` 小于 `secret` 返回 `-1`，等于返回 `0`，大于返回 `1`。你**这一次**传入的 `x` 的比较结果，要等到**下一次**调用才会揭示。
- 一旦已经揭示的比较结果只剩下一个可能的 `secret`，就不允许再调用 `check`；`n = 1` 时，第一次调用之前就已经如此。
- 由于这种延迟，任意时刻最多只有一次调用的比较结果还没揭示。你可以多花一次调用——用任意一个还没用过的合法 `x`——专门把它取回来。

```py
def check(x: int) -> int | None:
    """Provided. x must lie in [1, n] and must not repeat an earlier call's x in this game.
    Returns None on the very first call. On every later call, returns -1, 0, or 1: the
    comparison of the PREVIOUS call's argument against the hidden secret, never of x itself."""

def find_secret(n: int, check) -> int:
    """Returns secret, calling check at most 2 * ceil(log2(n)) + 1 times."""
```

例如，`n = 7`、`secret = 5` 时：

```text
check(3) -> None    # 还没有更早的猜测可以比较
check(6) -> -1      # 比较的是 3 和 secret：3 < 5
check(4) -> 1       # 比较的是 6 和 secret：6 > 5，于是 secret 落在 {4, 5} 中
check(7) -> -1      # 比较的是 4 和 secret：4 < 5，于是 secret = 5
```

到这一步 `secret = 5` 已经是唯一的可能，再调用一次 `check`（无论传入 `2` 还是别的没用过的数）都会被拒绝。

### Part 2 —— 每次调用猜两个数，同一个秘密数字

`check_batch` 取代 `check`，把同样的单次延迟施加到一整份列表上：

- 这局游戏里、任意一批中出现过的每个 `x`，都必须互不相同并落在 `[1, n]` 内，而且每次调用至少要带一个猜测。
- 第一次调用返回 `None`。
- 从第二次调用开始，每次返回一个长度与**上一次**调用的列表相同的列表，按同样的顺序给出那批里每个 `x` 与 `secret` 的比较结果。
- “多花一次调用取回最后一批结果”的规则、以及“一旦确定就不能再调用”的规则同样适用。

```py
def check_batch(xs: list[int]) -> list[int] | None:
    """Provided. Every x used across every call in the game must be distinct and lie in [1, n],
    and xs must be non-empty. Returns None on the first call. On every later call, returns a list
    the same length as the PREVIOUS call's xs, comparing each of those guesses to secret (same
    -1/0/1 sense as check), in the same order."""

def find_secret_batched(n: int, check_batch) -> int:
    """Returns secret, calling check_batch at most 2 * ceil(log(n, 3)) + 1 times."""
```

例如，`n = 13`、`secret = 9` 时：

```text
check_batch([4, 10]) -> None       # 还没有更早的一批可以比较
check_batch([2])     -> [-1, 1]    # 依次比较 4、10 和 secret：4 < 9，10 > 9
```

### Part 3 —— 多局互相独立的游戏，让总轮数最少

现在有若干局互相独立的游戏共用**同一条**通道，每局都有自己的编号、自己的上界 `n[g]` 和自己的秘密数字 `secret[g]`。每一轮你提交一个字典，把其中一部分编号（也可以一个都不含）映射到该局的一个猜测；`check_round` 会把**上一轮提交的整份内容**逐条回传比较结果，不管这一轮自己提交的是哪些编号：

- 对同一个编号来说，为它提交过的每个猜测必须互不相同，并落在 `[1, n[g]]` 内。
- 第一轮返回 `None`。
- 从第二轮开始，每次返回的字典恰好包含**上一轮**提交过的那些编号，每个映射到该猜测与它自己那局秘密数字的比较结果。
- 一旦某个编号的秘密数字已经确定，就不能再为它提交猜测。
- 现在要最小化的是总轮数（调用 `check_round` 的次数），不是猜测的总个数。

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

例如，游戏 `"A"`（`n = 5`、`secret = 4`）和 `"B"`（`n = 20`、`secret = 15`）：

```text
check_round({"A": 2, "B": 8}) -> None                 # 还没有更早的一轮可以比较
check_round({})               -> {"A": -1, "B": -1}   # 回传第 1 轮的猜测，尽管这一轮自己什么都没问
```

## 参考解答

<details>
<summary>展开参考解答</summary>

值得先确认一点：下面都假设 `check`（以及它的批量版、多局版）必须严格逐次调用。如果真实系统允许同时发出多个请求，延迟这件事本身就不存在了，普通二分就够用。

### Part 1

因为第 $i$ 次调用传入的参数，是在第 $i$ 次调用自己的返回值出现**之前**就已经定好的，所以你永远不知道刚刚那次猜测的比较结果——只知道再前一次的。因此这串调用必须交替扮演两种角色：*真实*探测，即当前 `[lo, hi]` 的中点；*填充*调用，它唯一的作用是让下一次调用发生，从而把真实探测的比较结果带回来。这个填充值本身会成为**下一个**待揭示的猜测，所以它自己的比较结果同样会被处理，和真实探测一视同仁。第一个填充值只能落在 `[lo, hi]` 里面，因为此时还没有排除掉任何数；之后的填充值则被推到 `[1, n]` 两端没动过的地方，那里的比较结果早就知道。两种情况下循环都只是照着回传的结果收窄区间，不需要特殊处理。

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

真实探测落在第 $1, 3, 5, \dots$ 次调用上，紧接着的那次调用就会把它揭示出来，也就是第 $2, 4, 6, \dots$ 次。所以经过 $2k$ 次调用，恰好有 $k$ 个真实探测被揭示，而每一个真实探测要么正好命中 `secret`，要么至少把 `[lo, hi]` 砍掉一半；因此 $k = \lceil \log_2 n \rceil$ 个被揭示的真实探测，总能把候选个数压到 1 以内，也就是 $2\lceil \log_2 n \rceil$ 次调用以内。如果中点已经被某个填充值占掉，探测点会被挪开一点、砍得少一些，所以下面的验证代码直接把调用次数量了出来——$n$ 小于 400 时的每个秘密数字，以及一直到 $10^9$ 的 54 个规模——都没有超过 $2\lceil \log_2 n \rceil$：签名允许多花的那一次（取回最后一个比较结果用的）从来没有用上。

### Part 2

同样的交替方式用在一批两个猜测上也成立：提交把 `[lo, hi]` 三等分的两个点 `lo + (hi - lo)//3` 和 `lo + 2*(hi - lo)//3`，下一轮读到它们的比较结果后，就能把候选范围收窄到含 `secret` 的那一段三分之一，而不是二分之一。一旦只剩下最多两个候选，一个探测点就足以把它们分清，所以这时的真实轮只提交一个点——也就是 Part 1 的二分——这同时给下一次的填充值留下了一个可用的数，`n` 小到 2 时全靠它。

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

同样的计数方式把 2 换成 3 依然成立：$k = \lceil \log_3 n \rceil$ 个被揭示的真实批次，总能把候选个数压到 1 以内，所以总调用数不超过 $2\lceil \log_3 n \rceil$。对任何 $n$ 都有 $\lceil \log_3 n \rceil \le \lceil \log_2 n \rceil$，所以这一问从不比 Part 1 差；$n$ 越大两者拉得越开，相差 $\log_2 3 \approx 1.58$ 倍：$n = 10^9$ 时下面的验证代码量到的是 38 次，而 Part 1 是 58 次。

### Part 3

多局游戏共用一条通道时，一轮根本不需要凑一个人工的填充值：把每一局还没解决的中点一次性全部提交上去，下一轮提交一个空字典，纯粹是为了让这一轮的比较结果传回来。每一局都搭着同样的两轮节奏往前走，一旦自己的 `[lo, hi]` 缩到一点就从字典里自然消失，所以总轮数只取决于哪一局需要的对半次数最多——正是把 Part 1 的界用在最大的那个 `n[g]` 上；其余更小的游戏都在路上顺便解决掉，不额外花代价。

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

记 $k = \lceil \log_2(\max_g n[g]) \rceil$。最大的那一局单独玩要花 Part 1 的 $2k$ 次调用，而 `solve_games` 无论带上多少局，花掉的都正好是这 $2k$ 轮。任何协议在规模为 $n$ 的一局上都不可能少于 $\lceil \log_2(n + 1) \rceil$ 轮：$r$ 轮过后这一局最多只有 $r - 1$ 个比较结果回传过来，而 $c$ 次三路比较最多能区分 $2^{c+1} - 1$ 个值，于是 $n \le 2^r - 1$。下面的验证代码把两头都算成了具体的数字：30 局游戏、$n$ 最大到 $10^9$，一起解只要 58 轮，而任何协议的下界是 30 轮；逐局单独解则要 1694 次调用。

### 追问

- 如果 `check` 可以并发调用（在收到任何回复之前就能发出多个请求），延迟就不存在了，普通二分用 $\lceil \log_2 n \rceil$ 次调用即可。
- Part 2 的想法可以推广成每轮提交 $b - 1$ 个点，把 `[lo, hi]` 每轮缩小为原来的 $1/b$；$b$ 取得太大，瓶颈就会从轮数变成一批里的猜测个数。
- 用 Fibonacci／黄金比例的策略，原则上能把 Part 1 逼近到 $1.44 \log_2 n$ 次调用左右，做法是让每次探测的角色取决于相邻两个 Fibonacci 数的比例，而不是严格取中点；但要在这种延迟协议下把它构造并证明正确，比上面的界要复杂得多。
- Part 3 里那一轮“真实”提交，也可以把 Part 2 的三分点用到每一局上，而不是只提交中点，把两种加速叠加起来，轮数降到约 $2\lceil \log_3(\max_g n[g]) \rceil$。
- 如果网络故障会悄悄丢掉一次调用，这套协议完全没有办法察觉；两种角色交替的机制还需要额外加上序列号，或者给 `check` 补一条超时重试的规则。

<details>
<summary>验证代码（可运行）</summary>

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
