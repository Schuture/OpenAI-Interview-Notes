# Fault-Tolerant Work Queue

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Medium | SWE · Infra Eng | queue, state-machine, retry | 4 parts |
<!-- meta:end -->

## Problem

A *work queue* holds tasks that workers pull, process, and report back on. Each task is submitted with
a caller-chosen `task_id`, unique among every task ever submitted, and an opaque `payload` that the
queue never inspects. A worker is identified by a `worker_id` string. In one run, the calls to the
methods below number at most $2 \times 10^5$ in total.

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

Every accepted `submit` gives its task a *submission number*: 1 for the first task, 2 for the second, and
so on. A task keeps its submission number for its whole life.

`reserve(worker_id)` hands the calling worker, out of the tasks currently `ready`, the one with the
smallest submission number — first in, first out by original submission, regardless of whether a task got
to `ready` by being freshly submitted or by being returned there. It moves that task to `reserved` and returns a `Reservation`
holding `task_id`, `payload`, and a fresh *token*: a value, unique to this one act of reserving this one
task, that `complete` and `fail` must present back. Returns `None` if no task is `ready`.

`complete(task_id, token)` marks the task `completed`. This only succeeds if the task is currently
`reserved` and `token` matches the token issued by that reservation; otherwise it raises
`InvalidReservationError`. If `task_id` was never submitted, it raises `UnknownTaskError` instead.

`fail(task_id, token)` checks `token` under the exact same rule as `complete`. Once it matches, the task
goes back to `ready`, with its submission number unchanged, so `reserve` picks it ahead of every ready
task submitted after it. This part places no limit on how many times a task may
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
q.submit('t3', 'deploy')

r1 = q.reserve('w1')          # r1.task_id == 't1'
r2 = q.reserve('w2')          # r2.task_id == 't2'
q.complete('t1', r1.token)    # 't1' -> completed
q.fail('t2', r2.token)        # 't2' -> ready; its number 2 is still below 't3''s 3

r3 = q.reserve('w3')          # r3.task_id == 't2' again (not 't3'), with a new token
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
once `clock.now()` is strictly greater than the deadline. `lease_duration` and every value the clock
returns are at most $10^9$.

There is no background thread scanning for expirations. Instead, every call to a `WorkQueue` method,
`submit` included, begins with a *reclaiming pass*: each reservation whose lease has expired by then is
ended with the same effect as if its worker had called `fail` on it at that moment, so its task re-enters
`ready` with its submission number unchanged. One pass handles the expired reservations one at a time, in ascending
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

`requeue_dead(task_id)` moves a `dead` task back to `ready`, with its submission number unchanged, and
resets its attempt count to 0, so it gets `max_attempts` more reservations. Raises
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

### Part 4 — Dependencies

`submit` takes a third argument, `depends_on`: a sequence of `task_id`s, empty by default, naming the
task's *dependencies*. A task is *unblocked* once every one of its dependencies is `completed`; a task
without dependencies is always unblocked. A `depends_on` holds at most 10 ids, and an id listed twice
counts once.

- Every id in `depends_on` must belong to a task submitted earlier; otherwise `submit` raises
  `UnknownTaskError`. Since a task can only depend on tasks submitted
  before it, the dependency graph has no cycle. A `task_id` that was already submitted still raises `ValueError`,
  and that check comes first.
- If any dependency is currently `dead`, `submit` raises `ValueError`. A rejected `submit` changes nothing.
- `reserve` hands out, among the tasks that are `ready` *and* unblocked, the one with the smallest
  submission number. A `ready` task that is still blocked is skipped, and it keeps its place for when it
  gets unblocked. Returns `None` if no task qualifies.
- A task whose dependency is `dead` can never be unblocked, so it is dead as well. Whenever a task becomes
  `dead` (through `fail` or lease expiry), every task that depends on it, directly or through a chain of
  dependencies, and is not `dead` yet becomes `dead` in the same step: first the task itself, then the
  others in ascending order of submission number. Their attempt counts stay as they are.
  `dead_letters()` lists tasks in the order they became `dead`, these ones included.
