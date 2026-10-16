# Job Scheduler Bug Hunt

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Debugging · Python | ★☆☆☆☆ | Medium | SWE · Infra Eng | debugging, concurrency, asyncio, heap, testing | 2 parts / 60 min | Onsite |
<!-- meta:end -->

## Problem

Two small job schedulers are given, one built on threads and one on `asyncio`. A *job* is a function with
positional and keyword arguments, a `run_at` time (the earliest clock reading at which it may start) and a
*status*: `PENDING` until it has finished, then `COMPLETED` if the function returned normally, with its return
value stored in `result`, or `FAILED` if it raised an `Exception`, with that exception stored in `error`.
A `clock` is a zero-argument callable returning the current time in seconds, so a test can move time forward
by hand instead of waiting. Each part has three bugs, all of them inside the scheduler class; a user report
describes the first one.

### Part 1: a threaded scheduler

`submit(job)` adds a job to a min-heap ordered by `run_at`. `run_due()` removes every job with
`run_at <= clock()` from the heap and starts one daemon thread for each; it returns the started threads.
Jobs with equal `run_at` start in the order they were submitted, and `started` records the jobs in the order
they left the heap. A job must leave the heap exactly once and only once it is due, even when several threads
call `run_due()` at the same time. `start(poll)` calls `run_due()` every `poll` seconds on a background
thread, and `stop()` ends that thread. `run_due` calls `checkpoint` after it has seen that a job is due and
before it removes the job; `checkpoint` does nothing unless a test replaces it, so a test can hold several
threads at that exact point.

```python
import heapq
import threading
import time
from enum import Enum


class Status(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job:
    """One unit of work: call func(*args, **kwargs) once the clock reaches run_at."""

    def __init__(self, func, args=(), kwargs=None, run_at=0.0):
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.run_at = run_at
        self.status = Status.PENDING
        self.result = None
        self.error = None


class FakeClock:
    """A clock a test can move by hand instead of waiting on the wall clock."""

    def __init__(self, start: float = 0.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class Scheduler:
    """Runs each submitted job in its own daemon thread once its run_at has been reached."""

    def __init__(self, clock=time.monotonic, checkpoint=lambda: None):
        self.clock = clock
        self.checkpoint = checkpoint
        self.started = []              # jobs in the order they were taken off the heap
        self._heap = []                # entries (run_at, job)
        self._stop = threading.Event()

    def submit(self, job):
        heapq.heappush(self._heap, (job.run_at, job))

    def run_due(self):
        """Start a thread for every job with run_at <= now and return those threads."""
        threads = []
        now = self.clock()
        while self._heap and self._heap[0][0] <= now:
            self.checkpoint()
            _, job = heapq.heappop(self._heap)
            self.started.append(job)
            thread = threading.Thread(target=self._run, args=(job,), daemon=True)
            thread.start()
            threads.append(thread)
        return threads

    def _run(self, job):
        job.result = job.func(*job.args, **job.kwargs)
        job.status = Status.COMPLETED

    def start(self, poll=0.01):
        """Call run_due every poll seconds on a background thread until stop() is called."""
        def loop():
            while not self._stop.is_set():
                self.run_due()
                time.sleep(poll)
        self._ticker = threading.Thread(target=loop, daemon=True)
        self._ticker.start()

    def stop(self):
        self._stop.set()
        self._ticker.join(timeout=5)


def test_runs_a_due_job():
    clock = FakeClock()
    scheduler = Scheduler(clock=clock)
    job = Job(lambda a, b: a + b, args=(2, 3), run_at=10)
    scheduler.submit(job)
    assert scheduler.run_due() == []          # not due yet
    clock.advance(10)
    for thread in scheduler.run_due():
        thread.join()
    assert job.status is Status.COMPLETED and job.result == 5


test_runs_a_due_job()
```

> **Bug report.** If a job's function throws, the job stays `PENDING` forever: it is never marked as done or
> as failed, and the only trace is a traceback on stderr. Everything else seems fine.

Find the three bugs. For each, write a test that fails against the code above and passes once the bug is
fixed, say what the bug does and why, and fix it with the smallest change that keeps the class's interface.

### Part 2: an `asyncio` scheduler

`Job` and `Status` are those of Part 1, except that `func` is a coroutine function. `submit(job)` adds a job
to a min-heap ordered by `(run_at, submission number)`. `run()` is a coroutine that, every `poll` seconds,
starts an `asyncio` task for every job with `run_at <= clock()`, and returns once no job is waiting in the
heap and no task is still running. While `run()` waits, the event loop must stay free to run other tasks.

