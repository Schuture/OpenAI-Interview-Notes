# Time-Travel Key-Value Store

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | SWE | binary-search, testing, concurrency | 4 parts |
<!-- meta:end -->

## Problem

A `TimeMap` records, for a set of string keys, the history of values a key has held over time. A
*timestamp* is a real number (an `int` or a `float`); a larger timestamp means a later point in time.
Implement the following four parts.

### Part 1 — Basic implementation

`TimeMap()` creates an empty store.

`set(key, value, timestamp)` records that, as of `timestamp`, `key` holds `value`. A key can have any
number of values recorded at different timestamps, and calls are not required to arrive in increasing
order of `timestamp` for a given key: a call with an earlier timestamp may happen after one with a later
timestamp has already been recorded.

`get(key, timestamp)` returns the value with the largest recorded timestamp that is less than or equal
to `timestamp`, among everything recorded so far for `key`. If `key` has never been passed to `set`, or
every timestamp recorded for `key` is greater than the one being queried, `get` returns `None`.

If two calls to `set` use the same `key` and exactly the same `timestamp`, the later of the two calls (in
the order `set` was invoked) is the one `get` uses for that timestamp, as if the earlier call had never
happened.

```py
from typing import Any


class TimeMap:
    def __init__(self) -> None: ...
    def set(self, key: str, value: Any, timestamp: float) -> None: ...
    def get(self, key: str, timestamp: float) -> Any | None: ...
```

Example:

```text
tm = TimeMap()
tm.set("probe-1", 68.0, 100.0)
tm.set("probe-1", 71.5, 140.0)
tm.get("probe-1", 130.0)          # -> 68.0   (the latest value recorded at or before 130.0)
tm.get("probe-1", 90.0)           # -> None   (nothing recorded yet at or before 90.0)
tm.get("probe-2", 140.0)          # -> None   (unknown key)
tm.set("probe-1", 65.0, 120.0)    # arrives after the 140.0 call, but timestamped earlier
tm.get("probe-1", 130.0)          # -> 65.0   (now the closest value at or before 130.0)
tm.set("probe-1", 70.0, 140.0)    # same timestamp as an earlier call
tm.get("probe-1", 140.0)          # -> 70.0   (the later call wins)
```

### Part 2 — Testability

Testing `TimeMap` should not depend on the real clock: a test that calls `time.time()` gets a different
timestamp on every run, and separating two calls with `time.sleep` makes the test slow.

`TimeMap`'s constructor accepts an optional *clock*: any object with a method `now() -> float`. `set` and
`get` both accept `timestamp` as optional; when it is left out (or passed as `None`), the call uses
`clock.now()` in its place. An explicit `timestamp` always overrides the clock, whether or not a clock was
injected. When no clock is given, `TimeMap` falls back to one that calls the real `time.time()`.

Tests use the following manual clock, which never touches the real time:

```python
class ManualClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, dt: float) -> None:
        self._now += dt   # dt may be negative: this simulates the clock moving backward
```

```py
class TimeMap:
    def __init__(self, clock: Any = None) -> None: ...
    def set(self, key: str, value: Any, timestamp: float | None = None) -> None: ...
    def get(self, key: str, timestamp: float | None = None) -> Any | None: ...
```

Example:

```text
clock = ManualClock(start=1000.0)
tm = TimeMap(clock=clock)
tm.set("probe-1", 68.0)            # timestamp defaults to clock.now() == 1000.0
clock.advance(40.0)
tm.set("probe-1", 71.5)            # timestamp defaults to clock.now() == 1040.0
tm.get("probe-1")                  # timestamp defaults to clock.now() == 1040.0 -> 71.5
tm.get("probe-1", 1000.0)          # an explicit timestamp overrides the clock -> 68.0
```

### Part 3 — Keeping timestamps strictly increasing

From this part on, the timestamp recorded for a given key must be strictly increasing. For a key `key`,
let `last(key)` be the largest timestamp recorded for it so far (undefined before its first `set`). When
`set(key, value, timestamp)` is called — whether `timestamp` was passed explicitly or came from
`clock.now()` — the timestamp that ends up recorded is:

- `timestamp` itself, if `last(key)` is undefined or `timestamp` is strictly greater than `last(key)`;
- `last(key) + 1` otherwise — this covers both the clock moving backward and an explicit `timestamp` that
  is not larger than the last one recorded for that key.

