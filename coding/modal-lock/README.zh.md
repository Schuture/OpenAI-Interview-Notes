# ModalLock 与 FairModalLock

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 · 并发，Python | ★☆☆☆☆ | 困难 | SWE · MLE | concurrency, threading, fairness | 2 个部分 |
<!-- meta:end -->

## 题目

*模式*（mode）是一个字符串，标识一份共享资源当前的用途——例如一块 GPU 此刻是在跑 `"train"`（训练）任务
还是 `"infer"`（推理）任务。`ModalLock` 保护这样一份资源：任意时刻，所有持有这把锁的线程用的都是同一个
模式；只要请求的是同一个模式，任意多个线程可以一起持有它。一个线程如果请求的模式与当前持有的不同，就必须
阻塞，直到当前所有持有者都释放为止。

下面的例子都借助一个小工具 `Rig` 来描述：它可以让一把锁按一个精确选定的到达与释放顺序运行，完全不依赖
sleep 或计时——每一步都会阻塞，直到它对锁造成的效果真正可以被观察到，用 `waiting_count()`（当前处于阻塞
状态的 `acquire()` 调用数，跨所有模式统计）来判断一次调用是真的进入了等待，还是已经立刻被批准。

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

### Part 1 —— ModalLock

`acquire(mode)` 阻塞，直到锁当前的模式要么不存在（锁空闲）要么等于 `mode`；然后把 `mode` 设为当前模式，
把调用者加入持有者集合。`release(mode)` 把调用者从持有者集合中移除；当前模式的最后一个持有者释放后，锁
重新变为空闲。`release(mode)` 在锁当前没有任何持有者、或者当前模式不是 `mode` 时抛出
`ModeMismatchError`——这两种情况都意味着这次调用并不对应它真正持有的任何一次预约。

```py
class ModalLock:
    def __init__(self) -> None: ...
    def acquire(self, mode: str) -> None: ...
    def release(self, mode: str) -> None: ...
    def waiting_count(self) -> int: ...
```

例子，用一把全新的 `ModalLock` 和线程 `a, b, c, d`：`a` 请求 `"train"`（立即获得）；`b` 请求 `"train"`
（加入 `a`）；`c` 请求 `"infer"`（阻塞，因为 `"train"` 正被持有）；`a` 释放（`b` 仍持有 `"train"`，`c`
继续阻塞）；`b` 释放（`"train"` 的持有者归零，`c` 获得 `"infer"`）；`d` 请求 `"infer"`（加入 `c`）。
这六步之后的持有者集合依次是：`{a}`、`{a, b}`、`{a, b}`、`{b}`、`{c}`、`{c, d}`。

### Part 2 —— FairModalLock

`ModalLock` 可能让一个模式永远饿死：只要当前模式不断有新的同模式持有者加入、抢在最后一个持有者释放之前，
锁就永远不会空闲，请求别的模式的线程也就永远轮不到。`FairModalLock` 按请求到达的顺序授予模式，规则如下。

每一次 `acquire(mode)` 调用都会加入一个*批次*（batch）：一串连续到达、请求同一模式、一起被服务的调用。
所有批次排在同一个先进先出的队列里，最早的排在最前面；当前持有锁的批次就留在队列头部。如果调用发现队列
*末尾*的批次请求的正是 `mode`，它就加入那个批次，即使那正是当前持有锁的批次；否则它在队列末尾新建一个
批次。一个批次一到达队列*头部*就被服务——它的全部成员一起成为持有者；加入头部批次的调用也立即成为持有者。
曾经加入过头部批次的成员全部释放之后，这个批次离开队列，下一个批次（如果有）随即被服务。因此，锁空闲时
`acquire(mode)` 立即返回；锁正以 `mode` 被持有、持有者后面又没有排队的批次时，也立即返回；但只要已经有
别的模式的请求在等待，新的 `acquire(mode)` 就要排在它后面，即使 `mode` 正是当前持有的模式。
`release(mode)` 抛出 `ModeMismatchError` 的条件与 `ModalLock.release` 相同：锁当前没有任何持有者，或者
持有者用的不是 `mode`。

```py
class FairModalLock:
    def __init__(self) -> None: ...
    def acquire(self, mode: str) -> None: ...
    def release(self, mode: str) -> None: ...
    def waiting_count(self) -> int: ...
```

下面前三个场景只用到两种模式；“到达”之后的每一列都发生在前一列之后，最后一列按运行顺序列出各个批次，
每个批次写成一起持有锁的名字集合。

| 场景 | 到达（名字:模式） | 释放顺序 | 批次 |
| --- | --- | --- | --- |
| 基本公平性 | a:train, b:infer, c:train | a, b, c | `{a}`、`{b}`、`{c}` |
| 交错到达 | a:train, b:infer, c:train, d:infer, e:train | a, b, c, d, e | `{a}`、`{b}`、`{c}`、`{d}`、`{e}` |
| 同模式扎堆 | a:train，然后 b:infer, c:infer, d:infer | a，然后 b, c, d | `{a}`、`{b, c, d}` |