```python
import asyncio
import heapq
import itertools
import time


class AsyncScheduler:
    """Runs each submitted coroutine job as an asyncio task once its run_at has been reached."""

    def __init__(self, clock=time.monotonic, poll=0.01):
        self.clock = clock
        self.poll = poll
        self._heap = []                # entries (run_at, seq, job)
        self._seq = itertools.count()

    def submit(self, job):
        heapq.heappush(self._heap, (job.run_at, next(self._seq), job))

    async def _execute(self, job):
        try:
            job.result = await job.func(*job.args, **job.kwargs)
            job.status = Status.COMPLETED
        except Exception as exc:
            job.error = exc
            job.status = Status.FAILED

    async def run(self):
        """Dispatch jobs as they fall due; return once no job is waiting or running."""
        while self._heap:
            now = self.clock()
            while self._heap and self._heap[0][0] <= now:
                _, _, job = heapq.heappop(self._heap)
                self._execute(job)
            time.sleep(self.poll)
```

> **Bug report.** I submit jobs and call `await scheduler.run()`, and nothing seems to happen: the jobs'
> statuses stay `PENDING` and none of my functions ever prints anything. Python prints a
> `RuntimeWarning` about a coroutine, but I do not know what it wants from me.

Find the three bugs and handle them as in Part 1.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two conventions are worth confirming before touching anything: a job whose function raises is final, with
status `FAILED` and the exception kept, rather than retried; and jobs with equal `run_at` start in submission
order. The tests below never wait on real time or hope for an interleaving. `FakeClock` makes the threaded
tests exact, a clock that ticks once per reading does the same for the `asyncio` randomized test, and
`checkpoint` holds threads at the one instant where the race lives. A test that can sleep or hang runs under a
timeout, so a failing test fails instead of freezing.

### Part 1: three bugs

Each row is a test against the public interface, run before and after the fix.

| Test | The class as given | Points to |
| --- | --- | --- |
| a job raising `ValueError` at time 1, a healthy job at time 2; advance to 2 and join the threads | the failing job is still `PENDING` with `error` unset, and its thread printed a traceback | bug 1, no exception handling |
| submit two jobs with the same `run_at` | the second `submit` raises `TypeError` | bug 2, heap entries |
| one job due and one not due; two threads in `run_due` held between "is it due" and "remove it" | both jobs run, the future one included | bug 3, no lock |

**Bug 1: `_run` assumes the function returns.** When `job.func(...)` raises, the exception unwinds `_run`,
so the line `job.status = Status.COMPLETED` never executes and nothing else records the outcome. The thread
ends with its traceback sent to `threading.excepthook`, which prints it. The `PENDING` status is then
indistinguishable from "not due yet". The fix catches `Exception` around the call, stores it, and sets the
terminal status. The other jobs are unaffected, since each job has its own thread.

```py
try:
    job.result = job.func(*job.args, **job.kwargs)
except Exception as exc:               # NOTE: Exception, not BaseException: Ctrl-C must still stop us
    job.error = exc
    job.status = Status.FAILED         # NOTE: set last, so a reader who sees a final status sees result/error
else:
    job.status = Status.COMPLETED
```

**Bug 2: heap entries are `(run_at, job)`.** `heapq` orders entries with `<`, and tuples compare element by
element: only when the first elements are equal does Python compare the second ones, and `Job` defines no
ordering, so two jobs with the same `run_at` raise `TypeError` in `heappush` (or later in `heappop`). The bug
hides until two jobs share a time, which is common once times are rounded to the minute. Giving `Job` an
`__lt__` would stop the crash but leave the order of ties to chance, because a heap is not stable. A
monotonically increasing submission number as the second element makes every entry distinct, never reaches
the `Job`, and orders ties first-in first-out.

```py
heapq.heappush(self._heap, (job.run_at, next(self._seq), job))   # NOTE: seq is unique, so the Job is never compared
```

**Bug 3: peeking and removing are two steps.** The loop tests `self._heap[0][0] <= now` and, a few lines
later, calls `heappop`. Between the two, another thread can take the same job. With one due job A and one
future job B, two threads both see A at the top; one pops A, and the other, having decided "the top is due",
pops whatever is on top now, which is B, and starts it early. Without the `checkpoint` hook this would
need luck to happen, with it the interleaving is forced. One lock around the whole peek-and-pop loop fixes it,
and `submit` takes the same lock because `heappush` modifies the list that the loop is reading. The threads
are started after the lock is released, since a job's function may itself call `submit`.