This constraint, and that adjustment, apply independently to each key; a key with few writes is not
compared against a key with many. This replaces the two Part 1 rules for a call whose timestamp is not
larger than the previous one recorded for that key: such a call is no longer inserted before an existing
entry, and no longer overwrites an entry at the same timestamp — it is always appended, at whichever
timestamp this rule computes. From this part on, `set` returns the timestamp it actually recorded, which
may differ from the `timestamp` argument.

```py
class TimeMap:
    def __init__(self, clock: Any = None) -> None: ...
    def set(self, key: str, value: Any, timestamp: float | None = None) -> float: ...
    def get(self, key: str, timestamp: float | None = None) -> Any | None: ...
```

Example:

```text
clock = ManualClock(start=100.0)
tm = TimeMap(clock=clock)
tm.set("probe-1", 68.0)            # -> 100.0   (clock.now())
tm.set("probe-1", 70.0, 100.0)     # explicit 100.0 is not greater than last (100.0) -> recorded at 101.0
tm.get("probe-1", 100.0)           # -> 68.0    (100.0 still holds the first value)
tm.get("probe-1", 101.0)           # -> 70.0
clock.advance(-50.0)               # the clock moves backward: now() == 50.0
tm.set("probe-1", 65.0)            # 50.0 is not greater than last (101.0) -> recorded at 102.0
tm.get("probe-1", 102.0)           # -> 65.0
```

### Part 4 — Concurrent access

Multiple threads may call `set` and `get` on the same store at the same time, for the same key or for
different keys, in any interleaving and under any scheduling. Implement `ThreadSafeTimeMap`, offering the
same `set`/`get` semantics as Part 3's `TimeMap` (including the strictly-increasing rule), plus the
following three guarantees, which must hold for any number of threads and any scheduling:

1. Every call to `set` or `get` behaves as if it took effect at a single instant, and a call that omits
   `timestamp` reads `clock.now()` at that instant: the store's internal state is never left inconsistent
   (for a given key, the recorded timestamps stay strictly increasing, and there are exactly as many
   recorded timestamps as recorded values), and no call raises an exception caused only by another
   thread's concurrent call.
2. Every value returned by `get(key, ...)` is either `None` or exactly the `value` argument of some `set`
   call on `key` — never a value paired with a timestamp that a different `set` call recorded.
3. Part 3's strictly-increasing rule still holds when several threads call `set` for the same key at the
   same time: whichever order their calls actually take effect in, the sequence of timestamps recorded for
   that key stays strictly increasing.

Implement and compare at least two locking strategies: one lock shared by the whole store, and one lock
per key, created the first time that key is touched. If you also consider a read/write lock that lets
concurrent `get` calls run together, say whether it would actually help here.

```py
class ThreadSafeTimeMap:
    def __init__(self, clock: Any = None) -> None: ...
    def set(self, key: str, value: Any, timestamp: float | None = None) -> float: ...
    def get(self, key: str, timestamp: float | None = None) -> Any | None: ...
```

Example:

```text
Thread A: set("probe-1", 71.5)     # no explicit timestamp; clock.now() == 1040.0 for both threads
Thread B: set("probe-1", 69.0)     # A and B run at the same time, in either order

# Whichever call actually takes effect first, "probe-1" ends up with two strictly increasing
# timestamps, e.g. 1040.0 and 1041.0 -- never two entries at 1040.0.
get("probe-1", 1041.0)  # -> 71.5 or 69.0, whichever of A/B took effect second, never anything else
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming with the interviewer before coding: what `get` returns when nothing matches
(here `None` rather than an empty string, since a value need not be a string); and whether "strictly
increasing" holds per key or globally (here per key, since unrelated keys have no reason to block each
other's writes).

### Part 1

Each key maps to two parallel lists kept in increasing order of timestamp: `_timestamps` and `_values`.
`set` uses `bisect_left` to find where `timestamp` belongs — if an entry already sits there, it is
overwritten (the later call wins); otherwise a new entry is inserted at that position, which is how a
timestamp arriving late still lands in the right place. `get` uses `bisect_right`, not `bisect_left`: with
an exact match at `timestamp`, `get` must still include it, so the answer sits at index `i - 1`, one before
where `bisect_right` would insert a value equal to `timestamp`.

```python
import bisect
from typing import Any


