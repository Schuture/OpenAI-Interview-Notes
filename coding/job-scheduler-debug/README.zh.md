# 任务调度器找 bug

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 调试 · Python | ★☆☆☆☆ | 中等 | SWE · Infra Eng | debugging, concurrency, asyncio, heap, testing | 2 个部分 / 60 分钟 | 现场面 |
<!-- meta:end -->

## 题目

下面给出两个小型任务调度器，一个基于线程，一个基于 `asyncio`。一个*任务*（job）由一个函数、位置参数与关键字参数、
一个 `run_at` 时间（允许它开始运行的最早时钟读数）和一个*状态*（status）组成：在运行结束之前是 `PENDING`；
函数正常返回则为 `COMPLETED`，返回值存入 `result`；函数抛出 `Exception` 则为 `FAILED`，异常存入 `error`。
`clock` 是一个不带参数、返回当前时间（秒）的可调用对象，这样测试可以手动推进时间，不必真的等待。每一部分都有三个
bug，全都在调度器类的内部；用户报告只描述了其中第一个。

### 第一部分：线程版调度器

`submit(job)` 把任务放进按 `run_at` 排序的最小堆（min-heap）。`run_due()` 把所有满足 `run_at <= clock()` 的任务
从堆中取出，并为每个任务启动一个守护线程（daemon thread），返回这些线程。`run_at` 相同的任务按提交顺序启动，
`started` 按任务离开堆的先后顺序记录它们。每个任务必须恰好离开堆一次，且只有到期之后才能离开，即使多个线程同时
调用 `run_due()` 也是如此。`start(poll)` 在后台线程上每隔 `poll` 秒调用一次 `run_due()`，`stop()` 结束这个线程。
`run_due` 在发现某个任务到期之后、把它从堆中取出之前调用 `checkpoint`；`checkpoint` 默认什么也不做，除非测试把它
换掉，于是测试可以把好几个线程按在这个位置上。

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

> **Bug 报告。** 任务的函数一旦抛出异常，这个任务就永远停在 `PENDING`：既不会被标成完成，也不会被标成失败，
> 唯一的痕迹是 stderr 上的一段 traceback。其他看起来都正常。

找出这三个 bug。对每一个，写一个在上面的代码上失败、修复后通过的测试，说明这个 bug 造成了什么、为什么会这样，并用
保持类接口不变的最小改动修复它。

### 第二部分：`asyncio` 版调度器

`Job` 和 `Status` 与第一部分相同，只是 `func` 是一个协程函数（coroutine function）。`submit(job)` 把任务放进按
`(run_at, 提交序号)` 排序的最小堆。`run()` 是一个协程：每隔 `poll` 秒，为每个满足 `run_at <= clock()` 的任务启动
一个 `asyncio` 任务（task）；当堆中没有等待的任务、也没有仍在运行的 task 时返回。`run()` 等待期间，事件循环
（event loop）必须保持空闲，能够运行其他 task。

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

> **Bug 报告。** 我提交了任务并调用 `await scheduler.run()`，却什么也没发生：任务的状态始终是 `PENDING`，
> 我的函数也从没打印过任何东西。Python 打印了一条关于协程的 `RuntimeWarning`，但我看不懂它想让我做什么。

找出这三个 bug，处理方式同第一部分。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得先确认两个约定：函数抛出异常的任务就此终结，状态为 `FAILED` 并保留异常，不重试；`run_at` 相同的任务按
提交顺序启动。下面的测试都不靠真实时间，也不靠碰巧的线程交错：`FakeClock` 让线程版测试结果精确，每读一次就走一格
的时钟让 `asyncio` 版的随机测试同样精确，`checkpoint` 把线程按在竞争发生的那一瞬间。可能睡眠或卡住的测试都套了超时，
所以失败的测试是失败，而不是冻住。

### 第一部分：三个 bug

每一行都是针对公开接口写的测试，修复前后各跑一次。

| 测试 | 原样给出的类 | 指向 |
| --- | --- | --- |
| 时刻 1 的任务抛 `ValueError`，时刻 2 的任务正常；推进到 2 并 join 线程 | 失败的任务仍是 `PENDING`，`error` 为空，它的线程打印了 traceback | bug 1，没有异常处理 |
| 提交两个 `run_at` 相同的任务 | 第二次 `submit` 抛 `TypeError` | bug 2，堆里的元素 |
| 一个已到期、一个未到期的任务；两个线程在 `run_due` 里被按在“是否到期”与“取出”之间 | 两个任务都运行，包括未到期的那个 | bug 3，没有锁 |

**Bug 1：`_run` 默认函数一定会返回。** `job.func(...)` 一旦抛出异常，异常会让 `_run` 提前展开退出，于是
`job.status = Status.COMPLETED` 这一行永远不会执行，也没有别处记录结果。线程带着交给 `threading.excepthook` 的
traceback 结束，后者把它打印出来。此后 `PENDING` 和“还没到时间”无法区分。修复是在调用外面捕获 `Exception`，
保存它，并设置终止状态。其他任务不受影响，因为每个任务有自己的线程。

```py
try:
    job.result = job.func(*job.args, **job.kwargs)
except Exception as exc:               # NOTE: Exception, not BaseException: Ctrl-C must still stop us
    job.error = exc
    job.status = Status.FAILED         # NOTE: set last, so a reader who sees a final status sees result/error
else:
    job.status = Status.COMPLETED
```

