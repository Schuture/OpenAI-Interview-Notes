# 容错工作队列

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 中等 | SWE · Infra Eng | queue, state-machine, retry | 4 个部分 |
<!-- meta:end -->

## 题目

一个*工作队列*（work queue）存放任务，供工人（worker）领取、处理并报告结果。每个任务在提交时带有一个调用方
指定的 `task_id`（在所有提交过的任务里唯一）和一个不透明的 `payload`（队列不检查它的内容）。工人由字符串
`worker_id` 标识。一次运行里，对下面这些方法的调用总数不超过 $2 \times 10^5$。

每一次公开方法调用都是原子的：不会有两次调用相互交错执行。任务在一个小型状态机中流转，这一部分只需要其中
三种状态：

| 状态 | 含义 |
| --- | --- |
| `ready` | 已提交，当前不被任何工人持有，可以被 `reserve` |
| `reserved` | 被某个工人持有，正在处理 |
| `completed` | 已成功处理完毕，终止状态 |

### Part 1 —— 预约、完成与失败

`submit(task_id, payload)` 新建一个 `ready` 状态的任务。如果 `task_id` 之前已经提交过，抛出 `ValueError`。

每一次被接受的 `submit` 都会给它的任务一个*提交序号*（submission number）：第一个任务为 1，第二个为 2，依此
类推。任务的提交序号终生不变。

`reserve(worker_id)` 从当前处于 `ready` 的任务中，把提交序号最小的那一个交给调用它的工人——按最初提交的顺序
先进先出，不论一个任务是靠刚提交进入 `ready`，还是靠被放回而进入 `ready`。它把这个任务变为 `reserved`，返回一个
`Reservation`，其中带有 `task_id`、`payload`，以及一个全新的*凭证*（token）：这个值只对应“这一次预约这一个
任务”，之后 `complete` 和 `fail` 必须把它带回来。如果没有任何任务处于 `ready`，返回 `None`。

`complete(task_id, token)` 把任务标记为 `completed`。只有当该任务当前处于 `reserved`、且 `token` 与这次
预约签发的 token 相同时才会成功；否则抛出 `InvalidReservationError`。如果 `task_id` 从未被提交过，改为
抛出 `UnknownTaskError`。

`fail(task_id, token)` 对 `token` 的校验规则与 `complete` 完全相同。一旦校验通过，任务就变回 `ready`，
提交序号不变，所以 `reserve` 会把它排在所有比它晚提交的 ready 任务之前。这一部分不限制一个任务可以失败并被重试多少次。

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
q.submit('t3', 'deploy')

r1 = q.reserve('w1')          # r1.task_id == 't1'
r2 = q.reserve('w2')          # r2.task_id == 't2'
q.complete('t1', r1.token)    # 't1' -> completed
q.fail('t2', r2.token)        # 't2' -> ready；它的序号 2 仍小于 't3' 的 3

r3 = q.reserve('w3')          # r3.task_id == 't2'（不是 't3'），又是这个任务，但 token 是新的
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
`lease_duration` 和时钟返回的每个读数都不超过 $10^9$。

没有后台线程扫描过期情况。取而代之的是：每次调用 `WorkQueue` 的任何一个方法（包括 `submit`），都先做一轮
*回收*（reclaiming pass）：把此刻已经过期的每一次预约结束掉，效果和对应的工人在这一刻调用了一次 `fail`
完全一样，也就是任务重新进入 `ready`，提交序号不变。一轮回收逐个处理过期的预约，按租约截止时刻从早到晚，
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

`requeue_dead(task_id)` 把一个 `dead` 状态的任务放回 `ready`，提交序号不变，并把它的尝试次数清零，于是它
又有 `max_attempts` 次预约机会。如果 `task_id` 从未被提交过，抛出 `UnknownTaskError`；
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

### Part 4 —— 依赖

`submit` 多接收第三个参数 `depends_on`：一个 `task_id` 的序列，默认为空，给出该任务的*依赖*（dependency）。当
一个任务的每个依赖都已 `completed` 时，它就是*已解除阻塞*的（unblocked）；没有依赖的任务始终已解除阻塞。
`depends_on` 至多含 10 个 id，同一个 id 出现两次只算一次。

- `depends_on` 里的每个 id 都必须属于之前已提交的任务，否则 `submit` 抛出 `UnknownTaskError`。由于一个任务只能
  依赖在它之前提交的任务，依赖图中没有环。如果 `task_id` 本身已经提交过，仍然抛出 `ValueError`，并且这项
  检查先做。