class TimeMap:
    def __init__(self) -> None:
        self._timestamps: dict[str, list[float]] = {}
        self._values: dict[str, list[Any]] = {}

    def set(self, key: str, value: Any, timestamp: float) -> None:
        timestamps = self._timestamps.setdefault(key, [])
        values = self._values.setdefault(key, [])
        i = bisect.bisect_left(timestamps, timestamp)
        if i < len(timestamps) and timestamps[i] == timestamp:
            values[i] = value               # NOTE: same timestamp as an existing entry -- the later call wins
        else:
            timestamps.insert(i, timestamp)
            values.insert(i, value)

    def get(self, key: str, timestamp: float) -> Any | None:
        timestamps = self._timestamps.get(key)
        if not timestamps:
            return None
        i = bisect.bisect_right(timestamps, timestamp)  # NOTE: not bisect_left -- an exact match still counts
        return self._values[key][i - 1] if i > 0 else None
```

`get` is $O(\log n)$ in the number of values recorded for `key`; `set` is $O(n)$ because `timestamps.insert`
and `values.insert` both shift the tail of the list.

```python
tm = TimeMap()
tm.set("probe-1", 68.0, 100.0)
tm.set("probe-1", 71.5, 140.0)
assert (tm.get("probe-1", 130.0), tm.get("probe-1", 90.0), tm.get("probe-2", 140.0)) == (68.0, None, None)
tm.set("probe-1", 65.0, 120.0)
assert tm.get("probe-1", 130.0) == 65.0
tm.set("probe-1", 70.0, 140.0)
assert tm.get("probe-1", 140.0) == 70.0
```

### Part 2

`set`/`get` reach for the clock exactly when `timestamp` is `None`; an
explicit `timestamp` of `0` or `0.0` is a real value, not "missing", which is why the check is `is None`
and not a falsiness check. From here on, each part *subclasses* the previous one under the same name
`TimeMap`, overriding only what changes and delegating to `super()` for the rest, so Part 1's `bisect`
logic is written once and reused, not repeated.

```python
import time


class RealClock:
    def now(self) -> float:
        return time.time()


class TimeMap(TimeMap):
    def __init__(self, clock: Any = None) -> None:
        super().__init__()
        self._clock = clock if clock is not None else RealClock()

    def set(self, key: str, value: Any, timestamp: float | None = None) -> None:
        super().set(key, value, self._clock.now() if timestamp is None else timestamp)

    def get(self, key: str, timestamp: float | None = None) -> Any | None:
        return super().get(key, self._clock.now() if timestamp is None else timestamp)
```

```python
clock = ManualClock(start=1000.0)
tm = TimeMap(clock=clock)
tm.set("probe-1", 68.0)
clock.advance(40.0)
tm.set("probe-1", 71.5)
assert tm.get("probe-1") == 71.5
assert tm.get("probe-1", 1000.0) == 68.0
```

### Part 3

Once every recorded timestamp for a key is guaranteed larger than the one before it, `set` no longer needs
`bisect_left` plus `list.insert` — the new entry is always the last one, so a plain `append` is enough,
turning the per-call cost from $O(n)$ into $O(1)$ amortized. `get` needs no change: the inherited one still
works, because the two lists stay sorted.

Rejecting a non-increasing timestamp with an exception instead would keep every recorded timestamp a
genuine clock reading, but leave the retry-or-drop decision to the caller. The `last(key) + 1` rule never
rejects a write, but the 1 is one unit of whatever the clock counts, a whole second with `time.time()`.
After the clock moves back, a key written more than once per unit is nudged on every write and runs ever
further ahead of the clock instead of catching up, and a `get` that omits `timestamp` queries at
`clock.now()`, so it misses those writes until the clock catches up. Counting in the clock's finest unit
(integer nanoseconds from `time.time_ns()`) makes each nudge negligible, so the clock does catch up.

```python
class TimeMap(TimeMap):
    def __init__(self, clock: Any = None) -> None:
        super().__init__(clock)
        self._last: dict[str, float] = {}

    def set(self, key: str, value: Any, timestamp: float | None = None) -> float:
        if timestamp is None:
            timestamp = self._clock.now()
        last = self._last.get(key)
        if last is not None and timestamp <= last:  # NOTE: a backward clock and a stale explicit timestamp
            timestamp = last + 1                     #      both land here
        self._timestamps.setdefault(key, []).append(timestamp)  # NOTE: append -- timestamp now exceeds all earlier
        self._values.setdefault(key, []).append(value)
        self._last[key] = timestamp
        return timestamp
