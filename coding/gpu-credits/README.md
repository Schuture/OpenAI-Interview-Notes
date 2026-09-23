# GPU Credits

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Medium | SWE | data-structure, simulation, heap | 3 parts |
<!-- meta:end -->

## Problem

A *GPU credit ledger* issues credit in *grants* and spends it over time.

`add_credit(credit_id, amount, timestamp, expiration)` issues a new grant of `amount` credits,
identified by `credit_id` (unique across every grant ever issued). `expiration` is a duration, not an
absolute time: the grant is valid on the closed interval `[timestamp, timestamp + expiration]`,
including both endpoints.

`subtract(amount, timestamp)` spends `amount` credits at time `timestamp`. It drains the grants that
are valid at `timestamp`, starting from the one with the smallest `timestamp + expiration` — the one
that expires soonest — and moving on to the next once the current one is exhausted, so a single call
may drain more than one grant. Credit a grant loses this way never comes back.

If `amount` is larger than everything valid at `timestamp`, `subtract` still never raises: the shortfall
becomes an outstanding *debt*. Debt is not attached to any one grant. It is repaid by grants with a
later `timestamp`: when a grant activates, its `amount` first pays down whatever debt is still
outstanding, and only what is left over, if anything, becomes the grant's credit, which a later
`subtract` can drain. The part that went to the debt is spent for good, exactly like credit drained by
`subtract`: the debt does not come back when that grant expires. A ledger can therefore stay in debt
for a long time, until enough new grants have activated to clear it.

`get_balance(timestamp)` reports the state of the ledger at `timestamp`, as if every `add_credit` and
`subtract` made so far had been replayed in increasing order of its own `timestamp` — not the order
the calls were actually made in — keeping only those whose `timestamp` is at most the one being
queried. Let $v$ be the sum of the remaining credit of every grant valid at that instant, minus the
debt outstanding at that instant. `get_balance` returns `None` when $v$ is negative, and returns $v$
itself otherwise. In particular, when no grant is valid and no debt is outstanding — before the first
grant activates, or after the last one has expired — $v = 0$ and the return value is the integer `0`,
not `None`.

Amounts, timestamps and durations are non-negative integers. Across `add_credit` and `subtract`
together, no two calls ever carry the same `timestamp`; two different grants may still expire at the
same instant. Across the whole call sequence, $U$ (calls to `add_credit`/`subtract`) and $Q$ (calls
to `get_balance`) are each at most $2 \times 10^4$; every `timestamp` and `expiration` is at most
$10^9$, `amount` is between $1$ and $10^9$, and a running total can exceed the range of a 32-bit
integer.

### Part 1 — In-order arrival

For this part, `add_credit`, `subtract` and `get_balance` are always called in non-decreasing order of
`timestamp`: the sequence of calls matches the order in which the events actually happen.

```py
class GPUCreditLedger:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

Example:

```text
add_credit('r1', 6, 10, 20)   # valid on [10, 30]
get_balance(10)  -> 6         # r1's window starts exactly at 10
add_credit('r2', 5, 14, 6)    # valid on [14, 20]
subtract(3, 16)               # drains r2 first, since it expires sooner: r2 5 -> 2
add_credit('r3', 4, 18, 8)    # valid on [18, 26]
subtract(9, 19)               # earliest-expiring first: r2 (2), then r3 (4), then r1 (3 of 6)
get_balance(19)  -> 3         # only r1 is left, holding 3 credits
get_balance(20)  -> 3         # 20 is the last instant of r2's window [14, 20], but r2 is already empty
add_credit('r4', 2, 24, 4)    # valid on [24, 28]
get_balance(28)  -> 5         # r1 (3) and r4 (2) are both still valid
get_balance(29)  -> 3         # r4's window [24, 28] has just ended; only r1 remains
get_balance(31)  -> 0         # r1's window [10, 30] has ended too: nothing is valid, and the answer is 0
```

### Part 2 — Out-of-order arrival

Real callers cannot guarantee this: `add_credit` and `subtract` may now be called in any order,
independent of their `timestamp` — a `subtract` for `timestamp = 42` may be called before the
`add_credit` for `timestamp = 35` that is meant to fund it. `get_balance(timestamp)` must still behave
exactly as defined above, as if every call made so far had been replayed in increasing order of
`timestamp`.

```py
class GPUCreditLedgerAnyOrder:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

