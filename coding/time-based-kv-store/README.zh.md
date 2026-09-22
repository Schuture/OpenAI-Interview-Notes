# 按时间点查询的 KV 存储

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | binary-search, testing, concurrency | 4 个部分 |
<!-- meta:end -->

## 题目

一个 `TimeMap` 为一组字符串 key 各自记录它随时间变化的取值历史。*时间戳*（timestamp）是一个实数（`int`
或 `float`），数值越大表示时间越晚。完成下面四个部分。

### Part 1 —— 基本实现

`TimeMap()` 创建一个空的存储。

`set(key, value, timestamp)` 记录“在 `timestamp` 这一刻，`key` 的值是 `value`”。一个 key 可以在不同的
时间戳上记录任意多个值，并且对同一个 key，调用不要求按 `timestamp` 递增的顺序到达：一次时间戳较早的调用
可能发生在一次时间戳较晚的调用已经被记录之后。

`get(key, timestamp)` 在目前为止为 `key` 记录的全部值里，返回时间戳不超过 `timestamp` 且最大的那一个。
如果 `key` 从未被 `set` 过，或者为 `key` 记录的所有时间戳都比查询的时间戳大，`get` 返回 `None`。

如果两次 `set` 调用用的是同一个 `key` 和完全相同的 `timestamp`，`get` 在这个时间戳上采用的是两次调用中
较后发生的那一次（按 `set` 被调用的先后顺序），就好像较早的那次调用从未发生过一样。

```py
from typing import Any


class TimeMap:
    def __init__(self) -> None: ...
    def set(self, key: str, value: Any, timestamp: float) -> None: ...
    def get(self, key: str, timestamp: float) -> Any | None: ...
```

例子：

```text
tm = TimeMap()
tm.set("probe-1", 68.0, 100.0)
tm.set("probe-1", 71.5, 140.0)
tm.get("probe-1", 130.0)          # -> 68.0   （130.0 及之前记录的最新值）
tm.get("probe-1", 90.0)           # -> None   （90.0 及之前还没有任何记录）
tm.get("probe-2", 140.0)          # -> None   （从未 set 过的 key）
tm.set("probe-1", 65.0, 120.0)    # 在 140.0 那次调用之后才到达，但时间戳更早
tm.get("probe-1", 130.0)          # -> 65.0   （现在 130.0 及之前最近的值是它）
tm.set("probe-1", 70.0, 140.0)    # 与之前一次调用的时间戳相同
tm.get("probe-1", 140.0)          # -> 70.0   （较晚的那次调用生效）
```

### Part 2 —— 可测试性

测试 `TimeMap` 不应该依赖真实时钟：调用 `time.time()` 的测试每次运行都会拿到不同的时间戳，用
`time.sleep` 隔开两次调用又会让测试变慢。

`TimeMap` 的构造函数接受一个可选的*时钟*（clock）：任何带有 `now() -> float` 方法的对象。`set` 和
`get` 的 `timestamp` 参数都是可选的；省略它（或显式传 `None`）时，调用改用 `clock.now()` 代替。只要
显式传入了 `timestamp`，不论有没有注入时钟，它都优先于时钟生效。不传入时钟时，`TimeMap` 退回到一个
调用真实 `time.time()` 的默认时钟。

测试用下面这个手动时钟，它从不读取真实时间：

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

例子：

```text
clock = ManualClock(start=1000.0)
tm = TimeMap(clock=clock)
tm.set("probe-1", 68.0)            # 时间戳默认取 clock.now() == 1000.0
clock.advance(40.0)
tm.set("probe-1", 71.5)            # 时间戳默认取 clock.now() == 1040.0
tm.get("probe-1")                  # 时间戳默认取 clock.now() == 1040.0 -> 71.5
tm.get("probe-1", 1000.0)          # 显式传入的时间戳优先于时钟 -> 68.0
```

### Part 3 —— 保证时间戳严格递增

