# Fault-Tolerant Work Queue

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★☆☆☆☆ | Medium | Infra Eng | queue, state-machine, retry | 3 parts |
<!-- meta:end -->

## Problem

A *work queue* holds tasks that workers pull, process, and report back on. Each task is submitted with
a caller-chosen `task_id`, unique among every task ever submitted, and an opaque `payload` that the
queue never inspects. A worker is identified by a `worker_id` string.

Every public method call is atomic: no two calls are ever interleaved with each other. A task moves
through a small state machine. This part only needs three of its states:

| State | Meaning |
| --- | --- |
| `ready` | submitted, not currently held by any worker, eligible for `reserve` |
| `reserved` | held by a worker, being processed |
| `completed` | processed successfully; terminal |

### Part 1 — Reservation, completion and failure

`submit(task_id, payload)` adds a new task in the `ready` state. Raises `ValueError` if `task_id` was
already submitted.

`reserve(worker_id)` hands the calling worker, out of the tasks currently `ready`, the one that entered
`ready` earliest — first in, first out, regardless of whether a task got to `ready` by being freshly
submitted or by being returned there. It moves that task to `reserved` and returns a `Reservation`
holding `task_id`, `payload`, and a fresh *token*: a value, unique to this one act of reserving this one
task, that `complete` and `fail` must present back. Returns `None` if no task is `ready`.

`complete(task_id, token)` marks the task `completed`. This only succeeds if the task is currently
`reserved` and `token` matches the token issued by that reservation; otherwise it raises
`InvalidReservationError`. If `task_id` was never submitted, it raises `UnknownTaskError` instead.

`fail(task_id, token)` checks `token` under the exact same rule as `complete`. Once it matches, the task
goes back to `ready`, at the back of the queue. This part places no limit on how many times a task may
fail and be retried.

Reserving a task again — after it fails, or after any other event returns it to `ready` — issues a brand
new token. A token from an earlier reservation of the task never works again for `complete` or `fail`,
even in the hands of a worker that still believes it owns the task.

```py
from typing import Any, NamedTuple


class Reservation(NamedTuple):
    task_id: str
    token: object
    payload: Any


class WorkQueue:
    def __init__(self) -> None: ...
    def submit(self, task_id: str, payload: Any) -> None: ...
    def reserve(self, worker_id: str) -> "Reservation | None": ...
    def complete(self, task_id: str, token: object) -> None: ...
    def fail(self, task_id: str, token: object) -> None: ...
```

Example:

```text
q = WorkQueue()
q.submit('t1', 'build')
q.submit('t2', 'test')

r1 = q.reserve('w1')          # r1.task_id == 't1'
r2 = q.reserve('w2')          # r2.task_id == 't2'
q.complete('t1', r1.token)    # 't1' -> completed
q.fail('t2', r2.token)        # 't2' -> ready, back of the queue

r3 = q.reserve('w3')          # r3.task_id == 't2' again, with a new token
q.complete('t2', r2.token)    # raises InvalidReservationError: r2.token is stale
q.complete('t2', r3.token)    # succeeds
```

### Part 2 — Lease timeouts

A worker can crash or hang after reserving a task without ever calling `complete` or `fail`. To bound
how long a task can stay stuck, every reservation now carries a *lease*: a deadline after which it is
considered abandoned.

Time comes from a manual clock, given below; the queue never reads the system clock.

```python
class ManualClock:
    def __init__(self, start: int = 0):
        self._now = start

    def now(self) -> int:
        return self._now

    def advance(self, dt: int) -> None:
        if dt < 0:
            raise ValueError("a clock cannot move backward")
        self._now += dt
```

`WorkQueue`'s constructor now also takes `clock` (a `ManualClock`) and a positive integer
`lease_duration`. When `reserve` issues a reservation at time `t = clock.now()`, its *lease deadline* is
`t + lease_duration`; the reservation stays valid through and including that instant, and has *expired*
once `clock.now()` is strictly greater than the deadline.

There is no background thread scanning for expirations. Instead, every call to a `WorkQueue` method,
`submit` included, begins with a *reclaiming pass*: each reservation whose lease has expired by then is
ended with the same effect as if its worker had called `fail` on it at that moment, so its task re-enters
`ready` at the back of the queue. One pass handles the expired reservations one at a time, in ascending
order of lease deadline, breaking ties by ascending `task_id`. Only then does the call do its own work.