- `requeue_dead(task_id)` follows Part 3, and additionally raises `ValueError` if any dependency of the
  task is currently `dead`. It revives only that one task: tasks that died with it stay `dead` until they are
  requeued themselves, after their own dependencies are no longer `dead`.

```py
class WorkQueue:
    def submit(self, task_id: str, payload: Any, depends_on: "Sequence[str]" = ()) -> None: ...
```

Example, with `lease_duration = 10` and `max_attempts = 2`. Tasks `c` and `e` depend on `a`, `d` depends
on `b` and `c`, and `f` depends on `d`:

```text
q.submit('a', 'x');  q.submit('b', 'x')                  # submission numbers 1, 2
q.submit('c', 'x', depends_on=['a'])                     # 3
q.submit('d', 'x', depends_on=['b', 'c'])                # 4
q.submit('e', 'x', depends_on=['a'])                     # 5
q.submit('f', 'x', depends_on=['d'])                     # 6

rA = q.reserve('w1')              # 'a'
rB = q.reserve('w2')              # 'b'
q.reserve('w3')                   # None: c, d, e, f are blocked
q.complete('a', rA.token)         # c and e are unblocked
rC = q.reserve('w1')              # 'c', number 3 < 5
q.fail('b', rB.token)             # 1 < 2 attempts -> ready
rB2 = q.reserve('w2')             # 'b' again, number 2 < 5
q.complete('c', rC.token)         # d still waits for b
rE = q.reserve('w1')              # 'e'
q.reserve('w3')                   # None: d and f are blocked
q.fail('b', rB2.token)            # 2 >= 2 attempts -> dead; d and f die with it
q.dead_letters()                  # -> ['b', 'd', 'f']
q.requeue_dead('d')               # raises ValueError: b is dead
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two things worth confirming with the interviewer before coding: whether a task that comes back to
`ready` (after a failure, a timeout, or `requeue_dead`) goes behind everything queued so far or keeps
its original place in the submission order, which the statement fixes as the latter; and whether the retry cap counts reservations or retries after the first —
`max_attempts = 3` allows three reservations where "3 retries" would allow four, the usual off-by-one.

### Part 1

A dict keyed by `task_id` holds each task's authoritative state, including its submission number `seq`;
a min-heap of `(seq, task_id)` holds the tasks currently `ready`: `reserve` pops the smallest, and `submit`
and every return to `ready` push. A returned task is pushed under its own old `seq`, so it comes out ahead
of every task submitted after it; a FIFO `deque` with an append at the back would get this wrong.
`complete` and `fail` share one check, `_lookup_reserved`: an unknown `task_id` raises `UnknownTaskError`;
anything else — a wrong token, a token from a reservation that already ended, a task that is not
`reserved` at all (an already-`completed` one included) — raises `InvalidReservationError`, because in
each case the caller's token is not the task's current reservation.

```python
import heapq
from typing import Any, NamedTuple

READY, RESERVED, COMPLETED, DEAD = "ready", "reserved", "completed", "dead"


class UnknownTaskError(Exception):
    """task_id was never passed to submit."""


class InvalidReservationError(Exception):
    """token is not the task's current reservation."""


class Reservation(NamedTuple):
    task_id: str
    token: int
    payload: Any


class _Task:
    __slots__ = ("payload", "status", "attempts", "token", "deadline", "seq")

    def __init__(self, payload: Any, seq: int):
        self.payload = payload
        self.seq = seq  # submission number, fixed for the task's whole life
        self.status = READY
        self.attempts = 0
        self.token = None
        self.deadline = None


