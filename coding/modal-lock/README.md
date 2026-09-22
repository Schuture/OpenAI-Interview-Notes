# ModalLock and FairModalLock

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding · concurrency, Python | ★☆☆☆☆ | Hard | SWE · MLE | concurrency, threading, fairness | 2 parts |
<!-- meta:end -->

## Problem

A *mode* is a string that names how a shared resource is being used at a given moment -- for example,
whether a GPU is currently running `"train"` jobs or `"infer"` jobs. `ModalLock` protects such a
resource: at any instant, every thread holding the lock is using the same mode, and any number of
threads may hold it together as long as they all ask for that one mode. A thread that asks for a
different mode than the one currently held must block until every current holder has released.

The examples below are given in terms of a small tool, `Rig`, that drives a lock through an exact,
chosen sequence of arrivals and releases without depending on sleeps or timing: every step blocks until
its effect on the lock is actually visible, using `waiting_count()` -- the number of `acquire()` calls
currently blocked, across every mode -- as the signal that a call has genuinely parked rather than been
granted immediately.

```python
import threading
import time


def wait_until(predicate, timeout=5.0):
    """Block until predicate() is true. The timeout only guards against a real deadlock; it plays
    no role when the lock behaves correctly, so it does not make the check timing-dependent."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for the lock to reach the expected state (deadlock?)")
        time.sleep(0.0005)


class _Waiter:
    def __init__(self, mode):
        self.mode = mode
        self.acquired = threading.Event()
        self.go_release = threading.Event()
        self.released = threading.Event()


class Rig:
    """name -> a dedicated thread that calls lock.acquire(mode) as soon as it is told to arrive,
    and lock.release(mode) as soon as it is told to release."""

    def __init__(self, lock):
        self.lock = lock
        self._w: dict[str, _Waiter] = {}

    def arrive(self, name, mode):
        """Start thread `name`, which calls acquire(mode) immediately. Returns only once that call
        has either been granted, or is genuinely parked inside acquire() -- so the caller's next
        step is guaranteed to happen strictly after this arrival, in program order."""
        w = _Waiter(mode)
        self._w[name] = w
        threading.Thread(target=self._run, args=(w,), daemon=True).start()
        wait_until(lambda: w.acquired.is_set() or self._parked(w))

    def _parked(self, w):
        # NOTE: count the other not-yet-granted calls BEFORE reading waiting_count(). That count can
        # only shrink meanwhile (a call woken by an earlier release may still be on its way out of
        # acquire()), so a waiting_count() above it can only come from w itself having parked.
        others = sum(1 for v in self._w.values() if v is not w and not v.acquired.is_set())
        return self.lock.waiting_count() > others

    def release(self, name):
        """Have `name` call release(mode) now. Returns once that call has returned."""
        w = self._w[name]
        w.go_release.set()
        wait_until(lambda: w.released.is_set())

    def holders(self):
        """The names whose acquire() has returned and whose release() has not."""
        return frozenset(n for n, w in self._w.items() if w.acquired.is_set() and not w.released.is_set())

    def _run(self, w):
        self.lock.acquire(w.mode)
        w.acquired.set()
        w.go_release.wait()
        self.lock.release(w.mode)
        w.released.set()
```

### Part 1 — ModalLock

`acquire(mode)` blocks until the lock's current mode is either absent (the lock is idle) or equal to
`mode`, then makes `mode` the current mode and adds the caller to the set of holders. `release(mode)`
removes the caller from that set; once the last holder of the current mode releases, the lock becomes
idle again. `release(mode)` raises `ModeMismatchError` when the lock currently has no holders at all, or
when its current mode is not `mode` -- both mean this call does not correspond to any reservation it
actually holds.

```py
class ModalLock:
    def __init__(self) -> None: ...
    def acquire(self, mode: str) -> None: ...
    def release(self, mode: str) -> None: ...
    def waiting_count(self) -> int: ...
```