- 只要有一个依赖当前处于 `dead`，`submit` 就抛出 `ValueError`。被拒绝的 `submit` 不改变任何状态。
- `reserve` 从既处于 `ready`、*又*已解除阻塞的任务中，交出提交序号最小的那一个。仍被阻塞的 `ready` 任务被跳过，
  它的位置保持不变，等解除阻塞后再按序号参与竞争。没有符合条件的任务时返回 `None`。
- 依赖处于 `dead` 的任务永远无法解除阻塞，所以它也是 `dead`。每当一个任务变为 `dead`（经由 `fail` 或租约
  过期），所有直接或经由依赖链依赖于它、且尚未 `dead` 的任务在同一步里一起变为 `dead`：先是该任务本身，
  再是其余任务，按提交序号从小到大。它们的尝试次数保持不变。`dead_letters()` 按任务变为 `dead` 的先后顺序列出，
  这些任务也包括在内。
- `requeue_dead(task_id)` 遵循 Part 3，并且在该任务的任一依赖当前处于 `dead` 时额外抛出 `ValueError`。它只复活这
  一个任务：与它一同死亡的任务仍是 `dead`，要等它们自己的依赖不再 `dead` 之后各自再被 requeue。

```py
class WorkQueue:
    def submit(self, task_id: str, payload: Any, depends_on: "Sequence[str]" = ()) -> None: ...
```

例子，`lease_duration = 10`、`max_attempts = 2`。任务 `c` 和 `e` 依赖 `a`，`d` 依赖 `b` 和 `c`，`f` 依赖 `d`：

```text
q.submit('a', 'x');  q.submit('b', 'x')                  # 提交序号 1、2
q.submit('c', 'x', depends_on=['a'])                     # 3
q.submit('d', 'x', depends_on=['b', 'c'])                # 4
q.submit('e', 'x', depends_on=['a'])                     # 5
q.submit('f', 'x', depends_on=['d'])                     # 6

rA = q.reserve('w1')              # 'a'
rB = q.reserve('w2')              # 'b'
q.reserve('w3')                   # None：c、d、e、f 都被阻塞
q.complete('a', rA.token)         # c 和 e 解除阻塞
rC = q.reserve('w1')              # 'c'，序号 3 < 5
q.fail('b', rB.token)             # 目前 1 < 2 次 -> ready
rB2 = q.reserve('w2')             # 又是 'b'，序号 2 < 5
q.complete('c', rC.token)         # d 仍在等 b
rE = q.reserve('w1')              # 'e'
q.reserve('w3')                   # None：d 和 f 被阻塞
q.fail('b', rB2.token)            # 目前 2 >= 2 次 -> dead；d 和 f 随之 dead
q.dead_letters()                  # -> ['b', 'd', 'f']
q.requeue_dead('d')               # 抛出 ValueError：b 是 dead
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得跟面试官确认两点：失败、超时或 `requeue_dead` 之后回到 `ready` 的任务，是排到目前所有排队任务
之后，还是保留它在提交顺序中的原位置（题目规定为后者）；重试上限数的是预约次数还是重试次数——`max_attempts = 3` 允许预约三次，
“重试 3 次”则允许四次，差一错误多半出在这里。

### Part 1

一个按 `task_id` 索引的字典保存每个任务的权威状态，其中包括提交序号 `seq`；一个由 `(seq, task_id)` 组成的
小根堆保存处于 `ready` 的任务：`reserve` 弹出最小的，`submit` 和每次回到 `ready` 都 push。放回的任务用它自己
原来的 `seq` 入堆，所以它会排在所有比它晚提交的任务之前；用 `deque` 追加到队尾的先进先出做法在这里是错的。
`complete` 和 `fail` 共用一次检查
`_lookup_reserved`：未知的 `task_id` 抛出 `UnknownTaskError`；其余情况——错误的 token、已经结束的预约
留下的旧 token、任务根本不处于 `reserved`（包括已 `completed` 的）——都抛出 `InvalidReservationError`，
因为调用方的 token 都不属于任务当前的那次预约。

```python
import heapq
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
    __slots__ = ("payload", "status", "attempts", "token", "deadline", "seq")

    def __init__(self, payload, seq):
        self.payload = payload
        self.seq = seq                              # submission number: fixed for the task's whole life
        self.status = "ready"
        self.attempts = 0
        self.token = None
        self.deadline = None