class WorkQueue:
    def __init__(self) -> None:
        self._tasks: dict[str, _Task] = {}  # the authoritative state of every task
        self._ready = []  # min-heap of (seq, task_id)
        self._next_token = 0

    def submit(self, task_id: str, payload: Any) -> None:
        # warning: submit reclaims too, so expired tasks re-enter ready before this one is added
        self._reclaim_expired()
        if task_id in self._tasks:
            raise ValueError(f"duplicate task_id {task_id!r}")
        seq = len(self._tasks)  # warning: a rejected submit adds nothing, so the numbers stay consecutive
        self._tasks[task_id] = _Task(payload, seq)
        heapq.heappush(self._ready, (seq, task_id))

    def reserve(self, worker_id: str) -> "Reservation | None":
        self._reclaim_expired()
        if not self._ready:
            return None
        _, task_id = heapq.heappop(self._ready)  # the smallest submission number
        task = self._tasks[task_id]
        task.attempts += 1  # warning: counted here, at reserve time, not in fail()
        self._next_token += 1
        task.status, task.token = RESERVED, self._next_token
        return Reservation(task_id, task.token, task.payload)

    def _lookup_reserved(self, task_id: str, token: object) -> _Task:
        self._reclaim_expired()  # warning: before the token check, this lease may just have expired
        task = self._tasks.get(task_id)
        if task is None:
            raise UnknownTaskError(task_id)
        if task.status != RESERVED or task.token != token:
            raise InvalidReservationError(task_id, token)
        return task

    def complete(self, task_id: str, token: object) -> None:
        task = self._lookup_reserved(task_id, token)
        task.status, task.token, task.deadline = COMPLETED, None, None

    def fail(self, task_id: str, token: object) -> None:
        task = self._lookup_reserved(task_id, token)
        self._release(task_id, task)

    def _release(self, task_id: str, task: _Task) -> None:  # warning: Part 3 replaces this with a ready-or-dead version
        task.status, task.token, task.deadline = READY, None, None
        # warning: the original seq, not a fresh one; appending to a FIFO would put it behind newer tasks
        heapq.heappush(self._ready, (task.seq, task_id))

    def _reclaim_expired(self) -> None:  # warning: a no-op until Part 2 gives it a real body
        pass
```

Each `submit`, `reserve` and return to `ready` is one heap operation, $O(\log n)$ for $n$ tasks; `complete`
is $O(1)$. The Part 1 example, run on this class:

```python
q = WorkQueue()
q.submit('t1', 'build')
q.submit('t2', 'test')
q.submit('t3', 'deploy')
r1, r2 = q.reserve('w1'), q.reserve('w2')
q.complete('t1', r1.token)
q.fail('t2', r2.token)
r3 = q.reserve('w3')
assert (r1.task_id, r2.task_id, r3.task_id) == ('t1', 't2', 't2')      # t2 goes ahead of t3
try:
    q.complete('t2', r2.token)
    raise AssertionError("stale token accepted")
except InvalidReservationError:
    q.complete('t2', r3.token)
assert q.reserve('w4').task_id == 't3'
```

### Part 2

A min-heap of `(deadline, task_id, token)` pops leases in exactly the order a reclaiming pass must
follow. Entries are never removed directly (lazy deletion): when `_reclaim_expired` pops one, a `token`
equal to the task's *current* token means the task is still on that reservation and it really has
expired; any other token means the task was completed, failed or re-reserved since the push, and the
stale entry is simply dropped. Let $n$ be the number of method calls so far; the heap never holds more
than $n$ entries. Each reservation is pushed once and popped at most once, so the heap work over $n$
calls totals $O(n \log n)$: amortized $O(\log n)$ per call.

```python
def __init__(self, clock: ManualClock, lease_duration: int) -> None:
    self._clock = clock
    self._lease_duration = lease_duration
    self._tasks: dict[str, _Task] = {}
    self._ready = []  # min-heap of (seq, task_id)
    self._next_token = 0
    self._leases = []  # min-heap of (deadline, task_id, token)


WorkQueue.__init__ = __init__


def reserve(self, worker_id: str) -> "Reservation | None":
    self._reclaim_expired()
    if not self._ready:
        return None
    _, task_id = heapq.heappop(self._ready)
    task = self._tasks[task_id]
    task.attempts += 1
    self._next_token += 1
    task.status, task.token = RESERVED, self._next_token
    # the only change from Part 1: the reservation gets a lease
    task.deadline = self._clock.now() + self._lease_duration
    heapq.heappush(self._leases, (task.deadline, task_id, task.token))
    return Reservation(task_id, task.token, task.payload)


