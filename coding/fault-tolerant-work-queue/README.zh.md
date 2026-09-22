# 容错工作队列

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | Infra Eng | queue, state-machine, retry | 3 个部分 |
<!-- meta:end -->

## 题目

一个*工作队列*（work queue）存放任务，供工人（worker）领取、处理并报告结果。每个任务在提交时带有一个调用方
指定的 `task_id`（在所有提交过的任务里唯一）和一个不透明的 `payload`（队列不检查它的内容）。工人由字符串
`worker_id` 标识。

每一次公开方法调用都是原子的：不会有两次调用相互交错执行。任务在一个小型状态机中流转，这一部分只需要其中
三种状态：

| 状态 | 含义 |
| --- | --- |
| `ready` | 已提交，当前不被任何工人持有，可以被 `reserve` |
| `reserved` | 被某个工人持有，正在处理 |
| `completed` | 已成功处理完毕，终止状态 |

### Part 1 —— 预约、完成与失败

`submit(task_id, payload)` 新建一个 `ready` 状态的任务。如果 `task_id` 之前已经提交过，抛出 `ValueError`。

`reserve(worker_id)` 从当前处于 `ready` 的任务中，把最早进入 `ready` 的那一个交给调用它的工人——先进先出，
不论一个任务是靠刚提交进入 `ready`，还是靠被放回而进入 `ready`。它把这个任务变为 `reserved`，返回一个
`Reservation`，其中带有 `task_id`、`payload`，以及一个全新的*凭证*（token）：这个值只对应“这一次预约这一个
任务”，之后 `complete` 和 `fail` 必须把它带回来。如果没有任何任务处于 `ready`，返回 `None`。

`complete(task_id, token)` 把任务标记为 `completed`。只有当该任务当前处于 `reserved`、且 `token` 与这次
预约签发的 token 相同时才会成功；否则抛出 `InvalidReservationError`。如果 `task_id` 从未被提交过，改为
抛出 `UnknownTaskError`。

`fail(task_id, token)` 对 `token` 的校验规则与 `complete` 完全相同。一旦校验通过，任务就变回 `ready`，
排到队尾。这一部分不限制一个任务可以失败并被重试多少次。

再次预约同一个任务——不论是因为它失败了，还是因为别的什么事件让它变回 `ready`——都会签发一个全新的
token。该任务之前任何一次预约的 token 都不会再对 `complete`/`fail` 生效，哪怕它握在一个仍然以为自己持有
这个任务的工人手里。

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

例子：

```text
q = WorkQueue()
q.submit('t1', 'build')
q.submit('t2', 'test')

r1 = q.reserve('w1')          # r1.task_id == 't1'
r2 = q.reserve('w2')          # r2.task_id == 't2'
q.complete('t1', r1.token)    # 't1' -> completed
q.fail('t2', r2.token)        # 't2' -> ready，排到队尾

r3 = q.reserve('w3')          # r3.task_id == 't2'，又是这个任务，但 token 是新的
q.complete('t2', r2.token)    # 抛出 InvalidReservationError：r2.token 已经失效
q.complete('t2', r3.token)    # 成功
```

### Part 2 —— 租约超时

工人可能在预约了一个任务之后崩溃或者挂起，从此再也不调用 `complete` 或 `fail`。为了限定一个任务最多能卡住
多久，现在每一次预约都带有一个*租约*（lease）：一个过后就视为被放弃的截止时刻。

时间由下面给出的手动时钟提供；队列从不读取系统时间。

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

`WorkQueue` 的构造函数现在还接收 `clock`（一个 `ManualClock`）和一个正整数 `lease_duration`。当 `reserve`
在时刻 `t = clock.now()` 签发一次预约时，它的*租约截止时刻*（lease deadline）是 `t + lease_duration`；这次
预约在这一刻（含）之前始终有效，一旦 `clock.now()` 严格大于这个截止时刻，这次预约就*过期*了。

没有后台线程扫描过期情况。取而代之的是：每次调用 `WorkQueue` 的任何一个方法（包括 `submit`），都先做一轮
*回收*（reclaiming pass）：把此刻已经过期的每一次预约结束掉，效果和对应的工人在这一刻调用了一次 `fail`
完全一样，也就是任务重新进入 `ready`，排到队尾。一轮回收逐个处理过期的预约，按租约截止时刻从早到晚，
截止时刻相同的按 `task_id` 升序。回收完毕之后，这次调用才做它本身的事。

一旦一次预约以这种方式被回收，它的 token 就会在和 Part 1 完全一致的规则下对 `complete`/`fail` 失效——一个
仍然以为自己持有租约的工人调用 `complete`/`fail` 会得到 `InvalidReservationError`，和它跟一次显式的 `fail`
撞车没有区别。

```py
class WorkQueue:
    def __init__(self, clock: "ManualClock", lease_duration: int) -> None: ...
```

例子，`lease_duration = 5`：

```text
t=0  q.submit('t1', 'x')
t=0  rA = q.reserve('A')          # deadline = 0 + 5 = 5，在 t=5 之前（含）都有效
t=7  clock.advance(7)             # 还没有任何调用——过期要到下一次调用才会被发现
t=7  rB = q.reserve('B')          # 先回收 t1（7 > 5）：变回 ready，随即被 B 重新预约
t=7  q.complete('t1', rA.token)   # 抛出 InvalidReservationError
t=7  q.complete('t1', rB.token)   # 成功
```

### Part 3 —— 重试预算与死信队列