Once a reservation is reclaimed this way, its token stops working for `complete`/`fail` under the exact
same rule as Part 1 — a worker that still believes it holds the lease gets `InvalidReservationError`,
indistinguishable from having raced an explicit `fail`.

```py
class WorkQueue:
    def __init__(self, clock: "ManualClock", lease_duration: int) -> None: ...
```

Example, with `lease_duration = 5`:

```text
t=0  q.submit('t1', 'x')
t=0  rA = q.reserve('A')          # deadline = 0 + 5 = 5, valid through t=5
t=7  clock.advance(7)             # no call yet -- expiry is not detected until the next call
t=7  rB = q.reserve('B')          # reclaims t1 first (7 > 5): back to ready, then re-reserved by B
t=7  q.complete('t1', rA.token)   # raises InvalidReservationError
t=7  q.complete('t1', rB.token)   # succeeds
```

### Part 3 — Retry budget and dead-letter queue

The constructor takes one more argument, a positive integer `max_attempts`. Each task now keeps an
*attempt count*: the number of times it has been reserved, starting from 0 when it is submitted. There is
also a fourth state, `dead`, which only `requeue_dead` can leave.

Whenever a `reserved` task leaves that state without completing — through `fail` or through lease
expiry — look at its attempt count, which already includes the reservation that just ended. If the count
has reached `max_attempts`, the task becomes `dead` instead of `ready`; otherwise it becomes `ready`,
exactly as before. `complete` is unaffected: a completed task still ends in the terminal `completed` state.

`dead_letters()` returns the `task_id` of every task currently `dead`, in the order they became `dead`.

`requeue_dead(task_id)` moves a `dead` task to the back of the `ready` queue and resets its attempt count
to 0, as if it had just been submitted, so it gets `max_attempts` more reservations. Raises
`UnknownTaskError` if `task_id` was never submitted, or `ValueError` if it is not currently `dead`. Like
every other method, `dead_letters` and `requeue_dead` begin with a reclaiming pass.

```py
class WorkQueue:
    def __init__(self, clock: "ManualClock", lease_duration: int, max_attempts: int) -> None: ...
    def dead_letters(self) -> list[str]: ...
    def requeue_dead(self, task_id: str) -> None: ...
```

Example, with `lease_duration = 3` and `max_attempts = 2`:

```text
t=0  q.submit('t1', 'x')
t=0  rA = q.reserve('A')          # 1st reservation
t=0  q.fail('t1', rA.token)       # 1 < 2 attempts so far -> ready
t=0  rB = q.reserve('B')          # 2nd reservation
t=0  q.fail('t1', rB.token)       # 2 >= 2 attempts -> dead
     q.dead_letters()             # -> ['t1']
     q.reserve('C')               # -> None, nothing ready
     q.requeue_dead('t1')         # attempt count reset to 0
     rC = q.reserve('C')          # 1st reservation again
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two things worth confirming with the interviewer before coding: whether a task that comes back to
`ready` (after a failure, a timeout, or `requeue_dead`) shares one FIFO order with freshly submitted
tasks or gets some priority; and whether the retry cap counts reservations or retries after the first —
`max_attempts = 3` allows three reservations where "3 retries" would allow four, the usual off-by-one.

### Part 1

A dict keyed by `task_id` holds each task's authoritative state; a `deque` holds the `task_id`s currently
`ready`, in the order they got there: `reserve` pops the front, `submit` and a requeue append at the back.
`complete` and `fail` share one check, `_lookup_reserved`: an unknown `task_id` raises `UnknownTaskError`;
anything else — a wrong token, a token from a reservation that already ended, a task that is not
`reserved` at all (an already-`completed` one included) — raises `InvalidReservationError`, because in
each case the caller's token is not the task's current reservation.

```python
import heapq
from collections import deque
from typing import Any, NamedTuple


class UnknownTaskError(Exception):
    """task_id was never passed to submit."""


class InvalidReservationError(Exception):
    """token is not the task's current reservation."""