WorkQueue.reserve = reserve


def _reclaim_expired(self) -> None:
    # we never remove a lease from the heap directly (lazy deletion):
    # a popped entry whose token is still the task's current token has really expired, any other is stale
    now = self._clock.now()
    while self._leases and self._leases[0][0] < now:  # warning: '<', not '<=', a lease is valid through its deadline
        _, task_id, token = heapq.heappop(self._leases)
        task = self._tasks[task_id]
        if task.status == RESERVED and task.token == token:  # warning: otherwise this entry is stale, we discard it
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
def __init__(self, clock: ManualClock, lease_duration: int, max_attempts: int) -> None:
    self._clock = clock
    self._lease_duration = lease_duration
    self._max_attempts = max_attempts
    self._tasks: dict[str, _Task] = {}
    self._ready = []  # min-heap of (seq, task_id)
    self._dead = []  # task_ids, in the order they entered dead
    self._next_token = 0
    self._leases = []  # min-heap of (deadline, task_id, token)


WorkQueue.__init__ = __init__


def _release(self, task_id: str, task: _Task) -> None:
    # fail and _reclaim_expired both end here, so a timeout is treated exactly like a failure
    task.token, task.deadline = None, None
    if task.attempts >= self._max_attempts:  # warning: attempts already counts the reservation that just ended
        task.status = DEAD
        self._dead.append(task_id)
    else:
        task.status = READY
        heapq.heappush(self._ready, (task.seq, task_id))


WorkQueue._release = _release


def dead_letters(self) -> list[str]:
    self._reclaim_expired()
    return list(self._dead)  # we return a copy


WorkQueue.dead_letters = dead_letters


def requeue_dead(self, task_id: str) -> None:
    self._reclaim_expired()
    task = self._tasks.get(task_id)
    if task is None:
        raise UnknownTaskError(task_id)
    if task.status != DEAD:
        raise ValueError(f"{task_id!r} is not in the dead-letter queue")
    self._dead.remove(task_id)
    task.status, task.attempts = READY, 0
    heapq.heappush(self._ready, (task.seq, task_id))  # warning: under its original seq, not at the back of the line


WorkQueue.requeue_dead = requeue_dead
```

`max_attempts = 1` needs no special case: the first reservation already brings `attempts` to `1`, so a
single `fail` (or a single expiry) sends the task straight to `dead`.

### Part 4

Each task stores its distinct dependency ids and `pending`, the number of them not yet `completed`.
Next to the tasks, a reverse-edge map sends each task to the dict of its dependants. Then:

- The ready heap now holds only tasks that are `ready` and have `pending == 0`, so `reserve` is unchanged:
  the top of the heap is the earliest-submitted unblocked task. A task is pushed when it is submitted or
  requeued with `pending == 0`, when it returns to `ready` after a reservation (it was unblocked then), and
  when `complete` brings its `pending` to 0.
- `complete` walks the reverse edges of the finished task once and drops them.
- A task becoming `dead` runs a DFS over the reverse edges, kills each not-yet-dead dependant once, and
  appends them sorted by `seq` after the task itself. No dependant of a dying task has `pending == 0`, so
  none of them is on the heap and nothing needs removing from it.
- `requeue_dead` rebuilds `pending` and the edges of the one task; both are idempotent.

Let $n$ be the number of calls. Every edge is added by a `submit` or `requeue_dead` call (at most 10 each)
and removed at most once. Every death, direct or by cascade, ends a stay in a live state that one such call
started. Hence the total is $O(n \log n)$, and a single `reserve` is still $O(\log n)$.

```python
class _Task:
    __slots__ = ("payload", "status", "attempts", "token", "deadline", "seq", "deps", "pending")

    def __init__(self, payload: Any, seq: int, deps: tuple[str, ...]):
        self.payload = payload
        self.seq = seq
        self.status = READY
        self.attempts = 0
        self.token = None
        self.deadline = None
        self.deps = deps  # distinct dependency ids
        self.pending = 0  # how many of them are not yet completed