Example (calls are listed in the order they are made, which is not the order of their `timestamp`):

```text
subtract(5, 42)                 # called before any add_credit at all
get_balance(8)  -> 0            # nothing has a timestamp <= 8 yet
add_credit('s1', 7, 35, 25)     # valid on [35, 60]
get_balance(35) -> 7            # the subtract's timestamp (42) is still in the future of this query
get_balance(42) -> 2            # replayed in timestamp order: 7 - 5 = 2
subtract(10, 48)                # only 2 credits are valid at 48; the other 8 become debt
get_balance(48) -> None         # v = 0 - 8 = -8
add_credit('s2', 5, 52, 10)     # valid on [52, 62]; all 5 go to the debt, 8 -> 3, and s2 holds nothing
get_balance(52) -> None         # v = 0 - 3 = -3
add_credit('s3', 3, 57, 10)     # valid on [57, 67]; clears exactly the remaining debt
get_balance(57) -> 0            # v = 0 - 0, returned as the integer 0, not None
get_balance(70) -> 0            # s2 and s3 have expired; the debt they repaid does not come back
```

### Part 3 — Answering many queries quickly

Implement `GPUCreditLedgerFast`, with the same behavior as `GPUCreditLedgerAnyOrder`, so that a long
call sequence dominated by `get_balance` is fast. When the $Q$ calls to `get_balance` have
non-decreasing timestamps, each made after every `add_credit`/`subtract` whose `timestamp` is at most
its own, the time spent inside all $Q$ of them together must be $O(U \log U + Q)$ — against the
$O(Q \cdot U \log U)$ of replaying every call from scratch on each query. Other arrival patterns (a
query out of that order, or an `add_credit`/`subtract` landing at or behind a timestamp already
queried) may fall back to a slower path, but `get_balance` must still return the value defined above.