```py
with self._lock:                       # NOTE: peek and pop are one step, or two callers share one peek
    now = self.clock()
    while self._heap and self._heap[0][0] <= now:
        self.checkpoint()
        _, _, job = heapq.heappop(self._heap)
```

### Part 2: three bugs

| Test | The class as given | Points to |
| --- | --- | --- |
| one due job; call `run()`, then wait 50 ms | the job stays `PENDING`; a `RuntimeWarning: coroutine ... was never awaited` is raised | bug 1, never scheduled |
| replace `time.sleep` with a recorder; one job due in 5 ms | the recorder is called | bug 2, blocking sleep |
| one job that takes 30 ms; read its status the moment `run()` returns | `PENDING` | bug 3, nothing waits for running jobs |

The first two tests are written so that they do not depend on the third bug: the first waits after `run()`
returns, the second only counts calls. The checks repair the bugs one at a time and show each test turning
green exactly when its own bug is gone.

**Bug 1: `self._execute(job)` only builds a coroutine.** Calling an `async def` function runs none of its
body; it returns a coroutine object, and the body runs only when something awaits it or wraps it in a task. A
bare call statement discards the object, and CPython then warns that it "was never awaited". The dispatch
has to turn the coroutine into a task, which is what makes the event loop run it.

```py
task = asyncio.create_task(self._execute(job))   # NOTE: calling a coroutine function only builds it
```

**Bug 2: `time.sleep` in a coroutine.** The event loop runs on one thread. `time.sleep(poll)` blocks that
thread, so no other task makes progress while it sleeps: dispatched tasks do not start, running jobs do not
resume from their own `await`. With bug 1 repaired, the symptom becomes jobs that start late and stall in
lockstep with `poll`. The replacement `await asyncio.sleep(poll)` suspends only `run()` and hands control back
to the loop. The test detects the bug without measuring time: it records every call to `time.sleep`, and a
correct scheduler makes none.

```py
await asyncio.sleep(self.poll)         # NOTE: time.sleep would freeze every task on the loop
```

**Bug 3: `run()` stops looking at its tasks.** The loop `while self._heap` ends the moment the last job is
dispatched, although that job has only just started. `run()` then returns while jobs are running, and the
caller's `asyncio.run` cancels whatever is left. The tasks are also held nowhere: the event loop keeps only
weak references to tasks, so a task that nothing else references can be garbage-collected before it finishes,
and the documentation of `create_task` asks for a strong reference. The fix keeps every task in a set until it
is done, and loops while the heap or the set is non-empty. Looping, rather than one `gather` after the last
dispatch, also covers a running job that submits another job.

```py
while self._heap or self._tasks:       # NOTE: running jobs count as work; they may submit more
    ...
    self._tasks.add(task)
    task.add_done_callback(self._tasks.discard)
```

### Follow-ups

- Polling wakes up when nothing is due; a `threading.Condition` (or an `asyncio` event) waited on until the
  earliest `run_at` removes both the idle wake-ups and the up-to-`poll` lateness.
- A thread per job is unbounded; a `ThreadPoolExecutor` caps concurrency, and a job's blocking function inside
  the `asyncio` version belongs in `loop.run_in_executor`.
- `time.monotonic` is the right clock for delays; `time.time` or `datetime.now` jumps when the system clock is
  corrected, which fires jobs early or late.
- Cancelling a job is `O(n)` on a heap; marking it cancelled and skipping it when it is popped is `O(1)`.
- `asyncio.TaskGroup` (Python 3.11) gives structured waiting, but it cancels the siblings of a task that
  raises, so the `except Exception` in `_execute` stays.
- Retries with backoff, and persisting the heap so that pending jobs survive a restart.

<details>
<summary>What the classes as given do, the complete files after the fixes, and the checks (runnable)</summary>