def __init__(self, clock: ManualClock, lease_duration: int, max_attempts: int) -> None:
    self._clock = clock
    self._lease_duration = lease_duration
    self._max_attempts = max_attempts
    self._tasks: dict[str, _Task] = {}
    self._ready = []  # min-heap of (seq, task_id), of the ready tasks with pending == 0, and only those
    self._dead = []
    self._next_token = 0
    self._leases = []
    self._dependents: dict[str, dict[str, None]] = {}  # reverse edges: task_id -> its not-yet-dead dependants


WorkQueue.__init__ = __init__


def _link(self, task_id: str, task: _Task) -> None:
    task.pending = 0
    for dep_id in task.deps:
        if self._tasks[dep_id].status != COMPLETED:
            task.pending += 1
            self._dependents.setdefault(dep_id, {})[task_id] = None  # warning: a dict, so linking twice is harmless
    if task.pending == 0:
        heapq.heappush(self._ready, (task.seq, task_id))


WorkQueue._link = _link


def submit(self, task_id: str, payload: Any, depends_on: "Sequence[str]" = ()) -> None:
    self._reclaim_expired()
    if task_id in self._tasks:
        raise ValueError(f"duplicate task_id {task_id!r}")
    deps = tuple(dict.fromkeys(depends_on))  # warning: a repeated id must count once, or pending never reaches 0
    for dep_id in deps:
        # warning: task_id itself is not stored yet, so a self-dependency lands here too
        if dep_id not in self._tasks:
            raise UnknownTaskError(dep_id)
    for dep_id in deps:
        if self._tasks[dep_id].status == DEAD:
            raise ValueError(f"dependency {dep_id!r} is dead")

    # warning: everything is validated above first, a rejected submit must change nothing
    task = _Task(payload, len(self._tasks), deps)
    self._tasks[task_id] = task
    self._link(task_id, task)


WorkQueue.submit = submit


def complete(self, task_id: str, token: object) -> None:
    task = self._lookup_reserved(task_id, token)
    task.status, task.token, task.deadline = COMPLETED, None, None
    for child_id in self._dependents.pop(task_id, ()):  # each edge is used once: its source is now final
        child = self._tasks[child_id]
        if child.status == READY:  # warning: a dead child is skipped, requeue_dead recounts from scratch
            child.pending -= 1
            if child.pending == 0:
                heapq.heappush(self._ready, (child.seq, child_id))


WorkQueue.complete = complete


def _release(self, task_id: str, task: _Task) -> None:
    task.token, task.deadline = None, None
    if task.attempts < self._max_attempts:
        # warning: pending is 0 here, since the task was reserved, so it goes straight back on the heap
        task.status = READY
        heapq.heappush(self._ready, (task.seq, task_id))
        return

    # first the task itself dies
    task.status = DEAD
    self._dead.append(task_id)
    # then a DFS over the reverse edges kills every not-yet-dead dependant once
    doomed, stack = [], [task_id]
    while stack:
        # the edges out of a dead task are dropped; requeue_dead re-adds them
        for child_id in self._dependents.pop(stack.pop(), ()):
            child = self._tasks[child_id]
            if child.status != DEAD:
                child.status = DEAD  # warning: marked at once, so a child reachable by two paths is collected once
                doomed.append(child_id)
                stack.append(child_id)
    # warning: the DFS order is arbitrary, the statement says ascending seq
    doomed.sort(key=lambda child_id: self._tasks[child_id].seq)
    self._dead.extend(doomed)


WorkQueue._release = _release


def requeue_dead(self, task_id: str) -> None:
    self._reclaim_expired()
    task = self._tasks.get(task_id)
    if task is None:
        raise UnknownTaskError(task_id)
    if task.status != DEAD:
        raise ValueError(f"{task_id!r} is not in the dead-letter queue")
    if any(self._tasks[dep_id].status == DEAD for dep_id in task.deps):
        # warning: otherwise a ready task could wait on a dead one forever
        raise ValueError(f"{task_id!r} has a dead dependency")
    self._dead.remove(task_id)
    task.status, task.attempts = READY, 0
    self._link(task_id, task)