```py
class GPUCreditLedgerFast:
    def add_credit(self, credit_id: str, amount: int, timestamp: int, expiration: int) -> None: ...
    def subtract(self, amount: int, timestamp: int) -> None: ...
    def get_balance(self, timestamp: int) -> int | None: ...
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two rules are worth confirming before coding, because reasonable ledgers differ on them: what
`get_balance` returns when no grant is valid (here `0`; `None` is reserved for a negative $v$), and what
happens to an overdraft (here it becomes debt, which later grants repay for good). Also ask whether
calls are guaranteed to arrive in timestamp order: if they are, Part 1 is already the final answer.

### Part 1

Keep the currently valid grants in a min-heap keyed by `timestamp + expiration`, so the one that expires
soonest is always on top, together with `total`, the sum of what the heap holds, and the running `debt`.
`add_credit` first pays down `debt`, then pushes whatever amount is left. `subtract`, at its own
timestamp, first discards anything from the heap that has already expired, then drains the top of the
heap repeatedly until the requested amount is covered or the heap is empty, adding whatever is left over
to `debt`. `get_balance` discards expired grants the same way and returns `total - debt`, or `None` when
that is negative. Debt only arises once the heap is empty, and a new grant is pushed only after the debt
is cleared, so `None` means exactly `debt > 0`.

Parts 2 and 3 replay events through the same logic, so it lives in a small state class that takes each
event as a tuple; the ledger of Part 1 is a thin wrapper around it:

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

A single `subtract` can pop several grants off the heap, but each grant is pushed once and popped at
most once over its whole lifetime, so $n$ calls cost $O(n \log n)$ in total.

### Part 2

Once calls can arrive in any order, the heap can no longer be updated live: an `add_credit` for
`timestamp = 35` that is called after a `subtract` for `timestamp = 42` has already been applied would
have to be inserted into a heap that has moved past it. `GPUCreditLedgerAnyOrder` instead keeps every
call in a plain append-only log, in call order, and rebuilds the state from scratch on every query: sort
the log by `timestamp` — not call order — keep only the events at or before the query, and feed them to
a fresh `_LedgerState`.

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

This is correct for any arrival order, but every `get_balance` call re-sorts and replays the whole
relevant log: $O(n \log n)$ for the $n$ calls at or before the query, every single time.

### Part 3

Two things make Part 2 slow under many queries: it sorts the log again on every call, and it replays
every event from the start even when the previous query's timestamp was almost the same.
`GPUCreditLedgerFast` fixes both, and is fast only on the pattern the statement targets:

- Keep the log sorted by timestamp incrementally with `bisect.insort`, instead of sorting from scratch
  on every query.
- Keep a *cursor*: the `_LedgerState` left after applying every stored event up to the highest timestamp
  queried so far. A query at or past the cursor only has to apply the events between the two.
- A query behind the cursor asks about the past. The cursor's state already contains later events and
  cannot be rewound, so such a query falls back to one full replay, as in Part 2, and leaves the cursor
  alone.
- An `add_credit`/`subtract` that lands at or behind the cursor invalidates it: the state was built
  without this event, so the cursor is dropped and rebuilt lazily by the next query.
- Answers are cached by timestamp, so asking the same timestamp again is a dictionary lookup. Every
  cached timestamp is at or behind the cursor, so an event past the cursor cannot change a cached answer,
  and a late event clears the cache together with the cursor.

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

While the cursor only ever advances — non-decreasing queries, no late event — every stored event is
applied exactly once over the life of the ledger and every grant is pushed and popped at most once,
$O(U \log U)$ in total; beyond that a query is a dictionary lookup and one subtraction, for
$O(U \log U + Q)$ altogether. `bisect.insort` still costs $O(n)$ per call to shift the list; if
`add_credit`/`subtract` calls are frequent too, replace the list with a balanced tree keyed by
timestamp, such as the treap in [Memory Allocator](../memory-allocator/README.md). On 2,000
out-of-order `add_credit`/`subtract` calls followed by 20,000 non-decreasing queries, it answers the
queries faster than Part 2 by well over two orders of magnitude.

### Follow-ups

- Enforcing credit in production: check `get_balance` before starting the expensive work a request
  stands for, admit the request only if the balance covers its estimated cost, and `subtract` the actual
  cost afterwards. Letting `subtract` always succeed and run up debt is a bookkeeping choice, not a
  spending policy.
- Frequent late events: snapshot the state every so many events, so that a late event rewinds only to
  the nearest snapshot before it instead of to the start; once the log is persisted, the same snapshots
  are the recovery checkpoints.
- Reversing a `subtract`: a correct refund has to remember which grants the call drained and by how
  much, so that exactly those amounts are restored; issuing a fresh grant instead changes when the
  credit expires.
- Two events at the same `timestamp`: once that is allowed, the ledger needs an explicit tie-break as a
  secondary sort key — grants before subtracts, say, then call order.
- Rejecting a late `add_credit` instead of absorbing it: track the highest timestamp any `get_balance`
  has already answered, and raise on any `add_credit`/`subtract` landing at or before it.

<details>
<summary>Checks (runnable)</summary>

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

# amounts beyond a 32-bit range: five grants of 10**9 each, none expired by the time they are all queried
big_ops = [('add', f'big{i}', 10 ** 9, i, 100) for i in range(5)]
for cls in (GPUCreditLedger, GPUCreditLedgerAnyOrder, GPUCreditLedgerFast):
    ledger = cls()
    for op in big_ops:
        feed(ledger, op)
    got = ledger.get_balance(4)
    assert got == 5 * 10 ** 9 == reference_balance(big_ops, 4) and got > 2 ** 32, (cls.__name__, got)


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