```python
# ---- the tests of the two tables, run here against the classes exactly as given ----
import asyncio
import contextlib
import random
import warnings

GivenScheduler, GivenAsyncScheduler = Scheduler, AsyncScheduler


@contextlib.contextmanager
def thread_errors():                    # collects what dying threads would print to stderr
    seen, old = [], threading.excepthook
    threading.excepthook = lambda args: seen.append(args.exc_value)
    try:
        yield seen
    finally:
        threading.excepthook = old


def failing_job(cls):                   # part 1, bug 1
    clock = FakeClock()
    scheduler = cls(clock=clock)
    def boom():
        raise ValueError("boom")
    bad, good = Job(boom, run_at=1), Job(lambda: "fine", run_at=2)
    scheduler.submit(bad)
    scheduler.submit(good)
    clock.advance(2)
    with thread_errors() as seen:
        for thread in scheduler.run_due():
            thread.join(timeout=5)
    return bad.status, type(bad.error), good.status, len(seen)


def equal_run_at(cls):                  # part 1, bug 2
    scheduler = cls(clock=FakeClock(5))
    first, second = Job(lambda: "first", run_at=5), Job(lambda: "second", run_at=5)
    try:
        scheduler.submit(first)
        scheduler.submit(second)
    except TypeError:
        return "TypeError"
    for thread in scheduler.run_due():
        thread.join(timeout=5)
    return [job.result for job in scheduler.started]


def concurrent_run_due(cls, checkpoint, count):   # part 1, bug 3: the same heap seen by several callers
    ran = []
    scheduler = cls(clock=FakeClock(10), checkpoint=checkpoint)
    scheduler.submit(Job(ran.append, args=("due",), run_at=0))
    scheduler.submit(Job(ran.append, args=("early",), run_at=100))    # must not run at time 10
    threads = []
    def call():
        threads.extend(scheduler.run_due())
    callers = [threading.Thread(target=call, daemon=True) for _ in range(count)]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join(timeout=15)
    for thread in threads:
        thread.join(timeout=5)
    return sorted(ran)


def run_async(coro):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = asyncio.run(asyncio.wait_for(coro, 5))        # the timeout keeps a hang from freezing the page
    return out, [str(w.message) for w in caught if issubclass(w.category, RuntimeWarning)]


async def due_job_runs(cls):            # part 2, bug 1
    scheduler = cls(poll=0.001)
    async def work(x):
        return x * 2
    job = Job(work, args=(21,), run_at=scheduler.clock())
    scheduler.submit(job)
    await scheduler.run()
    await asyncio.sleep(0.05)           # lets any task that exists run, so only bug 1 can fail this
    return job.status, job.result


async def blocking_sleeps(cls):         # part 2, bug 2
    calls, real_sleep = [], time.sleep
    time.sleep = calls.append           # a stand-in that records the call and returns at once
    try:
        scheduler = cls(poll=0.001)
        async def work():
            return None
        scheduler.submit(Job(work, run_at=scheduler.clock() + 0.005))
        await scheduler.run()
        await asyncio.sleep(0.05)
    finally:
        time.sleep = real_sleep
    return len(calls)


async def waits_for_running_jobs(cls):  # part 2, bug 3
    scheduler = cls(poll=0.001)
    async def slow():
        await asyncio.sleep(0.03)
        return "ok"
    job = Job(slow, run_at=scheduler.clock())
    scheduler.submit(job)
    await scheduler.run()
    return job.status                    # read the moment run() returns


# the given class, with only the bugs named in the class name repaired
class Bug1Fixed(GivenAsyncScheduler):
    async def run(self):
        while self._heap:
            now = self.clock()
            while self._heap and self._heap[0][0] <= now:
                _, _, job = heapq.heappop(self._heap)
                asyncio.create_task(self._execute(job))
            time.sleep(self.poll)


class Bugs12Fixed(GivenAsyncScheduler):
    async def run(self):
        while self._heap:
            now = self.clock()
            while self._heap and self._heap[0][0] <= now:
                _, _, job = heapq.heappop(self._heap)
                asyncio.create_task(self._execute(job))
            await asyncio.sleep(self.poll)


# part 1 as given
assert failing_job(GivenScheduler) == (Status.PENDING, type(None), Status.COMPLETED, 1)
assert equal_run_at(GivenScheduler) == "TypeError"
assert concurrent_run_due(GivenScheduler, threading.Barrier(2, timeout=10).wait, 2) == ["due", "early"]

# part 2 as given, and with one or two of the bugs repaired: each test turns green exactly when its bug goes
(status, result), warned = run_async(due_job_runs(GivenAsyncScheduler))
assert (status, result) == (Status.PENDING, None) and any("never awaited" in m for m in warned), warned
assert run_async(due_job_runs(Bug1Fixed))[0] == (Status.COMPLETED, 42)
assert run_async(blocking_sleeps(Bug1Fixed))[0] > 0
assert run_async(blocking_sleeps(Bugs12Fixed))[0] == 0
assert run_async(waits_for_running_jobs(GivenAsyncScheduler))[0] is Status.PENDING
assert run_async(waits_for_running_jobs(Bug1Fixed))[0] is Status.PENDING
assert run_async(waits_for_running_jobs(Bugs12Fixed))[0] is Status.PENDING
```

