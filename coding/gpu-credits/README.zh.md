# GPU 额度账本

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 中等 | SWE | data-structure, simulation, heap | 3 个部分 |
<!-- meta:end -->

## 题目

一个 *GPU 额度账本*（GPU credit ledger）以*授予*（grant）的形式发放额度，额度随时间被消耗。

`add_credit(credit_id, amount, timestamp, expiration)` 发放一笔新的授予，数量为 `amount`，用 `credit_id`
标识（在所有发放过的授予中唯一）。`expiration` 是一个时长，不是绝对时刻：这笔授予在闭区间
`[timestamp, timestamp + expiration]` 内有效，两端都包含在内。

`subtract(amount, timestamp)` 在时刻 `timestamp` 消耗 `amount` 数量的额度。它从在 `timestamp` 时刻有效的
授予中扣减，先扣 `timestamp + expiration` 最小的那一笔——也就是最快过期的那一笔——扣完之后再扣下一笔，
所以一次调用可能跨越多笔授予。一笔授予被这样扣掉的额度不会再恢复。

如果 `amount` 超过 `timestamp` 时刻所有有效授予的总量，`subtract` 仍然不会报错：超出的部分记为一笔未偿还的
*欠额*（debt）。欠额不附着在任何一笔具体的授予上，而是由 `timestamp` 更晚的授予偿还：一笔授予生效时，它的
`amount` 首先用于偿还尚未清偿的欠额，偿还之后还有剩余，剩余部分才成为这笔授予的额度，供之后的 `subtract`
扣减。用于偿还的部分和被 `subtract` 扣掉的额度一样，花掉就不再恢复：这笔授予过期时，它还掉的欠额不会重新
出现。因此账本可能长时间处于欠额状态，直到后续生效的授予累计足以补上为止。

`get_balance(timestamp)` 报告账本在 `timestamp` 时刻的状态。这个状态的定义是：把迄今为止的所有
`add_credit` 和 `subtract` 调用按各自 `timestamp` 从小到大的顺序（而不是调用实际发生的顺序）重放一遍，
其中只重放 `timestamp` 不超过被查询时刻的那些调用。设 $v$ 为该时刻所有有效授予的剩余额度之和，减去该时刻
尚未偿还的欠额。`get_balance` 在 $v$ 为负时返回 `None`，否则返回 $v$ 本身。特别地，当没有任何有效授予、
也没有欠额时——第一笔授予生效之前，或者最后一笔授予过期之后——$v = 0$，返回值是整数 `0`，而不是 `None`。

数量、时间戳和时长都是非负整数。`add_credit` 与 `subtract` 合在一起，任何两次调用的 `timestamp` 都不相同；
不过两笔不同的授予可以在同一时刻过期。

### Part 1 —— 按时间顺序到达

在这一部分中，`add_credit`、`subtract` 和 `get_balance` 总是按 `timestamp` 非降序被调用：调用的先后顺序
与事件实际发生的先后顺序一致。

```py
class GPUCreditLedger:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

例子：

```text
add_credit('r1', 6, 10, 20)   # 在 [10, 30] 内有效
get_balance(10)  -> 6         # r1 的有效区间正好从 10 开始
add_credit('r2', 5, 14, 6)    # 在 [14, 20] 内有效
subtract(3, 16)               # r2 过期更早，先扣它：r2 5 -> 2
add_credit('r3', 4, 18, 8)    # 在 [18, 26] 内有效
subtract(9, 19)               # 按过期时间从早到晚：r2 扣 2，r3 扣 4，r1 扣 3（原有 6）
get_balance(19)  -> 3         # 只剩 r1，还有 3
get_balance(20)  -> 3         # 20 是 r2 的区间 [14, 20] 的最后一刻，但 r2 早已扣空
add_credit('r4', 2, 24, 4)    # 在 [24, 28] 内有效
get_balance(28)  -> 5         # r1（3）和 r4（2）都还有效
get_balance(29)  -> 3         # r4 的区间 [24, 28] 刚刚结束，只剩 r1
get_balance(31)  -> 0         # r1 的区间 [10, 30] 也结束了：没有任何有效授予，答案是 0
```

### Part 2 —— 乱序到达

现实中的调用方无法保证这一点：`add_credit` 和 `subtract` 现在可以按任意顺序被调用，与它们各自的
`timestamp` 无关——一个 `timestamp = 42` 的 `subtract` 可能在为它提供额度的 `timestamp = 35` 的
`add_credit` 之前就被调用。`get_balance(timestamp)` 的定义不变：仍然是把迄今为止的所有调用按 `timestamp`
从小到大重放一遍所得到的结果。

```py
class GPUCreditLedgerAnyOrder:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