Example, with a fresh `ModalLock` and threads `a, b, c, d`: `a` requests `"train"` (granted at once);
`b` requests `"train"` (joins `a`); `c` requests `"infer"` (blocks, `"train"` is held); `a` releases
(`b` still holds `"train"`, so `c` keeps blocking); `b` releases (`"train"` drains to zero, `c` is
granted `"infer"`); `d` requests `"infer"` (joins `c`). The holder set after each of these six steps is,
in order: `{a}`, `{a, b}`, `{a, b}`, `{b}`, `{c}`, `{c, d}`.

### Part 2 — FairModalLock

`ModalLock` can starve a mode forever: as long as the current mode keeps gaining new same-mode holders
before its last one releases, the lock is never idle, so a waiter for a different mode never gets a
turn. `FairModalLock` grants modes in the order their requests arrived, by the following rule.

Every call to `acquire(mode)` joins a *batch*: a run of consecutively-arrived, same-mode requests that
are served together. Batches sit in a single FIFO queue, oldest first, and the batch that currently
holds the lock stays at the front of that queue. A call that finds the queue's *last* batch asking for
`mode` joins that batch, even if it is the batch currently holding the lock; otherwise it starts a new
batch at the back of the queue. A batch is served -- every one of its members becomes a holder -- as
soon as it reaches the *front* of the queue, and a call that joins the front batch becomes a holder at
once. The front batch leaves the queue once every member that ever joined it has released, and the next
batch (if any) is served. So `acquire(mode)` returns at once on an idle lock, and also while the lock is
held in `mode` with nothing queued behind the holders; but once a request for another mode is waiting, a
new `acquire(mode)` queues behind it even though `mode` is the mode currently held. `release(mode)`
raises `ModeMismatchError` under the same conditions as `ModalLock.release`: the lock has no holders at
all, or its holders are not using `mode`.

```py
class FairModalLock:
    def __init__(self) -> None: ...
    def acquire(self, mode: str) -> None: ...
    def release(self, mode: str) -> None: ...
    def waiting_count(self) -> int: ...
```

The first three scenarios below use only two modes; each column after "Arrivals" happens after every
earlier column, and the last column lists the batches in the order they run, each as the set of names
that hold the lock together.

| Scenario | Arrivals (name:mode) | Releases | Batches |
| --- | --- | --- | --- |
| Basic fairness | a:train, b:infer, c:train | a, b, c | `{a}`, `{b}`, `{c}` |
| Staggered arrivals | a:train, b:infer, c:train, d:infer, e:train | a, b, c, d, e | `{a}`, `{b}`, `{c}`, `{d}`, `{e}` |
| Same-mode burst | a:train, then b:infer, c:infer, d:infer | a, then b, c, d | `{a}`, `{b, c, d}` |

In the basic-fairness row, `c` requests the same mode as `a` but must not join `a`'s already-running
batch, because `b` is already queued behind it; `c` waits its own turn behind `b`. In the same-mode-burst
row, all three `"infer"` arrivals queue up while `"train"` is held, then all three become holders
together the instant `a` releases.