**Bug 2：堆里的元素是 `(run_at, job)`。** `heapq` 用 `<` 给元素排序，而元组是逐个元素比较的：只有第一个元素相等时，
Python 才会比较第二个，而 `Job` 没有定义任何顺序，所以两个 `run_at` 相同的任务会在 `heappush`（或之后的
`heappop`）里抛 `TypeError`。这个 bug 要到两个任务共用同一时刻才会冒出来，而时间取整到分钟后这很常见。给 `Job` 加
`__lt__` 能消除崩溃，但相同时刻的顺序依然碰运气，因为堆不是稳定的。把单调递增的提交序号放在第二位，就能让每个
元素互不相同、永远比不到 `Job`，并且让相同时刻的任务先进先出。

```py
heapq.heappush(self._heap, (job.run_at, next(self._seq), job))   # NOTE: seq is unique, so the Job is never compared
```

**Bug 3：查看堆顶与取出是两步。** 循环先判断 `self._heap[0][0] <= now`，几行之后才调用 `heappop`。这两步之间，
别的线程可以把同一个任务取走。设有一个已到期的任务 A 和一个未到期的任务 B，两个线程都看到堆顶是 A；一个线程弹出 A，
另一个线程已经判定“堆顶到期”，于是弹出此刻的堆顶，也就是 B，并把它提前启动。没有 `checkpoint` 钩子时，这需要运气
才会发生；有了它，这种交错就是必然的。用一把锁包住整个“查看并弹出”的循环即可修复；`submit` 也要拿同一把锁，因为
`heappush` 会修改循环正在读取的列表。线程在释放锁之后才启动，因为任务的函数自己也可能调用 `submit`。

```py
with self._lock:                       # NOTE: peek and pop are one step, or two callers share one peek
    now = self.clock()
    while self._heap and self._heap[0][0] <= now:
        self.checkpoint()
        _, _, job = heapq.heappop(self._heap)
```

### 第二部分：三个 bug

| 测试 | 原样给出的类 | 指向 |
| --- | --- | --- |
| 一个已到期的任务；调用 `run()`，然后等 50 ms | 任务仍是 `PENDING`；并出现 `RuntimeWarning: coroutine ... was never awaited` | bug 1，从未被调度 |
| 把 `time.sleep` 换成一个记录器；一个 5 ms 后到期的任务 | 记录器被调用了 | bug 2，阻塞式 sleep |
| 一个耗时 30 ms 的任务；在 `run()` 返回的那一刻读它的状态 | `PENDING` | bug 3，没有任何东西等待运行中的任务 |

前两个测试的写法让它们不依赖第三个 bug：第一个在 `run()` 返回之后再等一会儿，第二个只数调用次数。验证代码按顺序一个个
修复这些 bug，并说明每个测试恰好在它自己的 bug 消失时转绿。

**Bug 1：`self._execute(job)` 只是构造了一个协程。** 调用 `async def` 函数不会执行它的函数体，只返回一个协程对象；
只有被 await 或被包成 task 时，函数体才会运行。裸的调用语句把这个对象丢掉了，CPython 随后警告它“从未被 await”。
调度时必须把协程变成 task，这才会让事件循环去运行它。

```py
task = asyncio.create_task(self._execute(job))   # NOTE: calling a coroutine function only builds it
```

**Bug 2：协程里的 `time.sleep`。** 事件循环跑在一个线程上。`time.sleep(poll)` 阻塞的正是这个线程，所以它睡眠期间没有
任何其他 task 能前进：刚派发的 task 不会开始，正在运行的任务也无法从它自己的 `await` 处恢复。修好 bug 1 之后，症状
就变成任务启动迟缓、随 `poll` 同步卡顿。换成 `await asyncio.sleep(poll)` 只挂起 `run()` 本身，把控制权还给事件循环。
测试不测量时间就能发现这个 bug：它记录每一次对 `time.sleep` 的调用，而正确的调度器一次也不会调用。

```py
await asyncio.sleep(self.poll)         # NOTE: time.sleep would freeze every task on the loop
```

**Bug 3：`run()` 不再关心自己的 task。** 循环 `while self._heap` 在最后一个任务刚被派发的那一刻就结束了，而这个任务
才刚刚开始。于是 `run()` 在任务还在运行时就返回了，调用方的 `asyncio.run` 会把剩下的 task 全部取消。这些 task 也没有
被任何地方持有：事件循环只对 task 保留弱引用，因此没有别的引用的 task 可能在运行完之前就被垃圾回收，`create_task` 的
文档也要求保留强引用。修复是把每个 task 放进一个集合，直到它完成为止，并在堆或集合非空时继续循环。用循环而不是在最后
一次派发后做一次 `gather`，还能覆盖运行中的任务又提交了新任务的情形。

```py
while self._heap or self._tasks:       # NOTE: running jobs count as work; they may submit more
    ...
    self._tasks.add(task)
    task.add_done_callback(self._tasks.discard)
```

### 追问

- 轮询会在没有任务到期时白白醒来；改为在 `threading.Condition`（或 `asyncio` 的 event）上一直等到最早的 `run_at`，
  既能去掉空转唤醒，也能去掉最多 `poll` 的延迟。
- 每个任务一个线程没有上限；`ThreadPoolExecutor` 可以限制并发数，`asyncio` 版里任务中的阻塞函数应该放进
  `loop.run_in_executor`。
- 计算延迟应使用 `time.monotonic`；`time.time` 或 `datetime.now` 会在系统时间被校正时跳变，使任务提前或推迟触发。
- 在堆里取消一个任务是 `O(n)`；标记为已取消、弹出时再跳过则是 `O(1)`。
- `asyncio.TaskGroup`（Python 3.11）提供结构化的等待，但它会在某个 task 抛异常时取消其兄弟 task，所以 `_execute` 里的
  `except Exception` 仍要保留。
- 带退避的重试，以及把堆持久化，使等待中的任务能在重启后保留。

<details>
<summary>原样给出的类的运行结果、修复后的完整文件与验证代码（可运行）</summary>

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