例子（下面按调用发生的先后顺序列出，这个顺序并不是各自 `timestamp` 的顺序）：

```text
subtract(5, 42)                 # 此时还没有调用过任何 add_credit
get_balance(8)  -> 0            # 还没有 timestamp <= 8 的调用
add_credit('s1', 7, 35, 25)     # 在 [35, 60] 内有效
get_balance(35) -> 7            # 那次 subtract 的 timestamp 是 42，对这次查询来说还没有发生
get_balance(42) -> 2            # 按 timestamp 的顺序重放：7 - 5 = 2
subtract(10, 48)                # 48 时刻只有 2 个有效额度，其余 8 记为欠额
get_balance(48) -> None         # v = 0 - 8 = -8
add_credit('s2', 5, 52, 10)     # 在 [52, 62] 内有效；5 全部用来还欠额，8 -> 3，s2 自己一点不剩
get_balance(52) -> None         # v = 0 - 3 = -3
add_credit('s3', 3, 57, 10)     # 在 [57, 67] 内有效；正好还清剩下的欠额
get_balance(57) -> 0            # v = 0 - 0，返回整数 0，而不是 None
get_balance(70) -> 0            # s2 和 s3 都已过期；它们还掉的欠额不会重新出现
```

### Part 3 —— 快速回答大量查询

实现 `GPUCreditLedgerFast`，行为与 `GPUCreditLedgerAnyOrder` 相同，但要让一段以 `get_balance` 为主的长
调用序列跑得快。设共有 $U$ 次 `add_credit`/`subtract` 调用和 $Q$ 次 `get_balance` 调用，查询的时间戳非降序，
且每次查询都发生在所有 `timestamp` 不超过它的 `add_credit`/`subtract` 之后；此时全部 $Q$ 次 `get_balance`
调用合计耗时必须是 $O(U \log U + Q)$——而每次查询都从头重放全部调用要花 $O(Q \cdot U \log U)$。其他到达
方式（查询不满足上述顺序，或者有 `add_credit`/`subtract` 落在某个已经查询过的时间戳上或它之前）可以退化到
较慢的路径，但 `get_balance` 仍必须返回上面定义的那个值。

```py
class GPUCreditLedgerFast:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得确认两条规则，因为合理的账本在这两处做法不一：没有任何有效授予时 `get_balance` 返回什么
（这里返回 `0`，`None` 只留给 $v$ 为负的情形）；超支之后怎么办（这里记为欠额，由之后的授予偿还，还掉就
不再恢复）。还要问清调用能否保证按时间戳顺序到达：能的话，Part 1 就已经是最终答案。

### Part 1

用一个按 `timestamp + expiration` 排序的小根堆保存当前有效的授予，堆顶永远是最快过期的那一笔；再记两个数：
堆中剩余额度之和 `total`，以及累计的 `debt`。`add_credit` 先用新授予的额度偿还 `debt`，剩下的部分再入堆。
`subtract` 在它自己的时间戳上，先丢弃堆里已经过期的授予，再反复从堆顶扣减，直到扣满所需数量或堆变空为止，
扣不掉的部分计入 `debt`。`get_balance` 用同样的方式丢弃过期的授予，然后返回 `total - debt`，为负时返回
`None`。欠额只在堆被扣空之后才会产生，新授予也要等欠额还清才会入堆，所以返回 `None` 正好等价于 `debt > 0`。

Part 2 和 Part 3 都要通过同一套逻辑重放事件，所以把它写成一个小的状态类，每个事件用一个元组表示；Part 1
的账本只是它外面薄薄的一层：

```python
import heapq