```python
import heapq
import itertools
import threading
import time
from enum import Enum


class Status(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job:
    def __init__(self, func, args=(), kwargs=None, run_at=0.0):
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.run_at = run_at
        self.status = Status.PENDING
        self.result = None
        self.error = None


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class Scheduler:
    def __init__(self, clock=time.monotonic, checkpoint=lambda: None):
        self.clock = clock
        self.checkpoint = checkpoint
        self.started = []
        self._heap = []                # entries (run_at, seq, job)
        self._seq = itertools.count()
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def submit(self, job):
        with self._lock:
            # NOTE: seq is unique, so tuple comparison never reaches the Job; it also keeps equal run_at FIFO
            heapq.heappush(self._heap, (job.run_at, next(self._seq), job))

    def run_due(self):
        due = []
        with self._lock:                       # NOTE: peek and pop are one step, or two callers share one peek
            now = self.clock()
            while self._heap and self._heap[0][0] <= now:
                self.checkpoint()
                _, _, job = heapq.heappop(self._heap)
                self.started.append(job)
                due.append(job)
        threads = []
        for job in due:                        # NOTE: threads start outside the lock; a job may call submit()
            thread = threading.Thread(target=self._run, args=(job,), daemon=True)
            thread.start()
            threads.append(thread)
        return threads

    def _run(self, job):
        try:
            job.result = job.func(*job.args, **job.kwargs)
        except Exception as exc:               # NOTE: Exception, not BaseException: Ctrl-C must still stop us
            job.error = exc
            job.status = Status.FAILED         # NOTE: set last, so a reader who sees a final status sees result/error
        else:
            job.status = Status.COMPLETED

    def start(self, poll=0.01):
        def loop():
            while not self._stop.is_set():
                self.run_due()
                time.sleep(poll)
        self._ticker = threading.Thread(target=loop, daemon=True)
        self._ticker.start()

    def stop(self):
        self._stop.set()
        self._ticker.join(timeout=5)


if __name__ == "__main__":
    clock = FakeClock()
    scheduler = Scheduler(clock=clock)
    job = Job(lambda a, b: a + b, args=(2, 3), run_at=10)
    scheduler.submit(job)
    clock.advance(10)
    for thread in scheduler.run_due():
        thread.join()
    assert job.status is Status.COMPLETED and job.result == 5
    print("smoke test passed")
```

```python
import asyncio
import heapq
import itertools
import time


class AsyncScheduler:
    def __init__(self, clock=time.monotonic, poll=0.01):
        self.clock = clock
        self.poll = poll
        self._heap = []
        self._seq = itertools.count()
        self._tasks = set()            # NOTE: the event loop keeps only weak references to tasks

    def submit(self, job):
        heapq.heappush(self._heap, (job.run_at, next(self._seq), job))

    async def _execute(self, job):
        try:
            job.result = await job.func(*job.args, **job.kwargs)
            job.status = Status.COMPLETED
        except Exception as exc:
            job.error = exc
            job.status = Status.FAILED

    async def run(self):
        while self._heap or self._tasks:       # NOTE: running jobs count as work; they may submit more
            now = self.clock()
            while self._heap and self._heap[0][0] <= now:
                _, _, job = heapq.heappop(self._heap)
                task = asyncio.create_task(self._execute(job))   # NOTE: calling a coroutine function only builds it
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
            await asyncio.sleep(self.poll)     # NOTE: time.sleep would freeze every task on the loop
```

