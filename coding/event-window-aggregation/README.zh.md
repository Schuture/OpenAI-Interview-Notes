# 滑动窗口事件聚合

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE · Infra Eng | sliding-window, streaming, hashmap, heap | 4 个部分 | 电话面 · 现场面 |
<!-- meta:end -->

## 题目

一个聊天产品把用户的每个动作都记成一条*事件*（event）。每条事件至少带三个字段：`user_id`、`chat_id`、
`timestamp`（非负整数，单位为秒）。`chat_id` 只在同一个 `user_id` 下唯一：不同用户之间的 `chat_id`
可能重复，因此一个会话真正的标识是 `(user_id, chat_id)` 这一对，不能只用 `chat_id`。

### Part 1 —— 近期事件计数

这一部分假设所有用户、所有会话的事件按 `timestamp` 非降序依次到达（Part 3 会去掉这个假设）。实现一个
tracker，构造时给定一个正整数 `window`，支持：

```py
class RecentEventCounter:
    def __init__(self, window: int): ...
    def record_event(self, user_id: str, chat_id: str, timestamp: int) -> None: ...
    def recent_count(self, user_id: str, chat_id: str) -> int: ...
```

`record_event` 为该会话记一条事件。`recent_count` 返回该会话迄今记录的事件中，`timestamp` 落在闭区间
`[T - window, T]` 内的数量，其中 `T` 是迄今传给 `record_event` 的最大 `timestamp`——统计的是全体用户、
全体会话中的最大值，不是调用者自己那个会话的最大值，也不是墙上时钟。

在调用序列的任意时刻，tracker 内部仍保留状态的 `(user_id, chat_id)` 组合数不能超过当前窗口内至少有一条
事件的组合数：这个数字绝不能随历史上出现过的会话总数增长，只能随窗口内仍有事件的会话数增长。目标是
均摊 O(1) 的单次调用时间。

例子（`window = 5`）：

```text
record_event('alice', 'a1', 1)
record_event('alice', 'a1', 1)      # 允许重复的 timestamp
recent_count('alice', 'a1')  -> 2   # T = 1，窗口 [-4, 1]
record_event('alice', 'a2', 3)
recent_count('alice', 'a1')  -> 2   # T 变成 3；那两条 timestamp=1 的事件仍在 [-2, 3] 内
recent_count('alice', 'a2')  -> 1
record_event('alice', 'a1', 9)
recent_count('alice', 'a1')  -> 1   # T = 9，窗口 [4, 9]；只剩新事件
recent_count('alice', 'a2')  -> 0   # a2 唯一的事件（timestamp=3）也已经落在 [4, 9] 之外
```

### Part 2 —— 活跃会话数

事件多了第四个字段 `event_type`，取值 `"ping"`（用户正在这个会话里互动）或 `"close"`（用户显式结束了
这个会话——可能很久之后才发生，也可能永远不发生）。一个会话被认为*活跃*（active），当且仅当窗口内有它的
一条 `"ping"`，且在该会话迄今记录的事件中，这条 `"ping"` 之后没有再记录过 `"close"`——这里的“之后”指在
调用序列里更晚；当同一个会话的一条 `"ping"` 和一条 `"close"` 的 `timestamp` 相同时，以调用序列里更晚
记录的那一条为准（timestamp 仍按 Part 1 的假设非降序）。

```py
class SessionActivityTracker:
    def __init__(self, window: int): ...
    def record(self, user_id: str, chat_id: str, event_type: str, timestamp: int) -> None: ...
    def active_sessions(self, user_id: str) -> int: ...
```

`active_sessions(user_id)` 返回该用户当前活跃的会话数。Part 1 的内存约束仍然适用，只是约束对象换成了
判定活跃与否所需的状态；此外，只要一个用户的 `active_sessions` 当前为 `0`，tracker 里任何只按
`user_id` 索引的状态都不能为他保留条目。

例子（`window = 6`）：