WorkQueue.requeue_dead = requeue_dead
```

The Part 4 example, run on this class:

```python
q = WorkQueue(ManualClock(), lease_duration=10, max_attempts=2)
q.submit('a', 'x')
q.submit('b', 'x')
q.submit('c', 'x', depends_on=['a'])
q.submit('d', 'x', depends_on=['b', 'c'])
q.submit('e', 'x', depends_on=['a'])
q.submit('f', 'x', depends_on=['d'])
rA, rB = q.reserve('w1'), q.reserve('w2')
assert (rA.task_id, rB.task_id) == ('a', 'b') and q.reserve('w3') is None
q.complete('a', rA.token)
rC = q.reserve('w1')
assert rC.task_id == 'c'
q.fail('b', rB.token)
rB2 = q.reserve('w2')
assert rB2.task_id == 'b'
q.complete('c', rC.token)
rE = q.reserve('w1')
assert rE.task_id == 'e' and q.reserve('w3') is None
q.fail('b', rB2.token)
assert q.dead_letters() == ['b', 'd', 'f']
try:
    q.requeue_dead('d')
    raise AssertionError("revived with a dead dependency")
except ValueError:
    pass
```

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
- A per-task `cooldown`: a task that fails or expires becomes reservable again only at
  `failure_time + cooldown`, still under its original submission number. Park it in a second min-heap keyed
  by that release time and, at the start of every call after the reclaiming pass, move every entry that is
  due into the ready heap; a cascade must not touch parked tasks that are not dead.

<details>
<summary>Checks (runnable)</summary>

```python
import random
import time


class NaiveWorkQueue:
    """A direct reading of the statement: no heap, no helper shared with WorkQueue.
    Every call scans every task: for expired leases, for the next task to reserve,
    and for the dependants of a task that died."""

    def __init__(self, clock, lease_duration, max_attempts):
        self.clock = clock
        self.lease_duration = lease_duration
        self.max_attempts = max_attempts
        self.status, self.payload, self.attempts = {}, {}, {}
        self.token, self.deadline, self.order, self.deps = {}, {}, {}, {}
        self._next_token = 0
        self.dead_order = []

    def _mark_ready(self, task_id):
        self.status[task_id] = "ready"
        self.token[task_id] = None
        self.deadline[task_id] = None

    def _reclaim_all(self):
        now = self.clock.now()
        expired = sorted(                    # ascending deadline, ties by ascending task_id
            (self.deadline[t], t) for t in self.status
            if self.status[t] == "reserved" and self.deadline[t] < now
        )
        for _, task_id in expired:
            self._expire_or_kill(task_id)

    def _expire_or_kill(self, task_id):
        if self.attempts[task_id] < self.max_attempts:
            self._mark_ready(task_id)
            return
        self.status[task_id] = "dead"
        self.token[task_id] = None
        self.deadline[task_id] = None
        self.dead_order.append(task_id)
        doomed, changed = set(), True        # everything that depends on a dead task, transitively
        while changed:
            changed = False
            for t in self.status:
                if self.status[t] != "dead" and t not in doomed and any(
                        self.status[d] == "dead" or d in doomed for d in self.deps[t]):
                    doomed.add(t)
                    changed = True
        for t in sorted(doomed, key=lambda t: self.order[t]):
            self.status[t] = "dead"
            self.dead_order.append(t)

    def submit(self, task_id, payload, depends_on=()):
        self._reclaim_all()
        if task_id in self.status:
            raise ValueError(f"duplicate task_id {task_id!r}")
        for d in depends_on:
            if d not in self.status:
                raise UnknownTaskError(d)
        for d in depends_on:
            if self.status[d] == "dead":
                raise ValueError(f"dependency {d!r} is dead")
        self.payload[task_id] = payload
        self.attempts[task_id] = 0
        self.order[task_id] = len(self.order) + 1
        self.deps[task_id] = set(depends_on)
        self._mark_ready(task_id)

    def reserve(self, worker_id):
        self._reclaim_all()
        eligible = [t for t, st in self.status.items()
                    if st == "ready" and all(self.status[d] == "completed" for d in self.deps[t])]
        if not eligible:
            return None
        task_id = min(eligible, key=lambda t: self.order[t])
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
        if any(self.status[d] == "dead" for d in self.deps[task_id]):
            raise ValueError(f"{task_id!r} has a dead dependency")
        self.dead_order.remove(task_id)
        self.attempts[task_id] = 0
        self._mark_ready(task_id)