A third mode makes the "no cutting in line" rule visible with modes on both sides of the queue at once.
With a fresh `FairModalLock`: `a` requests `"train"` (granted); `b` requests `"infer"` (queues); `c`
requests `"export"` (queues); `d` requests `"infer"` (queues -- the queue's last batch is `c`'s
`"export"` batch, so `d` cannot join `b`); `a` releases (`b`'s batch runs, holders `{b}`); `e` requests
`"infer"` (the queue's last batch is now `d`'s, so `e` joins `d`, not `b`); `b` releases (`c`'s batch
runs, holders `{c}`); `c` releases (`d`'s batch runs together with `e`, holders `{d, e}`); `d` and `e`
release. The batches run in the order `{a}`, `{b}`, `{c}`, `{d, e}`.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming with the interviewer: whether `acquire` needs a timeout or a way to cancel a
pending wait (assumed not, to keep the interface small), and whether a mode string carries any meaning
beyond equality (assumed not; it is only ever compared with `==`).

### Part 1

A single `Condition` guards a triple: the current mode, the number of holders, and the number of callers
parked in `wait()`. `waiting_count()` reports the last of these. An observer sees a call counted from
the moment it enters `wait()` until it is granted: a call that is granted without blocking increments
and decrements the count without ever releasing the condition's lock in between, so no outside observer
can see the value change.

```python
import threading
from collections import deque


class ModeMismatchError(RuntimeError):
    """release(mode) does not match a reservation this call actually holds."""


class ModalLock:
    def __init__(self):
        self._cond = threading.Condition()
        self._mode = None          # current mode, or None when idle
        self._holders = 0
        self._waiting = 0          # calls parked in wait(), across every mode

    def acquire(self, mode):
        with self._cond:
            self._waiting += 1
            try:
                # NOTE: while, not if -- notify_all() wakes the parked callers of every mode at once;
                # by the time this one gets back in, another may already hold the lock in its mode
                while self._mode is not None and self._mode != mode:
                    self._cond.wait()
            finally:
                self._waiting -= 1
            self._mode = mode
            self._holders += 1

    def release(self, mode):
        with self._cond:
            if self._holders == 0 or self._mode != mode:      # NOTE: checked before any state is
                raise ModeMismatchError(mode)                   #  touched, so a bad call leaves
            self._holders -= 1                                  #  nothing to undo; the `with` block
            if self._holders == 0:                               #  still releases the underlying
                self._mode = None                                 #  mutex on the way out either way
                self._cond.notify_all()   # NOTE: notify_all, not notify -- notify() wakes one
                                            # caller, and the others parked for that same mode
                                            # would stay asleep instead of joining it

    def waiting_count(self):
        with self._cond:
            return self._waiting
```

`ModalLock` starves a mode whenever the current mode never fully drains. With `Rig`, this needs no luck
at all: an `"infer"` request is made to arrive first and park; then, repeatedly, a fresh `"train"`
request arrives *before* the previous `"train"` holder releases, so `_holders` never reaches zero and
`notify_all()` is never called -- the parked `"infer"` call cannot possibly wake up.

```python
lock = ModalLock()
rig = Rig(lock)
rig.arrive('w0', 'train')
rig.arrive('starved', 'infer')
wait_until(lambda: lock.waiting_count() == 1)
for i in range(1, 8):
    rig.arrive(f'w{i}', 'train')      # joins the still-current 'train' mode at once
    rig.release(f'w{i - 1}')          # 'train' loses a holder but never empties
    wait_until(lambda: rig.holders() == frozenset({f'w{i}'}))
    assert lock.waiting_count() == 1  # 'starved' is still parked
rig.release('w7')
wait_until(lambda: rig.holders() == frozenset({'starved'}))   # only now does it get a turn
rig.release('starved')
```

### Part 2

`_Batch` records one queue entry: its mode, how many calls are still parked in it, and how many of its
members currently hold the lock. `acquire` only ever inspects the *last* batch in the queue to decide
whether to join it -- checking "does a batch of this mode exist anywhere" instead would let a same-mode latecomer
cut in front of whatever is already queued behind the running batch, breaking fairness. A call is
granted the moment its own batch reaches the front (`_queue[0] is batch`); this condition already covers
both the idle-lock case (an empty queue with one freshly appended batch is trivially at the front) and
the join-the-running-batch case (the batch stays at index 0 while active), so no separate fast path is
needed. `release` removes the front batch only once both of its counts are zero: a member woken when
its batch reached the front may not have re-entered the condition yet (`active == 0` while
`waiting > 0`), and removing the batch under it would leave that member waiting for a batch that is no
longer in the queue. Calling `notify()` instead of `notify_all()` here hangs the lock whenever a batch
reaches the front with two or more members parked: `notify()` wakes just one of them, and once that one
releases, the batch has `active == 0` but `waiting > 0`, so it is not removed and nothing calls `notify`
again -- the remaining members, and every batch behind them, wait forever.

```python
class _Batch:
    __slots__ = ("mode", "waiting", "active")

    def __init__(self, mode):
        self.mode = mode
        self.waiting = 0    # calls blocked in acquire(), not yet granted
        self.active = 0     # calls granted from this batch, not yet released


class FairModalLock:
    def __init__(self):
        self._cond = threading.Condition()
        self._queue = deque()     # deque[_Batch]; index 0 is served first (or already running)

    def acquire(self, mode):
        with self._cond:
            if self._queue and self._queue[-1].mode == mode:   # NOTE: only the TAIL is checked --
                batch = self._queue[-1]                          # an older same-mode batch is off limits
            else:
                batch = _Batch(mode)
                self._queue.append(batch)
            batch.waiting += 1
            while self._queue[0] is not batch:      # NOTE: while, not if -- see ModalLock.acquire
                self._cond.wait()
            batch.waiting -= 1
            batch.active += 1

    def release(self, mode):
        with self._cond:
            batch = self._queue[0] if self._queue else None
            if batch is None or batch.mode != mode or batch.active == 0:
                raise ModeMismatchError(mode)
            batch.active -= 1
            if batch.active == 0 and batch.waiting == 0:    # NOTE: a woken member may not be back yet
                self._queue.popleft()
                self._cond.notify_all()

    def waiting_count(self):
        with self._cond:
            return sum(batch.waiting for batch in self._queue)
```

Once a batch is in the queue, every batch ahead of it has stopped being the tail, so none of them gains
another member: each has a fixed, finite set of members. As long as every holder eventually calls
`release` (the only assumption this needs), the front batch therefore empties and is removed, then the
next one, so every batch reaches the front after finitely many others and no mode can be locked out
forever -- unlike `ModalLock`, where a batch's own members joining forever is exactly what keeps a
*different* batch waiting.

### Follow-ups

- A reader/writer lock is the special case with two fixed modes, `"read"` and `"write"`, plus the extra
  rule that a `"write"` batch may never have more than one member.
- Supporting `acquire(mode, timeout)` needs a call that times out to remove itself from its batch (or
  from a freshly-created one it started alone) before returning, instead of just abandoning its `wait()`.
- An `asyncio` version replaces `Condition.wait()` with `await condition.wait()`; the single-threaded
  event loop makes every state change between one `await` and the next atomic by construction.
- Across processes, `threading.Condition` will not do, since it lives in one process's memory; a
  `multiprocessing.Condition` with the mode and queue kept in shared memory, or an external coordinator
  such as a database row lock, would need to play the same role.
- Serving modes by priority instead of strict arrival order reintroduces starvation for low-priority
  modes unless it is combined with aging, the same trade-off `ModalLock` itself makes.

<details>
<summary>Checks (runnable)</summary>

```python
import random
from collections import Counter


def expected_holders(events):
    """Recomputes, after each event, which names the fairness rule says should be holding the
    lock -- from the rule text alone, with its own batch bookkeeping, never calling FairModalLock."""
    queue = []  # list of [mode, set(names)], oldest batch first
    results = []
    for kind, *rest in events:
        if kind == 'arrive':
            name, mode = rest
            if queue and queue[-1][0] == mode:
                queue[-1][1].add(name)
            else:
                queue.append([mode, {name}])
        else:
            (name,) = rest
            for _, members in queue:
                members.discard(name)
        while queue and not queue[0][1]:
            queue.pop(0)
        results.append(frozenset(queue[0][1]) if queue else frozenset())
    return results


def run_scenario(rig, steps):
    """steps: list of ('arrive', name, mode, expected) | ('release', name, expected)."""
    for step in steps:
        if step[0] == 'arrive':
            _, name, mode, expected = step
            rig.arrive(name, mode)
        else:
            _, name, expected = step
            rig.release(name)
        if expected is not None:
            wait_until(lambda: rig.holders() == expected)
            assert rig.holders() == expected, (step, rig.holders(), expected)
    return rig


# --- the five scenarios given in the statement, plus a ModalLock burst ---
run_scenario(Rig(ModalLock()), [
    ('arrive', 'a', 'train', frozenset({'a'})),
    ('arrive', 'b', 'train', frozenset({'a', 'b'})),
    ('arrive', 'c', 'infer', frozenset({'a', 'b'})),
    ('release', 'a', frozenset({'b'})),
    ('release', 'b', frozenset({'c'})),
    ('arrive', 'd', 'infer', frozenset({'c', 'd'})),
    ('release', 'c', frozenset({'d'})),
    ('release', 'd', frozenset()),
])

run_scenario(Rig(ModalLock()), [
    ('arrive', 'a', 'train', frozenset({'a'})),
    ('arrive', 'b', 'infer', frozenset({'a'})), ('arrive', 'c', 'infer', frozenset({'a'})),
    ('release', 'a', frozenset({'b', 'c'})),     # both parked 'infer' callers must be woken
    ('release', 'b', frozenset({'c'})), ('release', 'c', frozenset()),
])

run_scenario(Rig(FairModalLock()), [
    ('arrive', 'a', 'train', frozenset({'a'})),
    ('arrive', 'b', 'infer', frozenset({'a'})),
    ('arrive', 'c', 'train', frozenset({'a'})),
    ('release', 'a', frozenset({'b'})),
    ('release', 'b', frozenset({'c'})),
    ('release', 'c', frozenset()),
])

run_scenario(Rig(FairModalLock()), [
    ('arrive', 'a', 'train', frozenset({'a'})), ('arrive', 'b', 'infer', frozenset({'a'})),
    ('arrive', 'c', 'train', frozenset({'a'})), ('arrive', 'd', 'infer', frozenset({'a'})),
    ('arrive', 'e', 'train', frozenset({'a'})),
    ('release', 'a', frozenset({'b'})), ('release', 'b', frozenset({'c'})),
    ('release', 'c', frozenset({'d'})), ('release', 'd', frozenset({'e'})),
    ('release', 'e', frozenset()),
])

burst_rig = Rig(FairModalLock())
run_scenario(burst_rig, [
    ('arrive', 'a', 'train', frozenset({'a'})),
    ('arrive', 'b', 'infer', frozenset({'a'})), ('arrive', 'c', 'infer', frozenset({'a'})),
    ('arrive', 'd', 'infer', frozenset({'a'})),
])
assert burst_rig.lock.waiting_count() == 3
run_scenario(burst_rig, [('release', 'a', frozenset({'b', 'c', 'd'}))])
assert burst_rig.lock.waiting_count() == 0
for n in ('b', 'c', 'd'):
    run_scenario(burst_rig, [('release', n, None)])

run_scenario(Rig(FairModalLock()), [
    ('arrive', 'a', 'train', frozenset({'a'})), ('arrive', 'b', 'infer', frozenset({'a'})),
    ('arrive', 'c', 'export', frozenset({'a'})), ('arrive', 'd', 'infer', frozenset({'a'})),
    ('release', 'a', frozenset({'b'})),
    ('arrive', 'e', 'infer', frozenset({'b'})),
    ('release', 'b', frozenset({'c'})), ('release', 'c', frozenset({'d', 'e'})),
    ('release', 'd', frozenset({'e'})), ('release', 'e', frozenset()),
])

for err_lock in (ModalLock(), FairModalLock()):
    try:
        err_lock.release('train')
        raise AssertionError("expected ModeMismatchError")
    except ModeMismatchError:
        pass
    rig = Rig(err_lock)
    rig.arrive('x', 'train')
    try:
        err_lock.release('infer')
        raise AssertionError("expected ModeMismatchError")
    except ModeMismatchError:
        pass
    rig.release('x')

# --- randomized: independent recomputation of the fairness rule against many scripted runs ---
def random_fairness_trial(seed, cover, n_events=40):
    rng = random.Random(seed)
    lock = FairModalLock()
    rig = Rig(lock)
    modes = ["train", "infer", "export"]
    names = [f"t{i}" for i in range(16)]
    rng.shuffle(names)
    events, mode_of, next_idx = [], {}, 0

    def step():
        nonlocal next_idx
        holders_now = rig.holders()
        if next_idx < len(names) and (not holders_now or rng.random() < 0.55):
            name, mode = names[next_idx], rng.choice(modes)
            next_idx += 1
            mode_of[name] = mode
            rig.arrive(name, mode)
            events.append(('arrive', name, mode))
        elif holders_now:
            name = rng.choice(sorted(holders_now))
            rig.release(name)
            events.append(('release', name))
        else:
            return      # every name has already arrived and released
        # NOTE: settle after EVERY event, arrive or release -- skipping this after a release would
        # let the next step() read a holder set that has not caught up with a just-freed batch yet
        expected = expected_holders(events)[-1]
        wait_until(lambda: rig.holders() == expected)
        assert rig.holders() == expected, (seed, events, rig.holders(), expected)
        if events[-1][0] == 'arrive' and holders_now and mode_of[min(holders_now)] == mode:
            cover['joined the running batch' if name in expected else 'held mode, still queued'] += 1
        elif events[-1][0] == 'release' and len(expected - holders_now) >= 2:
            cover['2+ entered together'] += 1

    for _ in range(n_events):
        step()
    while rig.holders() or next_idx < len(names) or lock.waiting_count():
        step()
    return len(events)


cover = Counter()
total = sum(random_fairness_trial(seed, cover) for seed in range(150))
assert total > 3000 and len(cover) == 3 and min(cover.values()) >= 100, (total, cover)

# --- randomized stress test under real, uncontrolled concurrency ---
def stress(lock_factory, n_threads, n_rounds, require_progress, seed):
    modes = ["train", "infer", "export"]
    lock = lock_factory()
    held: dict[int, str] = {}
    book = threading.Lock()
    done = [False] * n_threads
    violations = []     # NOTE: threads only record; an assert inside a thread would just end that
    stop = threading.Event()    # thread and never fail the check -- the main thread asserts below

    def worker(idx):
        local_rng = random.Random(f"{seed}:{idx}")
        for _ in range(n_rounds):
            mode = local_rng.choice(modes)
            lock.acquire(mode)
            with book:
                held[idx] = mode
                if len(set(held.values())) > 1:                    # checked right at join time
                    violations.append(dict(held))
            if local_rng.random() < 0.5:
                time.sleep(0)                                      # yield, no timing assumption
            else:
                time.sleep(local_rng.uniform(0, 0.0008))
            with book:
                del held[idx]
            lock.release(mode)
        done[idx] = True

    def observer():                          # independent watcher, outside the worker's own logic
        while not stop.is_set():
            with book:
                if len(set(held.values())) > 1:
                    violations.append(dict(held))
            time.sleep(0.0003)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n_threads)]
    obs = threading.Thread(target=observer, daemon=True)
    for t in threads:
        t.start()
    obs.start()
    deadline = time.monotonic() + 15.0
    for t in threads:
        t.join(timeout=max(0.0, deadline - time.monotonic()))
    stop.set()
    assert not violations, violations[:3]
    if require_progress:
        assert all(done), "some thread never completed within the timeout"


for seed in range(10):
    stress(ModalLock, n_threads=16, n_rounds=30, require_progress=False, seed=seed)
    stress(FairModalLock, n_threads=16, n_rounds=30, require_progress=True, seed=seed)

print("all checks passed")
```

</details>

</details>