```python
# ---- the same tests against the fixed classes ----
assert failing_job(Scheduler) == (Status.FAILED, ValueError, Status.COMPLETED, 0)
assert equal_run_at(Scheduler) == ["first", "second"]
assert concurrent_run_due(Scheduler, lambda: time.sleep(0), 8) == ["due"]
assert run_async(due_job_runs(AsyncScheduler)) == ((Status.COMPLETED, 42), [])
assert run_async(blocking_sleeps(AsyncScheduler))[0] == 0
assert run_async(waits_for_running_jobs(AsyncScheduler)) == (Status.COMPLETED, [])

# negative control: the fixed scheduler with its lock taken away and callers held between peek and pop
unlocked = Scheduler(clock=FakeClock(10), checkpoint=threading.Barrier(2, timeout=10).wait)
unlocked._lock = contextlib.nullcontext()
unlocked.submit(Job(lambda: None, run_at=0))
unlocked.submit(Job(lambda: None, run_at=100))
racers = []
for _ in range(2):
    racers.append(threading.Thread(target=unlocked.run_due, daemon=True))
    racers[-1].start()
for racer in racers:
    racer.join(timeout=15)
assert [job.run_at for job in unlocked.started] == [0, 100]      # the future job was taken at time 10

# the background ticker runs a job when its time comes on the real clock
real = Scheduler()
job = Job(lambda: "ticked", run_at=real.clock() + 0.03)
real.submit(job)
real.start(poll=0.005)
for _ in range(400):
    if job.status is not Status.PENDING:
        break
    time.sleep(0.005)
real.stop()
assert (job.status, job.result) == (Status.COMPLETED, "ticked")


# ---- cross-check against a model written from the statement alone ----
rng = random.Random(7)
for _ in range(60):
    clock = FakeClock()
    scheduler = Scheduler(clock=clock)
    spec = []                                            # (run_at, raises, job), in submission order
    for i in range(rng.randint(1, 12)):
        raises = rng.random() < 0.3
        def work(i=i, raises=raises):
            if raises:
                raise RuntimeError(i)
            return i
        job = Job(work, run_at=rng.randint(0, 6))
        spec.append((job.run_at, raises, job))
        scheduler.submit(job)
    taken = []
    for now in range(0, 8):
        clock.t = now
        with thread_errors() as seen:
            for thread in scheduler.run_due():
                thread.join(timeout=5)
        assert not seen
        fresh = [(r, i) for i, (r, _, _) in enumerate(spec) if r <= now and i not in taken]
        taken += [i for _, i in sorted(fresh)]           # by run_at, then by submission order
        assert [spec[i][2] for i in taken] == scheduler.started
    for i, (_, raises, job) in enumerate(spec):
        assert job.status is (Status.FAILED if raises else Status.COMPLETED), i
        assert (isinstance(job.error, RuntimeError)) == raises and (job.result == i) == (not raises)


class SteppingClock:
    """Reads 0, 1, 2, ...: one tick per look at the clock, so no real waiting is involved."""

    def __init__(self):
        self.t = -1

    def __call__(self):
        self.t += 1
        return self.t


async def model_run(rng):
    clock = SteppingClock()
    scheduler = AsyncScheduler(clock=clock, poll=0)
    began, spec = [], []
    for i in range(rng.randint(1, 12)):
        raises = rng.random() < 0.3
        async def work(i=i, raises=raises):
            began.append(i)
            for _ in range(rng.randint(0, 3)):
                await asyncio.sleep(0)
            if raises:
                raise RuntimeError(i)
            return i
        job = Job(work, run_at=rng.randint(0, 6))
        spec.append((job.run_at, raises, job))
        scheduler.submit(job)
    await scheduler.run()
    assert not scheduler._heap and not scheduler._tasks
    assert began == [i for _, i in sorted((r, i) for i, (r, _, _) in enumerate(spec))]
    for i, (_, raises, job) in enumerate(spec):
        assert job.status is (Status.FAILED if raises else Status.COMPLETED), i
        assert (isinstance(job.error, RuntimeError)) == raises and (job.result == i) == (not raises)


async def many_runs():
    rng = random.Random(11)
    for _ in range(60):
        await model_run(rng)


asyncio.run(asyncio.wait_for(many_runs(), 20))

# a job may submit another job and run() still waits for it
async def chained():
    scheduler = AsyncScheduler(poll=0.001)
    async def second():
        return "second"
    follow = Job(second, run_at=scheduler.clock())
    async def first():
        scheduler.submit(follow)
        return "first"
    lead = Job(first, run_at=scheduler.clock())
    scheduler.submit(lead)
    await scheduler.run()
    return lead.status, follow.status, follow.result


assert asyncio.run(asyncio.wait_for(chained(), 5)) == (Status.COMPLETED, Status.COMPLETED, "second")

print("all checks passed")
```

</details>

</details>