class WorkQueue:
    def __init__(self):
        self._tasks: dict[str, _Task] = {}
        self._ready = []                            # min-heap of (seq, task_id)
        self._next_token = 0

    def submit(self, task_id, payload):
        self._reclaim_expired()                     # NOTE: submit reclaims too, so expired tasks re-enter ready before this one is added
        if task_id in self._tasks:
            raise ValueError(f"duplicate task_id {task_id!r}")
        seq = len(self._tasks)                      # NOTE: rejected submits add nothing, so numbers stay consecutive
        self._tasks[task_id] = _Task(payload, seq)
        heapq.heappush(self._ready, (seq, task_id))

    def reserve(self, worker_id):
        self._reclaim_expired()
        if not self._ready:
            return None
        _, task_id = heapq.heappop(self._ready)
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
        heapq.heappush(self._ready, (task.seq, task_id))    # NOTE: the ORIGINAL seq, not a fresh one -- appending to a FIFO would put it behind newer tasks

    def _reclaim_expired(self):                       # NOTE: no-op until Part 2 gives it a real body
        pass
```

每次 `submit`、`reserve` 和回到 `ready` 都是一次堆操作，对 $n$ 个任务为 $O(\log n)$；`complete` 是 $O(1)$。在这个类上运行 Part 1 的例子：

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

一个按 `(deadline, task_id, token)` 排序的小根堆，弹出租约的顺序正好是一轮回收要求的顺序。堆里的条目
从不直接删除（惰性删除）：`_reclaim_expired` 弹出一个条目时，如果它的 `token` 等于任务*当前*的 token，
说明任务还停在这次预约上，确实过期了；否则任务在此之后已经被完成、失败或重新预约，作废的条目直接
丢掉。设 $n$ 为迄今的方法调用次数，堆里的条目从不超过 $n$ 个。每次预约只 push 一次、最多 pop 一次，
所以 $n$ 次调用在堆上的总开销是 $O(n \log n)$，均摊每次 $O(\log n)$。

```python
def __init__(self, clock, lease_duration):
    self._clock = clock
    self._lease_duration = lease_duration
    self._tasks: dict[str, _Task] = {}
    self._ready = []           # min-heap of (seq, task_id)
    self._next_token = 0
    self._leases = []          # min-heap of (deadline, task_id, token)


WorkQueue.__init__ = __init__


def reserve(self, worker_id):
    self._reclaim_expired()
    if not self._ready:
        return None
    _, task_id = heapq.heappop(self._ready)
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
    self._ready = []
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
        heapq.heappush(self._ready, (task.seq, task_id))


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
    heapq.heappush(self._ready, (task.seq, task_id))     # NOTE: back under its original seq, not at the back of the line


WorkQueue.requeue_dead = requeue_dead
```

`max_attempts = 1` 不需要任何特殊处理：第一次预约就把 `attempts` 记到 `1`，所以只要 `fail` 一次
（或过期一次），任务就直接进入 `dead`。

### Part 4

每个任务保存它去重后的依赖 id，以及 `pending`：其中尚未 `completed` 的个数。任务字典之外再有一个反向边映射，把
每个任务映射到由它的依赖者构成的字典。于是：

- 就绪堆现在只放处于 `ready` 且 `pending == 0` 的任务，所以 `reserve` 不用改：堆顶就是最早提交的、已解除阻塞的
  任务。入堆的时机有：提交或 requeue 时 `pending == 0`；一次预约结束后回到 `ready`（那时它已解除阻塞）；
  以及 `complete` 把某个任务的 `pending` 减到 0。
- `complete` 对完成的任务沿反向边走一遍，然后把这些边丢掉。
- 一个任务变为 `dead` 时，沿反向边做一次 DFS，把每个尚未 `dead` 的依赖者恰好杀一次，再按 `seq` 排序后接在该任务
  之后。垂死任务的依赖者 `pending` 都不为 0，所以它们都不在堆里，也就不用从堆里删除任何东西。
- `requeue_dead` 只为这一个任务重建 `pending` 和边；两者都是幂等的。

设 $n$ 为调用次数。每条边都由一次 `submit` 或 `requeue_dead` 调用加入（每次至多 10 条），且最多被删除一次。每次
死亡，不论直接死亡还是级联死亡，都结束了由这样一次调用开启的一段存活期。因此总开销是 $O(n \log n)$，单次
`reserve` 仍是 $O(\log n)$。

```python
class _Task:
    __slots__ = ("payload", "status", "attempts", "token", "deadline", "seq", "deps", "pending")

    def __init__(self, payload, seq, deps):
        self.payload = payload
        self.seq = seq
        self.status = "ready"
        self.attempts = 0
        self.token = None
        self.deadline = None
        self.deps = deps           # distinct dependency ids
        self.pending = 0           # how many of them are not yet completed


def __init__(self, clock, lease_duration, max_attempts):
    self._clock = clock
    self._lease_duration = lease_duration
    self._max_attempts = max_attempts
    self._tasks: dict[str, _Task] = {}
    self._ready = []           # min-heap of (seq, task_id): ready tasks whose pending == 0, and only those
    self._dead = []
    self._next_token = 0
    self._leases = []
    self._dependents: dict[str, dict[str, None]] = {}    # reverse edges: task_id -> its not-yet-dead dependants