从这一部分起，为同一个 key 记录下来的时间戳必须严格递增。对 key `key`，设 `last(key)` 是目前为止为它
记录过的最大时间戳（在它第一次被 `set` 之前，`last(key)` 未定义）。调用 `set(key, value, timestamp)`
时——不论 `timestamp` 是显式传入的，还是来自 `clock.now()`——最终记录下来的时间戳是：

- 如果 `last(key)` 未定义，或者 `timestamp` 严格大于 `last(key)`，就照 `timestamp` 本身记录；
- 否则记为 `last(key) + 1`——这既涵盖时钟发生回拨的情况，也涵盖调用方显式传入一个不比上次更大的
  `timestamp` 的情况。

这条约束以及这条调整规则，对每个 key 各自独立生效；写入次数少的 key 和写入次数多的 key 互不比较。
这取代了 Part 1 里针对“时间戳不大于该 key 上一次记录值”的两条规则：这样的调用不再插入到某个已有条目
之前，也不再覆盖同一时间戳上的条目——它总是被追加，追加时用的时间戳按这条规则计算得到。从这一部分起，
`set` 返回它实际记录下来的时间戳，这个值可能与 `timestamp` 参数不同。

```py
class TimeMap:
    def __init__(self, clock: Any = None) -> None: ...
    def set(self, key: str, value: Any, timestamp: float | None = None) -> float: ...
    def get(self, key: str, timestamp: float | None = None) -> Any | None: ...
```

例子：

```text
clock = ManualClock(start=100.0)
tm = TimeMap(clock=clock)
tm.set("probe-1", 68.0)            # -> 100.0   （clock.now()）
tm.set("probe-1", 70.0, 100.0)     # 显式传入的 100.0 不大于 last（100.0）-> 记为 101.0
tm.get("probe-1", 100.0)           # -> 68.0    （100.0 上仍是第一个值）
tm.get("probe-1", 101.0)           # -> 70.0
clock.advance(-50.0)               # 时钟回拨：now() == 50.0
tm.set("probe-1", 65.0)            # 50.0 不大于 last（101.0）-> 记为 102.0
tm.get("probe-1", 102.0)           # -> 65.0
```

### Part 4 —— 并发访问

多个线程可能同时对同一个存储调用 `set` 和 `get`，可能针对同一个 key，也可能针对不同的 key，调度方式
和交错顺序不受限制。实现 `ThreadSafeTimeMap`，它提供与 Part 3 的 `TimeMap` 相同的 `set`/`get` 语义
（包括那条严格递增规则），并且额外保证下面三条，对任意线程数和任意调度都要成立：

1. 每一次 `set` 或 `get` 调用都表现得像是在单个瞬间生效，省略了 `timestamp` 的调用也在这一瞬间读取
   `clock.now()`：存储的内部状态永远不会被留在不一致的状态（对给定的 key，记录下来的时间戳始终严格递增，
   并且记录的时间戳个数与记录的值个数始终相等），也不会有调用仅仅因为另一个线程的并发调用而抛出异常。
2. `get(key, ...)` 返回的每一个值，要么是 `None`，要么正好是某次对 `key` 调用 `set` 时传入的 `value`
   参数——绝不会把一次 `set` 调用的值，和另一次 `set` 调用记录的时间戳配成一对。
3. 多个线程同时对同一个 key 调用 `set` 时，Part 3 的严格递增规则依然成立：不论它们的调用实际按什么
   顺序生效，为该 key 记录下来的时间戳序列始终严格递增。

至少实现并比较两种加锁策略：一把锁覆盖整个存储；以及每个 key 各自一把锁，在这个 key 第一次被访问时
才创建。如果你还考虑了一种能让并发 `get` 调用同时进行的读写锁，说明它在这里是否真的有用。

```py
class ThreadSafeTimeMap:
    def __init__(self, clock: Any = None) -> None: ...
    def set(self, key: str, value: Any, timestamp: float | None = None) -> float: ...
    def get(self, key: str, timestamp: float | None = None) -> Any | None: ...
```

例子：