class Reservation(NamedTuple):
    task_id: str
    token: int
    payload: Any


class _Task:
    __slots__ = ("payload", "status", "attempts", "token", "deadline")

    def __init__(self, payload):
        self.payload = payload
        self.status = "ready"
        self.attempts = 0
        self.token = None
        self.deadline = None


class WorkQueue:
    def __init__(self):
        self._tasks: dict[str, _Task] = {}
        self._ready = deque()
        self._next_token = 0

    def submit(self, task_id, payload):
        self._reclaim_expired()                     # NOTE: submit reclaims too, so expired tasks queue ahead of this one
        if task_id in self._tasks:
            raise ValueError(f"duplicate task_id {task_id!r}")
        self._tasks[task_id] = _Task(payload)
        self._ready.append(task_id)

    def reserve(self, worker_id):
        self._reclaim_expired()
        if not self._ready:
            return None
        task_id = self._ready.popleft()
        task = self._tasks[task_id]
        task.attempts += 1                          # NOTE: counted here, at reserve time -- not in fail()
        self._next_token += 1
        task.status, task.token = "reserved", self._next_token
        return Reservation(task_id, task.token, task.payload)

    def _lookup_reserved(self, task_id, token):
        self._reclaim_expired()                     # NOTE: before the token check -- this lease may just have expired
        task = self._tasks.get(task_id)
        if task is None:
            raise UnknownTaskError(task_id)
        if task.status != "reserved" or task.token != token:
            raise InvalidReservationError(task_id, token)
        return task

    def complete(self, task_id, token):
        task = self._lookup_reserved(task_id, token)
        task.status, task.token, task.deadline = "completed", None, None

    def fail(self, task_id, token):
        task = self._lookup_reserved(task_id, token)
        self._release(task_id, task)

    def _release(self, task_id, task):               # NOTE: Part 3 replaces this with a ready-or-dead version
        task.status, task.token, task.deadline = "ready", None, None
        self._ready.append(task_id)

    def _reclaim_expired(self):                       # NOTE: no-op until Part 2 gives it a real body
        pass
```

With no heap yet, every method here is $O(1)$. The Part 1 example, run on this class:

```python
q = WorkQueue()
q.submit('t1', 'build')
q.submit('t2', 'test')
r1, r2 = q.reserve('w1'), q.reserve('w2')
q.complete('t1', r1.token)
q.fail('t2', r2.token)
r3 = q.reserve('w3')
assert (r1.task_id, r2.task_id, r3.task_id) == ('t1', 't2', 't2')
try:
    q.complete('t2', r2.token)
    raise AssertionError("stale token accepted")
except InvalidReservationError:
    q.complete('t2', r3.token)
```

### Part 2

A min-heap of `(deadline, task_id, token)` pops leases in exactly the order a reclaiming pass must
follow. Entries are never removed directly (lazy deletion): when `_reclaim_expired` pops one, a `token`
equal to the task's *current* token means the task is still on that reservation and it really has
expired; any other token means the task was completed, failed or re-reserved since the push, and the
stale entry is simply dropped. Let $n$ be the number of method calls so far; the heap never holds more
than $n$ entries. Each reservation is pushed once and popped at most once, so the heap work over $n$
calls totals $O(n \log n)$: amortized $O(\log n)$ per call, although a single call that finds $k$
expired leases pays $O(k \log n)$.

```python
def __init__(self, clock, lease_duration):
    self._clock = clock
    self._lease_duration = lease_duration
    self._tasks: dict[str, _Task] = {}
    self._ready = deque()
    self._next_token = 0
    self._leases = []          # min-heap of (deadline, task_id, token)


WorkQueue.__init__ = __init__


def reserve(self, worker_id):
    self._reclaim_expired()
    if not self._ready:
        return None
    task_id = self._ready.popleft()
    task = self._tasks[task_id]
    task.attempts += 1
    self._next_token += 1
    task.status, task.token = "reserved", self._next_token
    task.deadline = self._clock.now() + self._lease_duration
    heapq.heappush(self._leases, (task.deadline, task_id, task.token))
    return Reservation(task_id, task.token, task.payload)


WorkQueue.reserve = reserve