WorkQueue.__init__ = __init__


def _link(self, task_id, task):
    task.pending = 0
    for dep_id in task.deps:
        if self._tasks[dep_id].status != "completed":
            task.pending += 1
            self._dependents.setdefault(dep_id, {})[task_id] = None    # NOTE: a dict, so linking twice is harmless
    if task.pending == 0:
        heapq.heappush(self._ready, (task.seq, task_id))


WorkQueue._link = _link


def submit(self, task_id, payload, depends_on=()):
    self._reclaim_expired()
    if task_id in self._tasks:
        raise ValueError(f"duplicate task_id {task_id!r}")
    deps = tuple(dict.fromkeys(depends_on))          # NOTE: a repeated id must count once, or pending never reaches 0
    for dep_id in deps:
        if dep_id not in self._tasks:                # NOTE: task_id itself is not stored yet, so a self-dependency lands here too
            raise UnknownTaskError(dep_id)
    for dep_id in deps:
        if self._tasks[dep_id].status == "dead":
            raise ValueError(f"dependency {dep_id!r} is dead")
    task = _Task(payload, len(self._tasks), deps)    # NOTE: validate everything above first -- a rejected submit must change nothing
    self._tasks[task_id] = task
    self._link(task_id, task)


WorkQueue.submit = submit


def complete(self, task_id, token):
    task = self._lookup_reserved(task_id, token)
    task.status, task.token, task.deadline = "completed", None, None
    for child_id in self._dependents.pop(task_id, ()):    # each edge is used once: its source is now final
        child = self._tasks[child_id]
        if child.status == "ready":                  # NOTE: a dead child is skipped -- requeue_dead recounts from scratch
            child.pending -= 1
            if child.pending == 0:
                heapq.heappush(self._ready, (child.seq, child_id))


WorkQueue.complete = complete


def _release(self, task_id, task):
    task.token, task.deadline = None, None
    if task.attempts < self._max_attempts:
        task.status = "ready"                        # NOTE: pending is 0 here -- it was reserved -- so it goes straight back on the heap
        heapq.heappush(self._ready, (task.seq, task_id))
        return
    task.status = "dead"
    self._dead.append(task_id)
    doomed, stack = [], [task_id]
    while stack:
        for child_id in self._dependents.pop(stack.pop(), ()):     # edges out of a dead task are dropped; requeue_dead re-adds them
            child = self._tasks[child_id]
            if child.status != "dead":
                child.status = "dead"                # NOTE: marked at once, so a child reachable by two paths is collected once
                doomed.append(child_id)
                stack.append(child_id)
    doomed.sort(key=lambda child_id: self._tasks[child_id].seq)    # NOTE: the DFS order is arbitrary; the statement says ascending seq
    self._dead.extend(doomed)


WorkQueue._release = _release


def requeue_dead(self, task_id):
    self._reclaim_expired()
    task = self._tasks.get(task_id)
    if task is None:
        raise UnknownTaskError(task_id)
    if task.status != "dead":
        raise ValueError(f"{task_id!r} is not in the dead-letter queue")
    if any(self._tasks[dep_id].status == "dead" for dep_id in task.deps):
        raise ValueError(f"{task_id!r} has a dead dependency")     # NOTE: otherwise a ready task could wait on a dead one forever
    self._dead.remove(task_id)
    task.status, task.attempts = "ready", 0
    self._link(task_id, task)


WorkQueue.requeue_dead = requeue_dead
```

在这个类上运行 Part 4 的例子：

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

### 追问

- 这个队列只保证*至少一次*（at-least-once）投递：租约过期不代表第一个工人真的停了，两个工人可能同时处理
  同一个任务。要让效果恰好一次（exactly-once），副作用本身要幂等，或者在副作用生效的那一刻再核对一次任务
  当前的 token，而不只是在 `complete` 时核对。
- `lease_duration` 太短，会在只是处理得慢的任务上白白耗掉重试预算；太长，崩溃的工人手里的任务又要卡
  更久。加一个 `heartbeat(task_id, token)`，让还活着的工人把截止时刻往后推，租约就能设得短些。
- 队列只在内存里，一次崩溃就丢失全部状态。要持久化，就在每次状态转移作用到内存之前先写日志，重启后重放。
- 给每个任务加一个 `cooldown`：失败或过期的任务要到 `failure_time + cooldown` 才能再次被预约，提交序号仍保持
  不变。把它放进按释放时刻排序的第二个小根堆，在每次调用的回收之后，把所有已到期的条目移入就绪堆；级联死亡
  不应碰那些还没 `dead` 的暂存任务。

<details>
<summary>验证代码（可运行）</summary>

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