```text
record('alice', 'a1', 'ping', 0)
active_sessions('alice')  -> 1
record('alice', 'a2', 'ping', 2)
active_sessions('alice')  -> 2
record('alice', 'a1', 'close', 3)
active_sessions('alice')  -> 1
record('alice', 'a2', 'ping', 5)         # 刷新 a2
active_sessions('alice')  -> 1
record('bruno', 'b1', 'ping', 9)         # T 变成 9；a2 的 ping(5) 仍在 [3, 9] 内
active_sessions('alice')  -> 1
record('bruno', 'b2', 'ping', 12)        # T 变成 12；a2 的 ping(5) 已经落在 [6, 12] 之外
active_sessions('alice')  -> 0
```

### Part 3 —— 事件乱序到达

去掉非降序的假设：`record` 现在可以按任意顺序调用，与 `timestamp` 无关。为此，`active_sessions`
多接收一个参数 `now`。

```py
class OutOfOrderSessionTracker:
    def __init__(self, window: int): ...
    def record(self, user_id: str, chat_id: str, event_type: str, timestamp: int) -> None: ...
    def active_sessions(self, user_id: str, now: int) -> int: ...
```

三条规则钉死语义：

1. `now` 不会小于此前任何一次传给 `record` 的 `timestamp`；在连续多次调用 `active_sessions` 之间，
   `now` 也不会变小——它是一直向前走的真实时钟，不是事后选定的值。
2. 活跃与否由事件携带的*时间戳本身*决定，与到达顺序无关：为每个会话记两个量，`last_ping` 与
   `last_close`，分别是该 `event_type` 迄今见过的最大 `timestamp`（若还没出现过则为 `-∞`）。会话在
   `now` 时刻活跃，当且仅当 `last_ping >= now - window` 且 `last_close <= last_ping`（并列同样归
   `ping`）。
3. 记 $C$ 为迄今传给 `active_sessions` 的所有 `now`、以及传给 `record` 的所有 `timestamp` 中的最大
   值；由规则 1，真实时钟已经走到 $C$，而且 $C$ 只会变大。因此 `timestamp < C - window` 的 `record`
   调用不可能再改变任何未来查询的答案，它什么都不改变。Part 1、2 的内存约束继续成立，只是把 Part 1
   里 `T` 的角色换成 $C$：一个会话被记住，仅当它已知的最近一个时间戳（ping 或 close）仍在 $C$ 的
   `window` 范围内。

例子（`window = 4`）：

```text
record('alice', 'a1', 'ping', 10)
active_sessions('alice', 10)  -> 1
record('alice', 'a1', 'close', 8)        # 一条 close，但比那条 ping 更早 -> 没有影响
active_sessions('alice', 11)  -> 1
record('alice', 'a1', 'close', 12)       # 一条比 ping 更晚的 close
active_sessions('alice', 12)  -> 0
record('alice', 'a1', 'ping', 11)        # 一条迟到的 ping，但仍早于那条 close -> 依然是关闭状态
active_sessions('alice', 13)  -> 0
record('alice', 'a1', 'ping', 14)        # 一条比 close 更晚的 ping -> 重新活跃
active_sessions('alice', 14)  -> 1
record('alice', 'a2', 'ping', 5)         # C = 14，所以 C - window = 10；5 < 10 -> 已过期，直接丢弃
active_sessions('alice', 14)  -> 1       # 不变：a2 从未真正进入过状态
```

### Part 4 —— 扩大规模（只要求口头讨论）

这一部分不要求代码，每个问题口头回答几句话即可。事件量涨到每秒数百万条，分布在许多台机器上，任何一台
机器都放不下全部状态。

1. 你会怎样把事件流分区到各台机器，使每台机器上原样跑 Part 3 的算法，机器之间完全不需要通信？
2. Part 3 假设 `now` 只会前进、事件不会迟到得太离谱。上游的投递系统要保证什么才能让这个假设成立？
   超出这个界限的事件应该怎么处理？