```

```python
clock = ManualClock(start=100.0)
tm = TimeMap(clock=clock)
assert tm.set("probe-1", 68.0) == 100.0
assert tm.set("probe-1", 70.0, 100.0) == 101.0
assert tm.get("probe-1", 100.0) == 68.0
assert tm.get("probe-1", 101.0) == 70.0
clock.advance(-50.0)
assert tm.set("probe-1", 65.0) == 102.0
assert tm.get("probe-1", 102.0) == 65.0
```

### Part 4

Making `set` thread-safe means locking the *whole* read-modify-write sequence — read `last(key)`, decide
whether to nudge, append, update `last(key)` — not just the individual dictionary or list calls inside it:
CPython's GIL never interrupts a single bytecode, but it can switch threads between any two of them, and
"read `last`, then write it back" leaves exactly such a gap: two threads that both read `last(key)` as
100.0, each with a clock reading of 100.0, both record 101.0.

Both locking strategies subclass Part 3's `TimeMap` again and only wrap `super().set` and `super().get` in
a lock, so what is protected is the sequence already written in Part 3, and `clock.now()` is read inside
the lock too. Read before waiting for the lock, a call that read the clock first could reach the lock
second, and would then be nudged to `last(key) + 1` although the clock never moved back. The simpler
strategy, `GlobalLockTimeMap`, uses one `threading.Lock` for the whole store, which makes an update to
`"probe-1"` wait behind an unrelated update to `"probe-2"`.

Giving each key its own lock removes that, but creating a key's lock is itself a read-modify-write ("is
there one already? if not, make one"), so it needs a small lock of its own, held only while it is created
or looked up. The attributes inherited from `TimeMap` stay shared without a lock of their own: a single
`dict.get`/`setdefault` call cannot be interrupted mid-call, only a sequence of several such calls can,
and the per-key lock is exactly what protects that sequence.

```python
import threading


class PerKeyLockTimeMap(TimeMap):
    def __init__(self, clock: Any = None) -> None:
        super().__init__(clock)
        self._key_locks: dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._registry_lock:  # NOTE: guards only the creation of a key's lock, not the operation under it
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
        return lock

    def set(self, key: str, value: Any, timestamp: float | None = None) -> float:
        with self._lock_for(key):  # NOTE: a missing timestamp is read from the clock in here, by Part 3's set
            return super().set(key, value, timestamp)

    def get(self, key: str, timestamp: float | None = None) -> Any | None:
        with self._lock_for(key):  # NOTE: get needs it too -- set appends the timestamp before the value
            return super().get(key, timestamp)


ThreadSafeTimeMap = PerKeyLockTimeMap
```

| | different keys | same key, several `get` | building the lock |
| --- | --- | --- | --- |
| one global lock | block each other | block each other | nothing to build |
| one lock per key | run independently | block each other | needs its own lock |
| read/write lock per key | run independently | run together | stdlib has none to build on |

A read/write lock would let several `get` calls on one key hold the lock together, but each holds it only
for an $O(\log n)$ bisect, and under the GIL two threads never execute bytecode at the same instant anyway,
so a correct one (the standard library ships none) would only add code and overhead. It pays off when the
locked section does work that can overlap, such as I/O, or on an interpreter without a GIL.

```python
tm = ThreadSafeTimeMap(clock=ManualClock(start=1040.0))
threads = [threading.Thread(target=tm.set, args=("probe-1", v)) for v in (71.5, 69.0)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert {tm.get("probe-1", 1040.0), tm.get("probe-1", 1041.0)} == {71.5, 69.0}
```

### Follow-ups

- Answering `get(key, t1, t2)` for a whole range needs two bisects to locate both ends, not a fresh scan
  of the key's whole history.
- To survive a restart, append every write to a log, with the timestamp it was actually recorded at, before
  applying it in memory, and replay the log on startup.
- Across machines, no clock is exactly synchronized; a hybrid logical clock keeps the largest physical time
  seen so far plus a separate counter for ties, so it orders causally related events correctly and, unlike
  the `+1` nudge, never runs ahead of the fastest physical clock.

<details>
<summary>Checks (runnable)</summary>

`GlobalLockTimeMap`, the single-lock strategy of Part 4, in full: every call wrapped in one shared lock.

```python
import threading


class GlobalLockTimeMap(TimeMap):
    def __init__(self, clock: Any = None) -> None:
        super().__init__(clock)
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, timestamp: float | None = None) -> float:
        with self._lock:
            return super().set(key, value, timestamp)

    def get(self, key: str, timestamp: float | None = None) -> Any | None:
        with self._lock:
            return super().get(key, timestamp)