class _LedgerState:
    """The ledger right after replaying some events in increasing order of timestamp."""

    def __init__(self):
        self.active = []    # heap of [expire_at, remaining]; the earliest-expiring grant is on top
        self.total = 0      # sum of remaining over self.active
        self.debt = 0

    def _drop_expired(self, ts):
        while self.active and self.active[0][0] < ts:     # NOTE: '<', not '<=' -- expiration is inclusive
            self.total -= heapq.heappop(self.active)[1]

    def apply(self, ts, event):
        """Applies one event as of its own timestamp ts."""
        if event[0] == "add":
            _, _credit_id, amount, expire_at = event
            paid = min(self.debt, amount)     # NOTE: a new grant repays outstanding debt before it can be spent
            self.debt -= paid
            if amount > paid:
                heapq.heappush(self.active, [expire_at, amount - paid])
                self.total += amount - paid
            return
        _, amount = event
        self._drop_expired(ts)
        while amount > 0 and self.active:
            grant = self.active[0]
            take = min(amount, grant[1])
            grant[1] -= take
            self.total -= take
            amount -= take
            if grant[1] == 0:
                heapq.heappop(self.active)
        self.debt += amount           # NOTE: whatever no valid grant could cover becomes debt

    def balance(self, ts):
        self._drop_expired(ts)
        net = self.total - self.debt      # NOTE: O(1); summing the heap here would cost O(k) on every query
        return None if net < 0 else net


class GPUCreditLedger:
    def __init__(self):
        self._state = _LedgerState()

    def add_credit(self, credit_id, amount, timestamp, expiration):
        self._state.apply(timestamp, ("add", credit_id, amount, timestamp + expiration))

    def subtract(self, amount, timestamp):
        self._state.apply(timestamp, ("sub", amount))

    def get_balance(self, timestamp):
        return self._state.balance(timestamp)
```

一次 `subtract` 可能从堆里弹出好几笔授予，但每笔授予一生中只入堆一次、最多出堆一次，所以 $n$ 次调用的
总代价是 $O(n \log n)$。

### Part 2

一旦调用可以乱序到达，堆就不能再实时更新了：如果 `timestamp = 42` 的 `subtract` 已经处理完，
`timestamp = 35` 的 `add_credit` 才被调用，它就得插进一个已经越过这个时刻的堆里。`GPUCreditLedgerAnyOrder`
转而把每次调用按调用顺序追加到一份日志里，每次查询都从头重建状态：把日志按 `timestamp`（而不是调用顺序）
排序，只保留不晚于查询时刻的事件，依次交给一个全新的 `_LedgerState`。

```python
class GPUCreditLedgerAnyOrder:
    def __init__(self):
        self._events = []   # append-only, call order -- NOT necessarily sorted by timestamp

    def add_credit(self, credit_id, amount, timestamp, expiration):
        self._events.append((timestamp, ("add", credit_id, amount, timestamp + expiration)))

    def subtract(self, amount, timestamp):
        self._events.append((timestamp, ("sub", amount)))

    def get_balance(self, timestamp):
        state = _LedgerState()
        for ts, event in sorted(e for e in self._events if e[0] <= timestamp):   # NOTE: sorted by
            state.apply(ts, event)                                              # timestamp, not call order
        return state.balance(timestamp)