构造函数再多接收一个参数：正整数 `max_attempts`。现在每个任务都记着一个*尝试次数*（attempt count），即它
被预约过的次数，提交时为 0。另外多出第四种状态 `dead`，只有 `requeue_dead` 能让任务离开这个状态。

每当一个 `reserved` 的任务在没有完成的情况下离开这个状态——不论是通过 `fail`，还是通过租约过期——就看它的
尝试次数（已经包含刚刚结束的这一次预约）：如果已经达到 `max_attempts`，任务就变为 `dead`，而不是
`ready`；否则和之前一样变为 `ready`。这条规则不影响 `complete`：完成的任务照旧进入终止状态 `completed`。

`dead_letters()` 返回当前处于 `dead` 状态的全部任务的 `task_id`，按它们进入 `dead` 的先后顺序排列。

`requeue_dead(task_id)` 把一个 `dead` 状态的任务放到 `ready` 队列的队尾，并把它的尝试次数清零，就像它刚刚
被提交一样，于是它又有 `max_attempts` 次预约机会。如果 `task_id` 从未被提交过，抛出 `UnknownTaskError`；
如果它当前不处于 `dead`，抛出 `ValueError`。和其它方法一样，`dead_letters` 和 `requeue_dead` 也都先做一轮
回收。

```py
class WorkQueue:
    def __init__(self, clock: "ManualClock", lease_duration: int, max_attempts: int) -> None: ...
    def dead_letters(self) -> list[str]: ...
    def requeue_dead(self, task_id: str) -> None: ...
```

例子，`lease_duration = 3`、`max_attempts = 2`：

```text
t=0  q.submit('t1', 'x')
t=0  rA = q.reserve('A')          # 第 1 次预约
t=0  q.fail('t1', rA.token)       # 目前 1 < 2 次 -> ready
t=0  rB = q.reserve('B')          # 第 2 次预约
t=0  q.fail('t1', rB.token)       # 目前 2 >= 2 次 -> dead
     q.dead_letters()             # -> ['t1']
     q.reserve('C')               # -> None，没有 ready 的任务
     q.requeue_dead('t1')         # 尝试次数清零
     rC = q.reserve('C')          # 又是第 1 次预约
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得跟面试官确认两点：失败、超时或 `requeue_dead` 之后回到 `ready` 的任务，是和新提交的任务共用
一个先进先出顺序，还是有优先级；重试上限数的是预约次数还是重试次数——`max_attempts = 3` 允许预约三次，
“重试 3 次”则允许四次，差一错误多半出在这里。

### Part 1

一个按 `task_id` 索引的字典保存每个任务的权威状态；一个 `deque` 按进入的先后保存处于 `ready` 的
`task_id`：`reserve` 从队首弹出，`submit` 和放回都追加到队尾。`complete` 和 `fail` 共用一次检查
`_lookup_reserved`：未知的 `task_id` 抛出 `UnknownTaskError`；其余情况——错误的 token、已经结束的预约
留下的旧 token、任务根本不处于 `reserved`（包括已 `completed` 的）——都抛出 `InvalidReservationError`，
因为调用方的 token 都不属于任务当前的那次预约。

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

这里还没有堆，所有方法都是 $O(1)$。在这个类上运行 Part 1 的例子：

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

一个按 `(deadline, task_id, token)` 排序的小根堆，弹出租约的顺序正好是一轮回收要求的顺序。堆里的条目
从不直接删除（惰性删除）：`_reclaim_expired` 弹出一个条目时，如果它的 `token` 等于任务*当前*的 token，
说明任务还停在这次预约上，确实过期了；否则任务在此之后已经被完成、失败或重新预约，作废的条目直接
丢掉。设 $n$ 为迄今的方法调用次数，堆里的条目从不超过 $n$ 个。每次预约只 push 一次、最多 pop 一次，
所以 $n$ 次调用在堆上的总开销是 $O(n \log n)$，均摊每次 $O(\log n)$；但一次调用碰上 $k$ 个过期租约时
要付 $O(k \log n)$。

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

在这个类上运行 Part 2 的例子：

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

`fail` 和 `_reclaim_expired` 都经由 `_release` 让任务离开 `reserved`，所以只替换这一个方法，超时就和显式
失败处理得完全一样。

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

`max_attempts = 1` 不需要任何特殊处理：第一次预约就把 `attempts` 记到 `1`，所以只要 `fail` 一次
（或过期一次），任务就直接进入 `dead`。有 $d$ 个死信任务时，`dead_letters` 要把每个 id 拷贝出来，开销是
$O(d)$；`requeue_dead` 里的 `list.remove` 也是 $O(d)$。

### 追问

- 这个队列只保证*至少一次*（at-least-once）投递：租约过期不代表第一个工人真的停了，两个工人可能同时处理
  同一个任务。要让效果恰好一次（exactly-once），副作用本身要幂等，或者在副作用生效的那一刻再核对一次任务
  当前的 token，而不只是在 `complete` 时核对。
- `lease_duration` 太短，会在只是处理得慢的任务上白白耗掉重试预算；太长，崩溃的工人手里的任务又要卡
  更久。加一个 `heartbeat(task_id, token)`，让还活着的工人把截止时刻往后推，租约就能设得短些。
- 队列只在内存里，一次崩溃就丢失全部状态。要持久化，就在每次状态转移作用到内存之前先写日志，重启后重放。

<details>
<summary>验证代码（可运行）</summary>

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