```

An independent reading of the statement, built without calling anything from `TimeMap`: every `set` call
is kept, in call order, in one list per key; with `nudge` on, `set` applies Part 3's rule, taking
`last(key)` as the largest timestamp in that list, and `get` scans the list for the largest timestamp at
or below the query, the later call winning a tie. It is compared with Part 2's class and with the three
classes that follow Part 3's rule.

```python
import random
from collections import Counter


class NaiveTimeMap:
    def __init__(self, clock: Any, nudge: bool) -> None:
        self.entries: dict[str, list[tuple[float, Any]]] = {}   # every set call, in call order
        self.clock, self.nudge = clock, nudge

    def set(self, key: str, value: Any, timestamp: float | None = None) -> float:
        if timestamp is None:
            timestamp = self.clock.now()
        earlier = [t for t, _ in self.entries.get(key, [])]
        if self.nudge and earlier and timestamp <= max(earlier):
            timestamp = max(earlier) + 1
        self.entries.setdefault(key, []).append((timestamp, value))
        return timestamp

    def get(self, key: str, timestamp: float | None = None) -> Any | None:
        if timestamp is None:
            timestamp = self.clock.now()
        best = None
        for t, v in self.entries.get(key, []):
            if t <= timestamp and (best is None or t >= best[0]):   # >=: the later of two equal timestamps wins
                best = (t, v)
        return best[1] if best is not None else None


def cross_check(cls, nudge, seed, n_ops=200):
    rng = random.Random(seed)
    clock = ManualClock(start=10.0)
    real, naive = cls(clock=clock), NaiveTimeMap(clock, nudge)
    counts = Counter()
    for _ in range(n_ops):
        key = rng.choice(["probe-1", "probe-2", "probe-3", "never-set"])
        ts = rng.choice([None, None, 0, 1, 2, 2.5, 3, 5, 10])
        pick = rng.random()
        if pick < 0.15:
            clock.advance(rng.choice([-5, -2, -1, 0, 1, 2, 3, 7]))
        elif pick < 0.6 and key != "never-set":
            value, t = rng.randint(0, 999), clock.now() if ts is None else ts
            earlier = [e for e, _ in naive.entries.get(key, [])]
            counts["same timestamp"] += t in earlier                 # Part 2: overwrite; Part 3: nudge
            counts["earlier timestamp"] += bool(earlier) and t < max(earlier)
            got, want = real.set(key, value, ts), naive.set(key, value, ts)
            assert not nudge or got == want, (cls, seed, key, ts, got, want)
        else:
            got, want = real.get(key, ts), naive.get(key, ts)
            assert got == want, (cls, seed, key, ts, got, want)
            counts["unknown key" if key == "never-set" else "before first" if want is None else "found"] += 1
    return counts


classes = {"Part 2": (TimeMap.__bases__[0], False),       # the class Part 3's TimeMap subclasses
           "Part 3": (TimeMap, True), "per-key lock": (ThreadSafeTimeMap, True), "global lock": (GlobalLockTimeMap, True)}
for name, (cls, nudge) in classes.items():
    totals = sum((cross_check(cls, nudge, seed) for seed in range(300)), Counter())
    assert len(totals) == 5 and min(totals.values()) > 100, (name, totals)   # every case fired repeatedly
    print(name, dict(totals))
```

A thread switch forced into every read-modify-write gap, instead of waiting for the scheduler to land in
one: `time.sleep(0)` releases the GIL, so after `YieldingDict.get` or `setdefault` has read, another thread
runs before the caller uses what it read. Part 3's `TimeMap`, and a per-key-lock variant whose lock
registry is not guarded, break a guarantee in almost every trial (a repeated timestamp, or a `get` that
finds a timestamp whose value is not appended yet and raises `IndexError`); the two locked classes never do.

```python
import sys


class YieldingDict(dict):
    def get(self, key, default=None):
        found = super().get(key, default)
        time.sleep(0)   # releases the GIL: another thread runs before the caller acts on `found`
        return found

    def setdefault(self, key, default=None):
        found = super().setdefault(key, default)
        time.sleep(0)
        return found