def expect(error, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
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

    q = Queue(ManualClock(), lease_duration=3, max_attempts=5)   # a returned task keeps its place
    for name in 'abcd':
        q.submit(name, 0)
    ra, rb, rc = q.reserve('w'), q.reserve('w'), q.reserve('w')
    q.fail('c', rc.token)
    q.fail('a', ra.token)
    assert [q.reserve('w').task_id for _ in range(3)] == ['a', 'c', 'd']   # not 'd', 'c', 'a'

    clock = ManualClock()                                # valid at the deadline, expired one tick later
    q = Queue(clock, lease_duration=3, max_attempts=5)
    q.submit('x', 0)
    q.submit('y', 0)
    rx, ry = q.reserve('w'), q.reserve('w')
    clock.advance(3)
    q.complete('x', rx.token)
    clock.advance(1)
    expect(InvalidReservationError, q.complete, 'y', ry.token)

    clock = ManualClock()                                # a pass goes by (deadline, task_id); submit runs one
    q = Queue(clock, lease_duration=4, max_attempts=1)
    q.submit('c', 0)
    q.reserve('w')                                       # c: deadline 4
    clock.advance(1)
    q.submit('b', 0)
    q.submit('a', 0)
    q.reserve('w'), q.reserve('w')                       # b, a: deadline 5
    clock.advance(5)
    q.submit('d', 0)                                     # reclaims c, then a, then b (max_attempts = 1: all dead)
    assert q.dead_letters() == ['c', 'a', 'b']

    clock = ManualClock()                                # max_attempts = 1: a single expiry is fatal
    q = Queue(clock, lease_duration=2, max_attempts=1)
    q.submit('z', 0)
    q.reserve('w')
    clock.advance(3)
    assert q.dead_letters() == ['z']

    q = Queue(ManualClock(), lease_duration=10, max_attempts=2)   # the Part 4 example
    q.submit('a', 'x')
    q.submit('b', 'x')
    q.submit('c', 'x', depends_on=['a'])
    q.submit('d', 'x', depends_on=['b', 'c'])
    q.submit('e', 'x', depends_on=['a'])
    q.submit('f', 'x', depends_on=['d'])
    rA, rB = q.reserve('w1'), q.reserve('w2')
    assert (rA.task_id, rB.task_id) == ('a', 'b') and q.reserve('w3') is None
    q.complete('a', rA.token)
    rC = q.reserve('w1')
    assert rC.task_id == 'c'                             # c and e are unblocked; c was submitted first
    q.fail('b', rB.token)
    rB2 = q.reserve('w2')
    assert rB2.task_id == 'b' and rB2.token != rB.token  # b keeps its place ahead of e
    q.complete('c', rC.token)
    rE = q.reserve('w1')
    assert rE.task_id == 'e' and q.reserve('w3') is None      # d still waits for b
    q.fail('b', rB2.token)
    assert q.dead_letters() == ['b', 'd', 'f']           # d and f die with b
    expect(ValueError, q.requeue_dead, 'd')              # b is dead
    q.complete('e', rE.token)
    assert q.reserve('w1') is None
    q.requeue_dead('b')                                  # b alone comes back; d and f stay dead
    assert q.dead_letters() == ['d', 'f']
    rB3 = q.reserve('w1')
    assert rB3.task_id == 'b'
    q.complete('b', rB3.token)
    q.requeue_dead('d')
    q.requeue_dead('f')
    assert q.reserve('w1').task_id == 'd' and q.reserve('w1') is None    # f waits for d

    q = Queue(ManualClock(), lease_duration=10, max_attempts=3)   # submit-time rejections
    q.submit('a', 0)
    expect(UnknownTaskError, q.submit, 'b', 0, depends_on=['a', 'zzz'])
    expect(UnknownTaskError, q.submit, 'b', 0, depends_on=['b'])  # self-dependency: not submitted yet
    expect(ValueError, q.submit, 'a', 0, depends_on=['a'])        # duplicate id comes first
    q.submit('b', 0, depends_on=['a', 'a'])              # rejected calls left no trace; repeats count once
    q.complete('a', q.reserve('w').token)
    assert q.reserve('w').task_id == 'b'
    q = Queue(ManualClock(), lease_duration=10, max_attempts=1)
    q.submit('a', 0)
    q.fail('a', q.reserve('w').token)
    expect(ValueError, q.submit, 'b', 0, depends_on=['a'])        # dead dependency
    q.requeue_dead('a')
    q.submit('b', 0, depends_on=['a'])


# --- randomized cross-check against NaiveWorkQueue, plus the statement's invariants ---
def outcome_of(fn, *args, **kwargs):
    try:
        return ("ok", fn(*args, **kwargs))
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

    def run(name, *args, **kwargs):
        of = outcome_of(getattr(fast, name), *args, **kwargs)
        os_ = outcome_of(getattr(slow, name), *args, **kwargs)
        assert of == os_, (seed, name, args, kwargs, of, os_)
        key = f"{name}:{'ok' if of[0] == 'ok' else 'err:' + of[1]}"
        outcomes[key] = outcomes.get(key, 0) + 1
        return of

    for step in range(n_ops):
        pick = rng.random()
        if pick < 0.25 or not all_task_ids:
            tid = rng.choice(all_task_ids) if all_task_ids and rng.random() < 0.1 else f"task{step}"
            deps = []
            if all_task_ids and rng.random() < 0.6:
                deps = [rng.choice(all_task_ids) for _ in range(rng.randint(1, 3))]   # repeats allowed
                if rng.random() < 0.05:
                    deps.append(rng.choice([f"ghost{step}", tid]))                    # unknown, or itself
            if run("submit", tid, step, depends_on=deps)[0] == "ok":
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
            before = len(slow.dead_order)
            of = run(method, tid, token)
            if len(slow.dead_order) - before >= 2:
                outcomes["cascade"] = outcomes.get("cascade", 0) + 1
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
            if slow.status[tid] in ("ready", "reserved"):
                assert all(slow.status[d] != "dead" for d in slow.deps[tid])      # nothing live waits on a dead task
            if slow.status[tid] == "reserved":
                assert all(slow.status[d] == "completed" for d in slow.deps[tid])
        assert fast.dead_letters() == slow.dead_letters()
        retired.update(r for r in issued if slow.token[r[0]] != r[1])
    return outcomes


totals, start = {}, time.perf_counter()
for seed in range(1500):
    for key, count in fuzz(seed, 80).items():
        totals[key] = totals.get(key, 0) + count
elapsed = time.perf_counter() - start

for name in ["submit:ok", "submit:err:ValueError", "submit:err:UnknownTaskError", "reserve:ok", "reserve:none",
             "dead_letters:ok", "complete:ok", "complete:err:UnknownTaskError",
             "complete:err:InvalidReservationError", "fail:ok", "fail:err:UnknownTaskError",
             "fail:err:InvalidReservationError", "requeue_dead:ok", "requeue_dead:err:UnknownTaskError",
             "requeue_dead:err:ValueError", "cascade"]:
    assert totals.get(name, 0) > 50, (name, totals.get(name, 0))    # every branch fires many times
assert elapsed < 20, elapsed                             # loose bound: 120,000 steps on two queues

print("all checks passed")
```

</details>

</details>