3. 某一个 `user_id`（或某一个 `chat_id`）产生的流量远超其他人。这时会出什么问题？分区方式该怎么调整？
4. 一台机器崩溃重启。它最少需要重放多长的历史才能恢复出正确的状态？Part 1–3 里的内存约束为什么让这个
   答案很小？

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得确认：`chat_id` 是全局唯一还是只在一个用户内唯一（这里取后者，key 是 `(user_id, chat_id)`）；
同一 `timestamp` 上 `ping`/`close` 谁优先（Part 1、2 按调用顺序，Part 3 里不再重要）。

### Part 1

保留一个全局先进先出队列 `_order`（按到达顺序，此处等于时间戳顺序），再给每个 key 配一个 `deque` 存
它自己的时间戳。两者共用同一种顺序，`_order` 队头淘汰出的时间戳一定也在其 key 自己的 deque 队头。

```python
from collections import deque


class RecentEventCounter:
    def __init__(self, window):
        self.window = window
        self._max_ts = float('-inf')   # T: the largest timestamp recorded so far
        self._order = deque()          # (timestamp, key), in arrival order == timestamp order here
        self._per_key = {}             # key -> deque of timestamps, only while one is still in the window

    def record_event(self, user_id, chat_id, timestamp):
        key = (user_id, chat_id)
        self._max_ts = max(self._max_ts, timestamp)
        self._order.append((timestamp, key))
        self._per_key.setdefault(key, deque()).append(timestamp)
        threshold = self._max_ts - self.window
        while self._order and self._order[0][0] < threshold:      # NOTE: '<' -- the window's left edge is inclusive
            ts, k = self._order.popleft()
            bucket = self._per_key[k]
            bucket.popleft()               # always the front of this key's own deque too -- both share one order
            if not bucket:
                del self._per_key[k]       # NOTE: this delete is the whole memory guarantee -- skip it and it leaks

    def recent_count(self, user_id, chat_id):
        return len(self._per_key.get((user_id, chat_id), ()))
```

每条事件入 `_order` 一次、最多出队一次，所以 `record_event` 均摊 O(1)；`recent_count` 是一次字典查找
加一次 `deque` 的 `len`（Python 里 O(1)，不是扫描）。

### Part 2

沿用同一套“全局 FIFO + 惰性判过期”思路，但只有 `ping` 需要排期：`close` 立刻生效。再用一个更粗的、
按 `user_id` 的计数器 `_active_count`，会话自身的活跃状态一翻转它就恰好变动 1。

```python
class SessionActivityTracker:
    def __init__(self, window):
        self.window = window
        self._max_ts = float('-inf')
        self._last_ping = {}         # (user_id, chat_id) -> timestamp; present iff currently active
        self._ping_queue = deque()   # (timestamp, user_id, chat_id), in arrival order
        self._active_count = {}      # user_id -> number of active chats; absent means 0

    def record(self, user_id, chat_id, event_type, timestamp):
        self._max_ts = max(self._max_ts, timestamp)
        key = (user_id, chat_id)
        if event_type == 'ping':
            if key not in self._last_ping:                    # NOTE: only a *new* activation bumps the count
                self._active_count[user_id] = self._active_count.get(user_id, 0) + 1
            self._last_ping[key] = timestamp
            self._ping_queue.append((timestamp, user_id, chat_id))
        else:  # 'close'
            if self._last_ping.pop(key, None) is not None:   # NOTE: in order, a close always supersedes
                self._active_count[user_id] -= 1               # a ping already recorded for this key
                if self._active_count[user_id] == 0:
                    del self._active_count[user_id]           # NOTE: the invariant Part 2 asks for
        threshold = self._max_ts - self.window
        while self._ping_queue and self._ping_queue[0][0] < threshold:
            ts, uid, cid = self._ping_queue.popleft()
            k = (uid, cid)
            if self._last_ping.get(k) == ts:      # NOTE: else stale -- a later ping or close replaced it
                del self._last_ping[k]
                self._active_count[uid] -= 1
                if self._active_count[uid] == 0:
                    del self._active_count[uid]

    def active_sessions(self, user_id):
        return self._active_count.get(user_id, 0)
```