```text
线程 A: set("probe-1", 71.5)       # 不显式传时间戳；对两个线程来说 clock.now() == 1040.0
线程 B: set("probe-1", 69.0)       # A 和 B 同时运行，先后不定

# 不论哪次调用先生效，"probe-1" 最终都有两个严格递增的时间戳，例如 1040.0 和 1041.0，
# 绝不会有两个条目都在 1040.0。
get("probe-1", 1041.0)  # -> 71.5 或 69.0，即 A、B 中后生效的那一次写入的值，不会是别的
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前有两点值得确认：没有匹配时 `get` 返回什么（这里选 `None` 而不是空字符串，因为值不一定是字符串）；
“严格递增”是每个 key 各自一条，还是全局一条（这里按 key，互不相关的 key 没有理由互相阻塞写入）。

### Part 1

每个 key 对应两个按时间戳递增排列的平行列表：`_timestamps` 和 `_values`。`set` 用 `bisect_left` 找到
`timestamp` 应在的位置——已有条目就覆盖（后写的生效），否则在那个位置插入新条目，迟到的时间戳因此也能
落到正确位置。`get` 用 `bisect_right`，不是 `bisect_left`：`timestamp` 恰好命中已有条目时也要算进去，
答案就在 `bisect_right` 会把等于 `timestamp` 的值插入到的位置再往前一格，即下标 `i - 1`。

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

`get` 是 $O(\log n)$；`set` 是 $O(n)$，因为 `timestamps.insert` 和 `values.insert` 都要挪动列表尾部。

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

`set`/`get` 恰好在 `timestamp` 是 `None` 时才去查时钟；显式传入的 `0` 或 `0.0` 是真实的值，不是“没传”，
这正是判断要写成 `is None` 的原因。从这里起，每个 Part 都在同一个名字 `TimeMap` 下*继承*上一个 Part
的类，只覆盖变化的部分，其余交给 `super()`，Part 1 的 `bisect` 逻辑因此只写了一遍。

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

一旦保证每个 key 记录下来的时间戳都比前一个大，`set` 就不再需要 `bisect_left` 配合 `list.insert`——
新条目永远是最后一个，直接 `append` 就够了，把每次调用的开销从 $O(n)$ 降到均摊 $O(1)$。`get` 不用改：
继承来的那一份原样可用，因为两个列表仍然有序。

如果改用异常拒绝不递增的时间戳，记录下来的每个时间戳都是真实的时钟读数，但重试还是丢弃这次写入就要由
调用方决定。`last(key) + 1` 从不拒绝写入，但这个 1 是时钟的一个计数单位，用 `time.time()` 时就是整整
一秒。时钟回拨之后，一个 key 如果每个单位时间写入不止一次，每次都会被往后推，时间戳越来越超前于时钟，
永远追不上；省略 `timestamp` 的 `get` 按 `clock.now()` 查询，在时钟追上之前看不到这些写入。以时钟的
最小单位计数（例如 `time.time_ns()` 的整数纳秒），每次推移都微不足道，时钟也就追得上。

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

让 `set` 线程安全，意味着锁住*整个*“读-改-写”序列——读 `last(key)`、判断、追加、更新 `last(key)`——
而不是只锁住其中单条字典或列表调用：CPython 的 GIL 不会在字节码执行到一半时切换线程，但可以在任意两条
字节码之间切换，“先读 `last`，再写回去”正好留了这样一道缝：两个线程都读到 `last(key)` 是 100.0，
手里的时钟读数也都是 100.0，就都会记下 101.0。

两种加锁策略都再次继承 Part 3 的 `TimeMap`，只在 `super().set`/`super().get` 外面套一层锁，被保护的就是
Part 3 里已经写好的那段操作，`clock.now()` 也因此在锁内读取。如果在等锁之前读时钟，先读时钟的调用可能
后拿到锁，随后被推到 `last(key) + 1`，尽管时钟从未回拨。较简单的 `GlobalLockTimeMap` 整个存储只用一把
`threading.Lock`，会让 `"probe-1"` 的更新等在无关的 `"probe-2"` 更新后面。

给每个 key 各自一把锁能去掉这一点，但创建一个 key 的锁本身就是一次“读-改-写”（有锁了吗？没有的话就造
一个），所以它也需要自己的一把小锁，只在创建或查找时短暂持有。继承自 `TimeMap` 的那些属性在所有 key
之间共享，本身不需要单独加锁：单独一次 `dict.get`/`setdefault` 调用不会被打断，会被打断的是连续好几次
这样的调用，而这正是每键锁要保护的部分。

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

| | 不同 key 之间 | 同一个 key 的多次 `get` | 锁本身的构建 |
| --- | --- | --- | --- |
| 一把全局锁 | 相互阻塞 | 相互阻塞 | 不需要额外构建 |
| 每个 key 一把锁 | 互不阻塞 | 相互阻塞 | 需要自己的一把锁 |
| 每个 key 一把读写锁 | 互不阻塞 | 可以同时进行 | 标准库没有现成的 |

读写锁能让同一个 key 上的多次 `get` 同时持锁，但每次 `get` 持锁时只做一次 $O(\log n)$ 的二分查找，而在
GIL 下两个线程本来就不会同时执行字节码；一个写对的读写锁（标准库没有现成的）只会多出代码和开销。锁内有
可以重叠的工作（比如 I/O），或者解释器没有 GIL 时，它才划算。

```python
tm = ThreadSafeTimeMap(clock=ManualClock(start=1040.0))
threads = [threading.Thread(target=tm.set, args=("probe-1", v)) for v in (71.5, 69.0)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert {tm.get("probe-1", 1040.0), tm.get("probe-1", 1041.0)} == {71.5, 69.0}
```

### 追问

- 回答一整段区间 `get(key, t1, t2)` 需要两次二分定位区间的两端，而不是把这个 key 的全部历史重新扫一遍。
- 要在重启后恢复状态，需要每次写入落到内存之前，连同它实际记录下来的时间戳一起追加进一份日志，启动时
  按顺序重放这份日志。
- 跨机器时没有哪个时钟是精确同步的；混合逻辑时钟（hybrid logical clock）记下目前见过的最大物理时间，
  另用一个计数器区分相同的时间，因此能给有因果关系的事件排出正确的先后，又不会像 `+1` 的推移那样跑到
  最快的物理时钟前面去。

<details>
<summary>验证代码（可运行）</summary>

`GlobalLockTimeMap`，也就是 Part 4 里那种单锁策略的完整代码：每次调用都包进同一把共享的锁。

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

一个不调用 `TimeMap` 任何代码、只照题面写出的版本：每个 key 的每一次 `set` 调用都按调用顺序存在一个
列表里；打开 `nudge` 时，`set` 套用 Part 3 的规则，`last(key)` 取这个列表里最大的时间戳；`get` 扫描
列表，找出不超过查询时间戳的最大时间戳，相同时间戳取较晚的那次调用。拿它和 Part 2 的类、以及遵循
Part 3 规则的三个类逐一对拍。

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

把线程切换强行塞进每一道“读-改-写”的缝里，而不是等调度器碰巧落在那里：`time.sleep(0)` 会释放 GIL，
所以 `YieldingDict.get` 或 `setdefault` 读完之后，调用方用上读到的结果之前，会先有别的线程运行。
Part 3 的 `TimeMap`，以及一个锁登记表不加保护的每键锁变体，几乎每一轮都会破坏某条保证（出现重复的
时间戳，或者 `get` 找到了一个值还没追加进来的时间戳，抛出 `IndexError`）；两个加锁的类从不出错。

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

再做一个不强行插入切换点的压力测试：`sys.setswitchinterval(1e-6)` 让等待中的线程 1 微秒后（而不是
5 毫秒后）就强制切换，线程才真正交错执行。`TickingClock` 的读数从不重复也不回退，所以在每次调用生效的
那一刻读它的存储从不推移时间戳；记录下来的时间戳如果不是它的某个读数，说明某次调用用了过时的读数，比如
在等锁之前读到的。不强行插入切换点时，切换多久落进一次缝里取决于机器有多忙，所以这个测试只断言两个加锁
的类通过；证明缺了锁会被抓到的，是上面那个强制切换的版本。

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