```

这对任意到达顺序都是正确的，但每次 `get_balance` 都要把相关的整段日志重新排序、重放一遍：对不晚于查询
时刻的 $n$ 次调用，每次都是 $O(n \log n)$。

### Part 3

面对大量查询时，Part 2 慢在两处：每次调用都要重新排序日志；即便这一次查询的时间戳与上一次几乎相同，也要
从头重放一遍。`GPUCreditLedgerFast` 把这两处都解决掉，但只在题目指定的那种到达方式下才快：

- 用 `bisect.insort` 让日志始终按时间戳有序，而不是每次查询都重新排序。
- 维护一个*游标*（cursor）：把不晚于“迄今查询过的最大时间戳”的全部事件都应用之后得到的 `_LedgerState`。
  不早于游标的查询只需应用两者之间的事件。
- 早于游标的查询是在问过去。游标处的状态已经包含了更晚的事件，无法倒退，所以这种查询退回到和 Part 2
  一样的完整重放，不动游标。
- 落在游标上或游标之前的 `add_credit`/`subtract` 会使游标失效：那份状态是在没有这个事件时算出来的。于是
  丢弃游标，等下一次查询再重建。
- 答案按时间戳缓存，重复查询同一个时间戳只是一次字典查找。缓存里的时间戳都不晚于游标，所以游标之后的新事件
  改变不了任何已缓存的答案；迟到的事件则连同游标一起清空缓存。

```python
import bisect


class GPUCreditLedgerFast:
    def __init__(self):
        self._log = []                        # (timestamp, event), kept sorted by timestamp
        self._cursor_ts = float("-inf")       # highest timestamp queried since the last late event
        self._cursor_idx = 0                  # index into self._log of the next event to apply
        self._state = _LedgerState()          # every event at or before self._cursor_ts, applied
        self._cache = {}                      # every key is <= self._cursor_ts

    def _insert_event(self, timestamp, event):
        bisect.insort(self._log, (timestamp, event))
        if timestamp <= self._cursor_ts:      # NOTE: a late event -- drop the cursor and every cached answer
            self._cursor_ts, self._cursor_idx = float("-inf"), 0
            self._state = _LedgerState()
            self._cache.clear()

    def add_credit(self, credit_id, amount, timestamp, expiration):
        self._insert_event(timestamp, ("add", credit_id, amount, timestamp + expiration))

    def subtract(self, amount, timestamp):
        self._insert_event(timestamp, ("sub", amount))

    def get_balance(self, timestamp):
        if timestamp in self._cache:
            return self._cache[timestamp]
        if timestamp >= self._cursor_ts:
            while self._cursor_idx < len(self._log) and self._log[self._cursor_idx][0] <= timestamp:
                self._state.apply(*self._log[self._cursor_idx])
                self._cursor_idx += 1
            self._cursor_ts = timestamp
            state = self._state
        else:                                 # NOTE: a query behind the cursor -- one full replay, O(n log n)
            state = _LedgerState()
            for ts, event in self._log:
                if ts > timestamp:
                    break
                state.apply(ts, event)
        self._cache[timestamp] = state.balance(timestamp)
        return self._cache[timestamp]
```

只要游标一直在推进——查询非降序、没有迟到的事件——账本整个生命周期里每个事件只被应用一次，每笔授予最多
入堆、出堆各一次，合计 $O(U \log U)$；除此之外每次查询只是一次字典查找加一次减法，总共
$O(U \log U + Q)$。`bisect.insort` 每次调用仍要花 $O(n)$ 移动列表；如果 `add_credit`/`subtract`
也很频繁，就把列表换成一棵按时间戳排序的平衡树，例如[内存分配器](../memory-allocator/README.zh.md)里的
树堆。先乱序调用 2000 次 `add_credit`/`subtract`、再做 20000 次非降序查询，这个实现回答查询比 Part 2
快两个数量级以上。

### 追问

- 生产环境里的额度控制：执行请求所代表的昂贵工作之前先查 `get_balance`，余额够付预估成本才放行，做完再按
  实际成本 `subtract`。让 `subtract` 永远成功、任由欠额累积，是记账方式，不是消费策略。
- 迟到的事件很频繁：每隔若干个事件给状态存一份快照，迟到的事件只需退回到它之前最近的快照，而不是从头重建；
  日志持久化之后，同一批快照也就是恢复用的检查点。
- 撤销一次 `subtract`：正确的退款要记住这次扣减动用了哪些授予、各扣了多少，才能原样补回；改为补发一笔新的
  授予，额度的过期时间就变了。
- 同一个 `timestamp` 上有多个事件：一旦允许，就要约定次序作为排序的第二关键字，例如先授予、后消耗，再按
  调用先后。

<details>
<summary>验证代码（可运行）</summary>

```python
import random
import time