### Part 3

“方法刚好处理到的最后一条事件”不再是可靠摘要：调用顺序里一条 `close` 后面完全可能跟着一条迟到的、
`timestamp` 其实更早的 `ping`。改为每个会话记两个只增不减的量，`last_ping` 与 `last_close`，天然与
到达顺序无关；会话活跃当且仅当 `last_ping` 在窗口内且 `last_close <= last_ping`。

`_clock` 装的就是规则 3 里的 $C$。规则 1 让每条记下的 `timestamp` 都成为真实时钟的下界，所以光是吃进
事件也能推着 `_clock` 前进——连着一长串 `record`、一次查询都没有时，状态还能有界，靠的正是这一点。
`max(last_ping, last_close) + window < _clock` 时这个会话就可以彻底遗忘：此后被接受的调用 `timestamp`
都不小于 `_clock - window`，比两个最大值都大，下一条事件自己就会成为新的最大值，删掉它不会丢掉
任何还有用的信息。

一个最小堆按这个“遗忘时刻”作键，兼顾两种职责：ping 主导（计入活跃）时键是 `last_ping + window`，
弹出意味着会话转为非活跃；close 主导时键是 `last_close + window`，弹出只是丢掉记录。入堆时带上当时的
`(last_ping, last_close)`，出堆才能分辨它是否已被取代。

```python
import heapq

NEG_INF = float('-inf')


class OutOfOrderSessionTracker:
    def __init__(self, window):
        self.window = window
        self._clock = NEG_INF   # C: the largest `now` or `timestamp` seen so far
        self._chat = {}         # (user_id, chat_id) -> (last_ping, last_close, counted)
        self._active_count = {}
        self._heap = []         # (forget_at, user_id, chat_id, last_ping, last_close); may go stale

    def record(self, user_id, chat_id, event_type, timestamp):
        if timestamp < self._clock - self.window:
            return                    # NOTE: rule 3 -- drop it before it costs a heap push
        key = (user_id, chat_id)
        last_ping, last_close, counted = self._chat.get(key, (NEG_INF, NEG_INF, False))
        if event_type == 'ping':
            last_ping = max(last_ping, timestamp)
        else:
            last_close = max(last_close, timestamp)
        ping_dominant = last_close <= last_ping   # NOTE: ties go to ping, and unlike Part 2 on the two
        if ping_dominant != counted:              # timestamps alone, never on the order they arrived in
            counted = ping_dominant
            self._active_count[user_id] = self._active_count.get(user_id, 0) + (1 if counted else -1)
            if self._active_count[user_id] == 0:
                del self._active_count[user_id]
        self._chat[key] = (last_ping, last_close, counted)
        forget_at = (last_ping if ping_dominant else last_close) + self.window
        heapq.heappush(self._heap, (forget_at, user_id, chat_id, last_ping, last_close))
        self._advance(timestamp)      # NOTE: ingest evicts too -- without this a query-free stream leaks

    def _advance(self, t):
        self._clock = max(self._clock, t)
        while self._heap and self._heap[0][0] < self._clock:
            _, user_id, chat_id, ping_v, close_v = heapq.heappop(self._heap)
            key = (user_id, chat_id)
            cur = self._chat.get(key)
            if cur is None or cur[0] != ping_v or cur[1] != close_v:
                continue                                 # stale: a later record() already replaced this
            if cur[2]:                                   # was still counted -- its ping just aged out
                self._active_count[user_id] -= 1
                if self._active_count[user_id] == 0:
                    del self._active_count[user_id]
            del self._chat[key]                          # safe either way, per the derivation above

    def active_sessions(self, user_id, now):
        self._advance(now)
        return self._active_count.get(user_id, 0)
```

每次 `record` 入堆一次，每个条目最多出堆一次（无论是否过期），所以入堆与淘汰都是均摊
$O(\log n)$；`active_sessions` 再加一次字典查找。