def _reclaim_expired(self):
    now = self._clock.now()
    while self._leases and self._leases[0][0] < now:       # NOTE: '<', not '<=' -- a lease is valid through its deadline
        _, task_id, token = heapq.heappop(self._leases)
        task = self._tasks[task_id]
        if task.status == "reserved" and task.token == token:    # NOTE: otherwise this entry is stale -- discard it
            self._release(task_id, task)


WorkQueue._reclaim_expired = _reclaim_expired
```

The Part 2 example, run on this class:

```python
clock = ManualClock()
q = WorkQueue(clock, lease_duration=5)
q.submit('t1', 'x')
rA = q.reserve('A')
clock.advance(7)
rB = q.reserve('B')
assert rB.task_id == 't1'
try:
    q.complete('t1', rA.token)
    raise AssertionError("expired token accepted")
except InvalidReservationError:
    q.complete('t1', rB.token)
```

### Part 3

Both `fail` and `_reclaim_expired` send a task that leaves `reserved` through `_release`, so replacing
that one method treats a timeout exactly like an explicit failure.

```python
def __init__(self, clock, lease_duration, max_attempts):
    self._clock = clock
    self._lease_duration = lease_duration
    self._max_attempts = max_attempts
    self._tasks: dict[str, _Task] = {}
    self._ready = deque()
    self._dead = []            # task_ids, in the order they entered `dead`
    self._next_token = 0
    self._leases = []


WorkQueue.__init__ = __init__


def _release(self, task_id, task):
    task.token, task.deadline = None, None
    if task.attempts >= self._max_attempts:      # NOTE: attempts already counts the reservation that just ended
        task.status = "dead"
        self._dead.append(task_id)
    else:
        task.status = "ready"
        self._ready.append(task_id)


WorkQueue._release = _release


def dead_letters(self):
    self._reclaim_expired()
    return list(self._dead)


WorkQueue.dead_letters = dead_letters


def requeue_dead(self, task_id):
    self._reclaim_expired()
    task = self._tasks.get(task_id)
    if task is None:
        raise UnknownTaskError(task_id)
    if task.status != "dead":
        raise ValueError(f"{task_id!r} is not in the dead-letter queue")
    self._dead.remove(task_id)
    task.status, task.attempts = "ready", 0
    self._ready.append(task_id)


WorkQueue.requeue_dead = requeue_dead
```

`max_attempts = 1` needs no special case: the first reservation already brings `attempts` to `1`, so a
single `fail` (or a single expiry) sends the task straight to `dead`. With $d$ dead tasks, `dead_letters`
costs $O(d)$ because it copies every id out, and so does the `list.remove` in `requeue_dead`.

### Follow-ups

- This queue only gives *at-least-once* delivery: a lease expiring does not mean the first worker
  stopped, so two workers can end up processing the same task concurrently. Exactly-once needs the
  worker's own side effect to be idempotent, or a check against the task's current token at the point
  the effect is applied, not only when `complete` is called.
- A short `lease_duration` burns retry budget on tasks that are merely slow, while a long one leaves a
  crashed worker's task stuck longer. A `heartbeat(task_id, token)` that pushes a live worker's deadline
  forward lets the lease stay short.
- The queue lives in memory, so a crash loses everything. Durability means logging each state transition
  before applying it in memory and replaying the log after a restart.

<details>
<summary>Checks (runnable)</summary>

```python
import random
import time