在“基本公平性”这一行，`c` 请求的模式与 `a` 相同，但不能加入 `a` 正在运行的批次，因为 `b` 已经排在它
后面；`c` 必须排在 `b` 后面等自己的机会。在“同模式扎堆”这一行，三个 `"infer"` 请求都在 `"train"` 被持有
期间排队，`a` 一释放，三个请求就同时成为持有者。

第三种模式能让“不能插队”这条规则在队列两端同时体现出来。用一把全新的 `FairModalLock`：`a` 请求
`"train"`（获得）；`b` 请求 `"infer"`（排队）；`c` 请求 `"export"`（排队）；`d` 请求 `"infer"`（排队——
此时队列末尾的批次是 `c` 的 `"export"` 批次，所以 `d` 不能加入 `b`）；`a` 释放（`b` 的批次运行，持有者
`{b}`）；`e` 请求 `"infer"`（此时队列末尾的批次是 `d` 的，所以 `e` 加入 `d`，而不是 `b`）；`b` 释放
（`c` 的批次运行，持有者 `{c}`）；`c` 释放（`d` 的批次与 `e` 一起运行，持有者 `{d, e}`）；`d`、`e`
依次释放。批次运行的顺序是 `{a}`、`{b}`、`{c}`、`{d, e}`。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得跟面试官确认两点：`acquire` 是否需要支持超时或取消一次尚未完成的等待（这里假设不需要，让
接口保持简单）；模式字符串除了相等比较之外还有没有别的含义（这里假设没有，全程只用 `==` 比较）。

### Part 1

一个 `Condition` 同时守护三样东西：当前模式、持有者数量，以及停在 `wait()` 里的调用数。
`waiting_count()` 汇报的就是最后这一项。在外部观察者看来，一次调用从进入 `wait()` 起被计入，直到获得
批准为止：一次不需要阻塞就被批准的调用会先加一再减一，中途从未释放过 Condition 的内部锁，所以外部观察者
根本看不到这个值变化过。

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

`ModalLock` 会在当前模式始终没有完全排空时让另一个模式饿死。用 `Rig` 重现这一点完全不需要运气：先让一个
`"infer"` 请求到达并停在等待里；然后反复让一个新的 `"train"` 请求抢在上一个 `"train"` 持有者释放*之前*
到达，`_holders` 就永远不会归零，`notify_all()` 也永远不会被调用——被停住的 `"infer"` 请求根本没有醒来
的机会。

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

`_Batch` 记录队列里的一项：它的模式、还有多少调用停在里面等待、有多少成员正持有锁。`acquire` 只检查队列
的*末尾*那一个批次来决定是否加入——如果换成检查“这个模式的批次是否存在于队列的某处”，就会让一个同模式的
后来者插到已经排在正在运行的批次后面的别人前面。一次调用被批准的时刻，正是它所在的批次到达队列头部的那
一刻（`_queue[0] is batch`）；这一个条件已经同时覆盖了锁空闲的情形（空队列里刚追加的批次天然就在头部）和
加入正在运行的批次的情形（批次在活跃期间一直停在下标 0），不需要再单独写一条快速路径。`release` 只在头部
批次的两个计数都归零时才把它移出队列：批次到达头部时被唤醒的成员，可能还没有重新拿到 Condition 的锁
（此时 `active == 0` 而 `waiting > 0`），如果这时把批次移走，这个成员就会一直等一个已经不在队列里的批次。
这里如果把 `notify_all()` 换成 `notify()`，那么只要有批次在到达头部时有两个以上的成员在等待，锁就会卡死：
`notify()` 只唤醒其中一个；它释放之后，批次的 `active == 0` 而 `waiting > 0`，不会被移出队列，也再没有人
调用 `notify`——其余成员以及排在后面的所有批次都会永远等下去。

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

一个批次进入队列之后，排在它前面的每个批次都不再是队尾，因此不会再有新成员加入：它们的成员都是固定的、
有限的。只要每个持有者最终都会调用一次 `release`（这是唯一需要的假设），头部批次就一定会排空并被移出，
接着是下一个，所以每个批次都会在有限个批次之后到达头部，没有哪个模式会被永远拦在外面——这与 `ModalLock`
正相反：在那里，恰恰是一个批次自己的成员源源不断地加入，才让*另一个*批次永远等不到。

### 追问

- 读写锁是它的特例：固定两个模式 `"read"` 和 `"write"`，再加一条规则——`"write"` 批次的成员数永远不能
  超过一个。
- 支持 `acquire(mode, timeout)` 需要让超时的调用在返回前把自己从所在的批次里移除（如果它是自己新建的
  批次，也要一并撤销），而不能只是放弃 `wait()` 就了事。
- `asyncio` 版本把 `Condition.wait()` 换成 `await condition.wait()`；单线程的事件循环让每两个 `await`
  之间的状态改变天然是原子的。
- 跨进程时 `threading.Condition` 不再够用，因为它只活在一个进程的内存里；需要换成 `multiprocessing.Condition`
  并把模式和队列放进共享内存，或者用数据库行锁之类的外部协调者来扮演同样的角色。
- 按优先级而不是严格到达顺序服务模式，会让低优先级模式重新面临饿死的风险，除非再配合老化（aging）
  机制——这正是 `ModalLock` 自己付出的那种代价。

<details>
<summary>验证代码（可运行）</summary>

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