def feed(ledger, op):
    if op[0] == 'add':
        ledger.add_credit(*op[1:])      # ('add', credit_id, amount, timestamp, expiration)
    else:
        ledger.subtract(*op[1:])        # ('sub', amount, timestamp)


def when(op):
    return op[3] if op[0] == 'add' else op[2]


# --- the two examples of the statement, on every class that accepts their call order ---
part1_calls = [('add', 'r1', 6, 10, 20), ('ask', 10, 6), ('add', 'r2', 5, 14, 6), ('sub', 3, 16),
               ('add', 'r3', 4, 18, 8), ('sub', 9, 19), ('ask', 19, 3), ('ask', 20, 3),
               ('add', 'r4', 2, 24, 4), ('ask', 28, 5), ('ask', 29, 3), ('ask', 31, 0)]
part2_calls = [('sub', 5, 42), ('ask', 8, 0), ('add', 's1', 7, 35, 25), ('ask', 35, 7), ('ask', 42, 2),
               ('sub', 10, 48), ('ask', 48, None), ('add', 's2', 5, 52, 10), ('ask', 52, None),
               ('add', 's3', 3, 57, 10), ('ask', 57, 0), ('ask', 70, 0)]
for calls, classes in [(part1_calls, [GPUCreditLedger, GPUCreditLedgerAnyOrder, GPUCreditLedgerFast]),
                       (part2_calls, [GPUCreditLedgerAnyOrder, GPUCreditLedgerFast])]:
    for cls in classes:
        ledger = cls()
        assert ledger.get_balance(9) == 0
        for call in calls:
            if call[0] == 'ask':
                got = ledger.get_balance(call[1])
                assert got == call[2] and type(got) is type(call[2]), (cls.__name__, call, got)
            else:
                feed(ledger, call)


# --- an independent reading of the statement: no heap, no shared helper, one linear scan per subtract ---
def reference_balance(ops, t):
    grants, debt = {}, 0                     # credit_id -> [first valid instant, last valid instant, remaining]
    for op in sorted((op for op in ops if when(op) <= t), key=when):
        if op[0] == 'add':
            _, credit_id, amount, ts, expiration = op
            repaid = min(debt, amount)
            debt -= repaid
            grants[credit_id] = [ts, ts + expiration, amount - repaid]
        else:
            _, need, ts = op
            for grant in sorted((g for g in grants.values() if g[0] <= ts <= g[1]), key=lambda g: g[1]):
                take = min(need, grant[2])
                grant[2] -= take
                need -= take
            debt += need
    v = sum(g[2] for g in grants.values() if g[0] <= t <= g[1]) - debt
    return None if v < 0 else v


# rules the examples do not reach
ops = [('add', 'a', 10, 10, 30), ('sub', 100, 20), ('add', 'b', 200, 50, 10)]   # b repays 90 and keeps 110
assert [reference_balance(ops, t) for t in (20, 41, 49, 50, 60, 61)] == [None, None, None, 110, 110, 0]
ops = [('sub', 4, 15), ('add', 'c', 6, 20, 5)]          # spent before c activates: debt, repaid at 20
assert [reference_balance(ops, t) for t in (14, 15, 19, 20, 25, 26)] == [0, None, None, 2, 2, 0]
ops = [('add', 'z', 5, 7, 0)]                           # expiration 0: valid at exactly one instant
assert [reference_balance(ops, t) for t in (6, 7, 8)] == [0, 5, 0]