class NaiveWorkQueue:
    """A direct reading of the statement: no heap, no helper shared with WorkQueue.
    Every call scans every task to find expired leases."""

    def __init__(self, clock, lease_duration, max_attempts):
        self.clock = clock
        self.lease_duration = lease_duration
        self.max_attempts = max_attempts
        self.status, self.payload, self.attempts = {}, {}, {}
        self.token, self.deadline, self.order = {}, {}, {}
        self._seq = 0
        self._next_token = 0
        self.dead_order = []

    def _mark_ready(self, task_id):
        self.status[task_id] = "ready"
        self.token[task_id] = None
        self.deadline[task_id] = None
        self._seq += 1
        self.order[task_id] = self._seq

    def _reclaim_all(self):
        now = self.clock.now()
        expired = sorted(                    # ascending deadline, ties by ascending task_id
            (self.deadline[t], t) for t in self.status
            if self.status[t] == "reserved" and self.deadline[t] < now
        )
        for _, task_id in expired:
            self._expire_or_kill(task_id)

    def _expire_or_kill(self, task_id):
        if self.attempts[task_id] >= self.max_attempts:
            self.status[task_id] = "dead"
            self.token[task_id] = None
            self.deadline[task_id] = None
            self.dead_order.append(task_id)
        else:
            self._mark_ready(task_id)

    def submit(self, task_id, payload):
        self._reclaim_all()
        if task_id in self.status:
            raise ValueError(f"duplicate task_id {task_id!r}")
        self.payload[task_id] = payload
        self.attempts[task_id] = 0
        self._mark_ready(task_id)

    def reserve(self, worker_id):
        self._reclaim_all()
        ready_ids = [t for t, st in self.status.items() if st == "ready"]
        if not ready_ids:
            return None
        task_id = min(ready_ids, key=lambda t: self.order[t])
        self.attempts[task_id] += 1
        self._next_token += 1
        self.token[task_id] = self._next_token
        self.status[task_id] = "reserved"
        self.deadline[task_id] = self.clock.now() + self.lease_duration
        return Reservation(task_id, self.token[task_id], self.payload[task_id])

    def _check(self, task_id, token):
        self._reclaim_all()
        if task_id not in self.status:
            raise UnknownTaskError(task_id)
        if self.status[task_id] != "reserved" or self.token[task_id] != token:
            raise InvalidReservationError(task_id, token)

    def complete(self, task_id, token):
        self._check(task_id, token)
        self.status[task_id] = "completed"
        self.token[task_id] = None
        self.deadline[task_id] = None

    def fail(self, task_id, token):
        self._check(task_id, token)
        self._expire_or_kill(task_id)

    def dead_letters(self):
        self._reclaim_all()
        return list(self.dead_order)

    def requeue_dead(self, task_id):
        self._reclaim_all()
        if task_id not in self.status:
            raise UnknownTaskError(task_id)
        if self.status[task_id] != "dead":
            raise ValueError(f"{task_id!r} is not in the dead-letter queue")
        self.dead_order.remove(task_id)
        self.attempts[task_id] = 0
        self._mark_ready(task_id)


def expect(error, fn, *args):
    try:
        fn(*args)
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


# --- hand-built cases, run against both implementations ---
for Queue in (WorkQueue, NaiveWorkQueue):
    clock = ManualClock()                                # the Part 3 example
    q = Queue(clock, lease_duration=3, max_attempts=2)
    q.submit('t1', 'x')
    q.fail('t1', q.reserve('A').token)
    rB = q.reserve('B')
    q.fail('t1', rB.token)
    assert q.dead_letters() == ['t1'] and q.reserve('C') is None
    expect(InvalidReservationError, q.complete, 't1', rB.token)   # dead is not reserved
    q.requeue_dead('t1')
    assert q.reserve('C').task_id == 't1'
    expect(ValueError, q.requeue_dead, 't1')             # reserved, not dead
    expect(UnknownTaskError, q.requeue_dead, 'nope')

    clock = ManualClock()                                # valid at the deadline, expired one tick later
    q = Queue(clock, lease_duration=3, max_attempts=5)
    q.submit('x', 0)
    q.submit('y', 0)
    rx, ry = q.reserve('w'), q.reserve('w')
    clock.advance(3)
    q.complete('x', rx.token)
    clock.advance(1)
    expect(InvalidReservationError, q.complete, 'y', ry.token)

    clock = ManualClock()                                # one pass goes by (deadline, task_id); submit runs one
    q = Queue(clock, lease_duration=4, max_attempts=5)
    q.submit('c', 0)
    q.reserve('w')                                       # c: deadline 4
    clock.advance(1)
    q.submit('b', 0)
    q.submit('a', 0)
    q.reserve('w'), q.reserve('w')                       # b, a: deadline 5
    clock.advance(5)
    q.submit('d', 0)                                     # reclaims c, then a, then b, before appending d
    assert [q.reserve('w').task_id for _ in range(4)] == ['c', 'a', 'b', 'd']

    clock = ManualClock()                                # max_attempts = 1: a single expiry is fatal
    q = Queue(clock, lease_duration=2, max_attempts=1)
    q.submit('z', 0)
    q.reserve('w')
    clock.advance(3)
    assert q.dead_letters() == ['z']