### Part 4

1. 按 `user_id` 分区：Part 3 的 tracker 在每台机器上原样运行，机器间无需协调。
2. 上游要承诺一个*水位线*（watermark）：`now` 越过某点之后事件最多还能迟到多久；更晚的事件正好是
   规则 3 的情形，直接丢弃。
3. 热点 `user_id` 按 `chat_id` 二次分片，查询时向各分片发请求再求和。
4. 超过 `window` 的状态已经被遗忘，崩溃后只需重放分区日志最近 `window` 的一段，不需要快照。

### 追问

- 分钟粒度的时间戳配上固定 `window`，可以把 Part 3 的堆换成 `window + 1` 个环形桶，退回 O(1)。
- 水位线是投递系统的承诺，Part 3 不检查；调用方给出低于 `_clock` 的 `now`，拿到的答案其实按 `_clock`
  算，悄无声息——一条断言就能防住。

<details>
<summary>验证代码（可运行）</summary>

```python
import random


# --- the statement's own examples ---
c = RecentEventCounter(window=5)
c.record_event('alice', 'a1', 1)
c.record_event('alice', 'a1', 1)
assert c.recent_count('alice', 'a1') == 2
c.record_event('alice', 'a2', 3)
assert (c.recent_count('alice', 'a1'), c.recent_count('alice', 'a2')) == (2, 1)
c.record_event('alice', 'a1', 9)
assert (c.recent_count('alice', 'a1'), c.recent_count('alice', 'a2')) == (1, 0)

s = SessionActivityTracker(window=6)
s.record('alice', 'a1', 'ping', 0); assert s.active_sessions('alice') == 1
s.record('alice', 'a2', 'ping', 2); assert s.active_sessions('alice') == 2
s.record('alice', 'a1', 'close', 3); assert s.active_sessions('alice') == 1
s.record('alice', 'a2', 'ping', 5); assert s.active_sessions('alice') == 1
s.record('bruno', 'b1', 'ping', 9); assert s.active_sessions('alice') == 1
s.record('bruno', 'b2', 'ping', 12)
assert s.active_sessions('alice') == 0 and 'alice' not in s._active_count

o = OutOfOrderSessionTracker(window=4)
o.record('alice', 'a1', 'ping', 10); assert o.active_sessions('alice', 10) == 1
o.record('alice', 'a1', 'close', 8); assert o.active_sessions('alice', 11) == 1
o.record('alice', 'a1', 'close', 12)
assert o.active_sessions('alice', 12) == 0 and 'alice' not in o._active_count
o.record('alice', 'a1', 'ping', 11); assert o.active_sessions('alice', 13) == 0
o.record('alice', 'a1', 'ping', 14); assert o.active_sessions('alice', 14) == 1
o.record('alice', 'a2', 'ping', 5); assert o.active_sessions('alice', 14) == 1
assert o.active_sessions('alice', 99) == 0 and not o._active_count and not o._chat

# --- the tie rule, both ways, for Part 2 (order-dependent) and Part 3 (order-independent) ---
t = SessionActivityTracker(window=100)
t.record('alice', 'a1', 'ping', 5); t.record('alice', 'a1', 'close', 5)
assert t.active_sessions('alice') == 0 and not t._active_count   # later call at the same ts wins
t = SessionActivityTracker(window=100)
t.record('alice', 'a1', 'close', 5); t.record('alice', 'a1', 'ping', 5)
assert t.active_sessions('alice') == 1                          # ... either way round

tr_a, tr_b = OutOfOrderSessionTracker(window=100), OutOfOrderSessionTracker(window=100)
tr_a.record('alice', 'a1', 'close', 5); tr_a.record('alice', 'a1', 'ping', 5)
tr_b.record('alice', 'a1', 'ping', 5); tr_b.record('alice', 'a1', 'close', 5)
assert tr_a.active_sessions('alice', 5) == tr_b.active_sessions('alice', 5) == 1   # order no longer matters


# --- independent references: no deque/heap, no shared helper, a full scan on every query ---
def brute_recent_count(events, user_id, chat_id, window):
    if not events:
        return 0
    T = max(ts for _, _, ts in events)
    return sum(1 for uid, cid, ts in events if uid == user_id and cid == chat_id and T - window <= ts <= T)


def brute_active_sessions_inorder(events, user_id, window):
    # events fed in call order == timestamp order (Part 2's assumption); ties broken by call order.
    if not events:
        return 0
    T = max(ts for _, _, _, ts in events)
    threshold = T - window
    last_event = {}                      # chat_id -> (event_type, ts) of THIS user's chronologically last event
    for uid, cid, et, ts in events:
        if uid == user_id:
            last_event[cid] = (et, ts)   # overwritten in call order, so it ends up as the true last one
    return sum(1 for et, ts in last_event.values() if et == 'ping' and ts >= threshold)


def brute_active_sessions_asof(events, user_id, window, now):
    # events fed in ANY order; rule 1 makes `now` at least every timestamp fed so far.
    threshold = now - window
    chats = {}
    for uid, cid, et, ts in events:
        if uid != user_id:
            continue
        lp, lc = chats.get(cid, (None, None))
        if et == 'ping':
            lp = ts if lp is None else max(lp, ts)
        else:
            lc = ts if lc is None else max(lc, ts)
        chats[cid] = (lp, lc)
    return sum(1 for lp, lc in chats.values() if lp is not None and lp >= threshold and (lc is None or lc <= lp))


# --- Part 1: random cross-check, in-order arrival ---
nonzero1 = aged_out1 = 0
for seed in range(400):
    rng = random.Random(seed)
    window = rng.choice([1, 2, 5, 10])
    users, chats = [f'k{i}' for i in range(rng.randint(1, 3))], [f's{i}' for i in range(rng.randint(1, 3))]
    counter, fed, ts = RecentEventCounter(window), [], 0
    for _ in range(rng.randint(1, 40)):
        ts += rng.randint(0, 3)
        uid, cid = rng.choice(users), rng.choice(chats)
        counter.record_event(uid, cid, ts)
        fed.append((uid, cid, ts))
        for u in users:
            for c_ in chats:
                got = counter.recent_count(u, c_)
                assert got == brute_recent_count(fed, u, c_, window), (seed, u, c_, fed)
                nonzero1 += got > 0
                aged_out1 += got == 0 and any(x[:2] == (u, c_) for x in fed)
assert nonzero1 > 5000 and aged_out1 > 1000, (nonzero1, aged_out1)   # full and fully-aged windows both seen

# --- Part 2: random cross-check, in-order arrival ---
seen2 = 0
for seed in range(400):
    rng = random.Random(1000 + seed)
    window = rng.choice([1, 2, 4, 8])
    users, chats = [f'k{i}' for i in range(rng.randint(1, 3))], [f's{i}' for i in range(rng.randint(1, 4))]
    tracker, fed, ts = SessionActivityTracker(window), [], 0
    for _ in range(rng.randint(1, 30)):
        ts += rng.randint(0, 3)
        uid, cid, et = rng.choice(users), rng.choice(chats), rng.choice(['ping', 'ping', 'close'])
        tracker.record(uid, cid, et, ts)
        fed.append((uid, cid, et, ts))
        for u in users:
            got, exp = tracker.active_sessions(u), brute_active_sessions_inorder(fed, u, window)
            assert got == exp, (seed, u, got, exp, fed)
            seen2 += got > 0
assert seen2 > 500, seen2   # coverage: many queries really saw an active chat, not all zeros

# --- Part 3: random cross-check, arbitrary arrival order, against a query-time full replay ---
late_events, expired_to_zero = 0, 0
for seed in range(600):
    rng = random.Random(2000 + seed)
    window = rng.choice([1, 2, 4, 8])
    users, chats = [f'k{i}' for i in range(rng.randint(1, 3))], [f's{i}' for i in range(rng.randint(1, 3))]
    tracker, fed, now_high = OutOfOrderSessionTracker(window), [], 0
    for _ in range(rng.randint(1, 25)):
        if rng.random() < 0.7:
            ts = max(0, now_high - rng.randint(0, window + 3))     # behind now_high: out of order
            if ts < now_high - window:
                late_events += 1
            uid, cid, et = rng.choice(users), rng.choice(chats), rng.choice(['ping', 'close'])
            tracker.record(uid, cid, et, ts)
            fed.append((uid, cid, et, ts))
        else:
            now_high += rng.randint(0, 3)
            for u in users:
                got = tracker.active_sessions(u, now_high)
                exp = brute_active_sessions_asof(fed, u, window, now_high)
                assert got == exp, (seed, u, now_high, got, exp, fed)
                expired_to_zero += got == 0
    now_high += window + 2
    for u in users:
        got = tracker.active_sessions(u, now_high)
        exp = brute_active_sessions_asof(fed, u, window, now_high)
        assert got == exp, ('final', seed, u, now_high, got, exp, fed)
        expired_to_zero += got == 0
assert late_events > 300 and expired_to_zero > 300, (late_events, expired_to_zero)

# Order independence and the arrival-driven clock at once: the same record() calls in five permutations,
# each fed with no query in between, must agree with each other and with the replay.
spans = 0
for seed in range(300):
    rng = random.Random(9000 + seed)
    window = rng.choice([1, 2, 4, 8])
    users = ['kx', 'ky']
    records = [(rng.choice(users), rng.choice(['s0', 's1']), rng.choice(['ping', 'close']), rng.randint(0, 25))
               for _ in range(rng.randint(2, 12))]
    now = max(r[3] for r in records)
    spans += now - min(r[3] for r in records) > window
    expected = tuple(brute_active_sessions_asof(records, u, window, now) for u in users)
    for _ in range(5):
        perm = records[:]
        rng.shuffle(perm)
        tr = OutOfOrderSessionTracker(window)
        for r in perm:
            tr.record(*r)
        assert tuple(tr.active_sessions(u, now) for u in users) == expected, (seed, records, perm)
assert spans > 150, spans   # coverage: the span often exceeds the window, so stale drops happen

# --- memory: 100,000 keys seen once and never again, under four arrival patterns ---
window, n = 100, 100_000
counter = RecentEventCounter(window)
for i in range(n):
    counter.record_event(f'k{i}', 'only', i)
assert len(counter._per_key) <= window + 1 and len(counter._order) <= window + 1, len(counter._per_key)

tracker = SessionActivityTracker(window)
for i in range(n):
    tracker.record(f'k{i}', 'only', 'ping', i)
assert max(len(tracker._last_ping), len(tracker._active_count), len(tracker._ping_queue)) <= window + 1

# shuffled arrival and not one query: ingest alone has to keep the state bounded
tracker = OutOfOrderSessionTracker(window)
order = list(range(n))
random.Random(42).shuffle(order)
for ts in order:
    tracker.record(f'k{ts}', 'only', 'ping', ts)
assert len(tracker._chat) <= window + 1 and len(tracker._heap) <= window + 1, len(tracker._heap)

# one key pinged 100,000 times: no live heap entry per event either
tracker = OutOfOrderSessionTracker(window)
for ts in range(n):
    tracker.record('hot', 'only', 'ping', ts)
assert len(tracker._chat) == 1 and len(tracker._heap) <= window + 1, len(tracker._heap)

# identical timestamps: all 100,000 keys really are inside the window, so holding them is correct,
# and one step of the clock past the window has to drop every one
tracker = OutOfOrderSessionTracker(window)
for i in range(n):
    tracker.record(f'k{i}', 'only', 'ping', 7)
assert len(tracker._chat) == n
assert tracker.active_sessions('k0', 7 + window + 1) == 0 and tracker._chat == {}

print("all checks passed")
```

</details>

</details>