def random_ops(rng, n, ts_max):
    ops = []
    for i, ts in enumerate(rng.sample(range(ts_max + 1), n)):       # distinct timestamps
        if rng.random() < 0.55:
            ops.append(('add', f'g{i}', rng.randint(1, 20), ts, rng.choice([0, 1, 4, 4, rng.randint(0, 15)])))
        else:
            ops.append(('sub', rng.choice([1, 2, 3, 5, 8, 30]), ts))
    return ops


def agree(ledgers, fed, t, context):
    expected = reference_balance(fed, t)
    for ledger in ledgers:
        got = ledger.get_balance(t)
        assert got == expected and type(got) is type(expected), (context, type(ledger).__name__, t, got, expected)
    return expected


seen = {'None': 0, 'zero': 0, 'positive': 0}
for seed in range(600):
    rng = random.Random(seed)
    ts_max = rng.choice([15, 30, 60])
    ops = random_ops(rng, rng.randint(1, 12), ts_max)

    # calls in timestamp order, queries in between: all three classes
    ledgers, fed, now = [GPUCreditLedger(), GPUCreditLedgerAnyOrder(), GPUCreditLedgerFast()], [], 0
    for op in sorted(ops, key=when):
        now = rng.randint(now, when(op))
        agree(ledgers, fed, now, ('in order', seed))
        for ledger in ledgers:
            feed(ledger, op)
        fed.append(op)
        now = when(op)
        agree(ledgers, fed, now, ('in order', seed))
    for t in range(now, ts_max + 18):
        agree(ledgers, fed, t, ('in order, tail', seed))

    # calls in arbitrary order, queries interleaved: some calls land behind timestamps already answered,
    # some queries repeat -- exercises the cursor reset and the cache of GPUCreditLedgerFast
    ledgers, fed, asked = [GPUCreditLedgerAnyOrder(), GPUCreditLedgerFast()], [], []
    rng.shuffle(ops)
    for op in ops:
        for ledger in ledgers:
            feed(ledger, op)
        fed.append(op)
        for _ in range(rng.randint(0, 3)):
            asked.append(rng.choice(asked) if asked and rng.random() < 0.3 else rng.randint(0, ts_max + 17))
            agree(ledgers, fed, asked[-1], ('any order', seed))
    for t in rng.sample(range(ts_max + 18), ts_max + 18):
        expected = agree(ledgers, fed, t, ('any order, sweep', seed))
        seen['None' if expected is None else 'zero' if expected == 0 else 'positive'] += 1
assert min(seen.values()) > 1000, seen

# --- Part 3: non-decreasing queries after out-of-order calls ---
rng = random.Random(7)
slow, fast = GPUCreditLedgerAnyOrder(), GPUCreditLedgerFast()
for i, ts in enumerate(rng.sample(range(20_000), 2_000)):
    op = ('add', f'g{i}', rng.randint(1, 90), ts, rng.randint(0, 400)) if i % 2 else ('sub', rng.randint(1, 40), ts)
    feed(slow, op)
    feed(fast, op)
queries = sorted(rng.randint(0, 20_500) for _ in range(600))
start = time.perf_counter()
slow_answers = [slow.get_balance(t) for t in queries]
slow_seconds = time.perf_counter() - start
start = time.perf_counter()
fast_answers = [fast.get_balance(t) for t in queries]
fast_seconds = time.perf_counter() - start
assert fast_answers == slow_answers
assert slow_seconds > 5 * fast_seconds, (slow_seconds, fast_seconds)   # measured: 100x or more at this size

print("all checks passed")
```

</details>

</details>