# --- randomized cross-check against NaiveWorkQueue, plus the statement's invariants ---
def outcome_of(fn, *args):
    try:
        return ("ok", fn(*args))
    except Exception as e:
        return ("err", type(e).__name__)


def fuzz(seed, n_ops):
    rng = random.Random(seed)
    clock = ManualClock()
    lease_duration = rng.choice([1, 2, 3, 5])
    max_attempts = rng.choice([1, 1, 2, 3, 5])
    fast = WorkQueue(clock, lease_duration, max_attempts)
    slow = NaiveWorkQueue(clock, lease_duration, max_attempts)
    all_task_ids, issued, retired, ever_completed, outcomes = [], [], set(), set(), {}

    def run(name, *args):
        of = outcome_of(getattr(fast, name), *args)
        os_ = outcome_of(getattr(slow, name), *args)
        assert of == os_, (seed, name, args, of, os_)
        key = f"{name}:{'ok' if of[0] == 'ok' else 'err:' + of[1]}"
        outcomes[key] = outcomes.get(key, 0) + 1
        return of

    for step in range(n_ops):
        pick = rng.random()
        if pick < 0.25 or not all_task_ids:
            tid = rng.choice(all_task_ids) if all_task_ids and rng.random() < 0.1 else f"task{step}"
            if run("submit", tid, step)[0] == "ok":
                all_task_ids.append(tid)
        elif pick < 0.45:
            of = run("reserve", f"w{step % 5}")
            if of[1] is None:
                outcomes["reserve:none"] = outcomes.get("reserve:none", 0) + 1
            else:
                assert all(of[1].token != tok for _, tok in issued)     # every token is fresh
                issued.append((of[1].task_id, of[1].token))
        elif pick < 0.85:
            method = "complete" if pick < 0.65 else "fail"
            if issued and rng.random() < 0.75:
                tid, token = rng.choice(issued[-4:] if rng.random() < 0.6 else issued)
            elif rng.random() < 0.3:
                tid, token = f"ghost{step}", rng.randint(-5, 5)
            else:
                tid, token = rng.choice(all_task_ids), rng.randint(-5, 5)
            of = run(method, tid, token)
            if (tid, token) in retired:
                assert of == ("err", "InvalidReservationError")          # an ended reservation never revives
            if of[0] == "ok" and method == "complete":
                ever_completed.add(tid)
        elif pick < 0.90:
            clock.advance(rng.choice([0, 1, 1, 2, 3, 5]))
        elif pick < 0.95:
            run("dead_letters")
        else:
            run("requeue_dead", rng.choice(all_task_ids) if rng.random() < 0.8 else f"ghost{step}")
        for tid in all_task_ids:
            task = fast._tasks[tid]
            assert task.status == slow.status[tid] and task.token == slow.token[tid]
            assert task.attempts == slow.attempts[tid] <= max_attempts
            assert tid not in ever_completed or task.status == "completed"
        retired.update(r for r in issued if slow.token[r[0]] != r[1])
    return outcomes


totals, start = {}, time.perf_counter()
for seed in range(1500):
    for key, count in fuzz(seed, 80).items():
        totals[key] = totals.get(key, 0) + count
elapsed = time.perf_counter() - start

for name in ["submit:ok", "submit:err:ValueError", "reserve:ok", "reserve:none", "dead_letters:ok",
             "complete:ok", "complete:err:UnknownTaskError", "complete:err:InvalidReservationError",
             "fail:ok", "fail:err:UnknownTaskError", "fail:err:InvalidReservationError",
             "requeue_dead:ok", "requeue_dead:err:UnknownTaskError", "requeue_dead:err:ValueError"]:
    assert totals.get(name, 0) > 50, (name, totals.get(name, 0))    # every branch fires many times
assert elapsed < 10, elapsed                             # loose bound: 120,000 steps on two queues

print("all checks passed")
```

</details>

</details>