class UnguardedPerKeyLock(PerKeyLockTimeMap):
    def _lock_for(self, key: str) -> threading.Lock:
        lock = self._key_locks.get(key)   # the same check-then-create, without the registry lock
        if lock is None:
            lock = threading.Lock()
            self._key_locks[key] = lock
        return lock


def forced_race(cls, n_threads=12):
    tmap = cls(clock=ManualClock(start=100.0))
    for name in ("_last", "_values", "_key_locks"):   # a thread switch inside every read-modify-write gap
        setattr(tmap, name, YieldingDict())
    barrier, errors = threading.Barrier(n_threads), []

    def worker(i):
        barrier.wait()
        try:
            if i % 2:
                tmap.set("probe-1", i)
            else:
                for _ in range(10):
                    tmap.get("probe-1", 1e9)   # may run between another thread's two appends
                    time.sleep(0)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ts = tmap._timestamps["probe-1"]
    return bool(errors) or any(a >= b for a, b in zip(ts, ts[1:]))   # True: a guarantee is broken


broken = {cls.__name__: sum(forced_race(cls) for _ in range(20))
          for cls in (TimeMap, UnguardedPerKeyLock, ThreadSafeTimeMap, GlobalLockTimeMap)}
print("trials out of 20 that broke a guarantee:", broken)
assert broken["TimeMap"] >= 15 and broken["UnguardedPerKeyLock"] >= 15, broken
assert broken["PerKeyLockTimeMap"] == broken["GlobalLockTimeMap"] == 0, broken
```

A stress test with unforced scheduling: `sys.setswitchinterval(1e-6)` makes a waiting thread force a
switch after 1 µs instead of 5 ms, so the threads really interleave. `TickingClock` never repeats or goes
back, so a store that reads it at the instant each call takes effect never nudges; a recorded timestamp
that is not one of its readings means a call acted on a stale reading, such as one taken before waiting
for the lock. How often unforced scheduling hits a gap depends on how busy the machine is, so this test
only asserts that the two locked classes pass; the forced version above is what shows a missing lock is
caught.

```python
import itertools


class TickingClock:
    def __init__(self) -> None:
        self._ticks = itertools.count(1)   # next() on a counter is atomic, so no two readings are equal

    def now(self) -> float:
        return 1000.0 * next(self._ticks)   # every reading is larger than the one before


def stress(cls, n_threads=16, ops_per_thread=300, n_keys=5, timeout=15):
    """Runs threads against one store; returns a count of each guarantee seen violated (empty if none)."""
    tmap = cls(clock=TickingClock())
    keys = [f"probe-{i}" for i in range(n_keys)]
    recorded, got, errors = {}, [], []   # recorded: value -> (key, the timestamp set() returned)

    def worker(tid):
        rng = random.Random(tid)
        try:
            for i in range(ops_per_thread):
                key = rng.choice(keys)
                if rng.random() < 0.6:
                    recorded[(tid, i)] = (key, tmap.set(key, (tid, i)))
                else:
                    got.append((key, tmap.get(key)))
        except Exception as e:
            errors.append(repr(e))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout)
        if t.is_alive():
            return Counter(["a worker did not finish -- possible deadlock"])
    problems = ["exception"] * len(errors)
    problems += ["get() returned a value never set on that key" for k, v in got
                 if v is not None and recorded.get(v, (None,))[0] != k]
    for key in keys:
        pairs = list(zip(tmap._timestamps.get(key, []), tmap._values.get(key, [])))
        ts = [t for t, _ in pairs]
        if pairs != sorted((t, v) for v, (k, t) in recorded.items() if k == key):
            problems.append("stored (timestamp, value) pairs differ from what set() returned")
        if any(a >= b for a, b in zip(ts, ts[1:])):
            problems.append("timestamps not strictly increasing")
        if any(t % 1000 for t in ts):
            problems.append("nudged to last + 1 although the clock only moves forward")
    return Counter(problems)


old_interval = sys.getswitchinterval()
sys.setswitchinterval(1e-6)   # at the default 5 ms, each worker mostly runs alone
try:
    for cls in (ThreadSafeTimeMap, GlobalLockTimeMap):
        problems = stress(cls)
        assert not problems, (cls.__name__, problems)
finally:
    sys.setswitchinterval(old_interval)
print("concurrency stress checks passed")
```

</details>

</details>
