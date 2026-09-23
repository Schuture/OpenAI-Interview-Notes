# Sliding-Window Event Aggregation

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Coding | ★★★☆☆ | Medium | SWE · Infra Eng | sliding-window, streaming, hashmap, heap | 4 parts | Phone screen · Onsite |
<!-- meta:end -->

## Problem

A chat product turns every user action into an *event*. Every event carries at least a `user_id`, a
`chat_id`, and a `timestamp` — a non-negative integer number of seconds. `chat_id` is unique only
*within* a `user_id`: two different users may independently use the same `chat_id`, so a chat's real
identity is the pair `(user_id, chat_id)`, never `chat_id` alone.

### Part 1 — Recent event count

For this part, events across every user and chat arrive in non-decreasing order of `timestamp`
(Part 3 drops this assumption). Implement a tracker, constructed once with a fixed positive integer
`window`, that supports:

```py
class RecentEventCounter:
    def __init__(self, window: int): ...
    def record_event(self, user_id: str, chat_id: str, timestamp: int) -> None: ...
    def recent_count(self, user_id: str, chat_id: str) -> int: ...
```

`record_event` logs one event for that chat. `recent_count` returns how many events logged so far for
that chat have a `timestamp` inside the closed interval `[T - window, T]`, where `T` is the largest
`timestamp` passed to `record_event` so far, over every user and chat — not the caller's own chat, and
not a wall clock.

At every point in the call sequence, the number of distinct `(user_id, chat_id)` pairs for which the
tracker still holds any state must not exceed the number of pairs that currently have at least one
event inside that window: it must never grow with how many distinct chats have ever been seen, only
with how many are still inside the window. Aim for amortized O(1) time per call.

Example, with `window = 5`:

```text
record_event('alice', 'a1', 1)
record_event('alice', 'a1', 1)      # duplicate timestamps are allowed
recent_count('alice', 'a1')  -> 2   # T = 1, window [-4, 1]
record_event('alice', 'a2', 3)
recent_count('alice', 'a1')  -> 2   # T is now 3; both events at 1 are still inside [-2, 3]
recent_count('alice', 'a2')  -> 1
record_event('alice', 'a1', 9)
recent_count('alice', 'a1')  -> 1   # T = 9, window [4, 9]; only the new event remains
recent_count('alice', 'a2')  -> 0   # a2's only event, at 3, is also outside [4, 9]
```

### Part 2 — Active chat count

Events now carry a fourth field, `event_type`, one of `"ping"` (the user is actively interacting with
the chat) or `"close"` (the user explicitly ended the chat — possibly much later, possibly never). A
chat is *active* if the window contains a `"ping"` for it and, among the events recorded so far for
that chat, no `"close"` has been recorded after that `"ping"` — "after" meaning later in the call
sequence; when a `"ping"` and a `"close"` for the same chat share a `timestamp`, whichever one is
recorded later in the call sequence wins (timestamps are still non-decreasing across calls, as in
Part 1).

```py
class SessionActivityTracker:
    def __init__(self, window: int): ...
    def record(self, user_id: str, chat_id: str, event_type: str, timestamp: int) -> None: ...
    def active_sessions(self, user_id: str) -> int: ...
```

`active_sessions(user_id)` returns the number of that user's chats that are currently active. Part 1's
memory rule still applies, now to whatever state decides activeness; in addition, no state the tracker
keys by `user_id` alone may survive for a user whose `active_sessions` is currently `0`.

Example, with `window = 6`:

```text
record('alice', 'a1', 'ping', 0)
active_sessions('alice')  -> 1
record('alice', 'a2', 'ping', 2)
active_sessions('alice')  -> 2
record('alice', 'a1', 'close', 3)
active_sessions('alice')  -> 1
record('alice', 'a2', 'ping', 5)         # refreshes a2
active_sessions('alice')  -> 1
record('bruno', 'b1', 'ping', 9)         # T becomes 9; a2's ping at 5 is still inside [3, 9]
active_sessions('alice')  -> 1
record('bruno', 'b2', 'ping', 12)        # T becomes 12; a2's ping at 5 has now fallen out of [6, 12]
active_sessions('alice')  -> 0
```

### Part 3 — Out-of-order arrival

Drop the non-decreasing assumption: `record` may now be called in any order, independent of
`timestamp`. To compensate, `active_sessions` takes an explicit second argument, `now`.

```py
class OutOfOrderSessionTracker:
    def __init__(self, window: int): ...
    def record(self, user_id: str, chat_id: str, event_type: str, timestamp: int) -> None: ...
    def active_sessions(self, user_id: str, now: int) -> int: ...
```

Three rules pin down the semantics:

1. `now` is never smaller than any `timestamp` already passed to `record` by that point, and, across
   successive calls to `active_sessions`, `now` never decreases either — it is a forward-moving wall
   clock, not a value chosen after the fact.
2. Activeness is decided by the *timestamps* the events carry, not by the order they arrived in: track,
   per chat, `last_ping` and `last_close`, each the largest `timestamp` seen so far for that
   `event_type` (`-∞` if none has arrived yet). The chat is active as of `now` iff
   `last_ping >= now - window` and `last_close <= last_ping` (a tie again goes to `ping`).
3. Write $C$ for the largest value seen so far among every `now` passed to `active_sessions` and every
   `timestamp` passed to `record`; by rule 1 the clock has already reached $C$, and $C$ only ever grows.
   A `record` call with `timestamp < C - window` can therefore no longer change the answer to any future
   query, and changes nothing. The same memory rule as Parts 1–2 still holds, with $C$ in the role
   Part 1 gave `T`: a chat is remembered only while its most recent known timestamp, ping or close, is
   still within `window` of $C$.

Example, with `window = 4`:

```text
record('alice', 'a1', 'ping', 10)
active_sessions('alice', 10)  -> 1
record('alice', 'a1', 'close', 8)        # a close, but earlier than the ping -> no effect
active_sessions('alice', 11)  -> 1
record('alice', 'a1', 'close', 12)       # a close later than the ping
active_sessions('alice', 12)  -> 0
record('alice', 'a1', 'ping', 11)        # a late ping, but still earlier than that close -> still closed
active_sessions('alice', 13)  -> 0
record('alice', 'a1', 'ping', 14)        # a ping later than the close -> active again
active_sessions('alice', 14)  -> 1
record('alice', 'a2', 'ping', 5)         # C = 14, so C - window = 10; 5 < 10 -> already stale, dropped
active_sessions('alice', 14)  -> 1       # unchanged: a2 never entered the state
```

### Part 4 — Scaling up (discussed, not coded)

No code is required for this part; answer each question out loud, in a few sentences. The event volume
grows to millions of events per second, spread across many machines, and no single machine can hold the
whole state.

1. How would you partition the stream across machines so each machine keeps running Part 3's algorithm
   unchanged, without talking to any other machine?
2. Part 3 assumed `now` only moves forward and no event is outrageously late. What must the upstream
   delivery system guarantee for that to hold, and what should happen to an event that violates it?
3. One `user_id`, or one `chat_id`, can produce far more traffic than the others. What breaks when that
   happens, and how would you change the partitioning to cope?
4. A machine crashes and restarts. What is the minimum history it must replay to reconstruct correct
   state, and why does the memory bound from Parts 1–3 make that amount small?

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming before coding: whether `chat_id` is globally unique or only within a user (the latter
here, so every key is `(user_id, chat_id)`), and how a same-`timestamp` `ping`/`close` tie is ordered
(call order in Parts 1–2; Part 3 shows it stops mattering once arrival order does).

### Part 1

Keep one global FIFO, `_order`, holding every event in arrival order (== timestamp order here), next to
a `deque` per key holding that key's own timestamps. Both share one order, so a timestamp evicted from
the front of `_order` is always at the front of its own key's deque too.

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

Every event enters `_order` once and leaves at most once, so `record_event` is amortized O(1);
`recent_count` is a dict lookup plus `len` of a `deque` (O(1) in Python, not a scan).

### Part 2

Reuse the same FIFO-plus-lazy-staleness idea, but only `ping` events need scheduling: a `close` takes
effect immediately. A coarser per-`user_id` counter, `_active_count`, moves by exactly one whenever a
chat's own active/inactive status flips.

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

"The last event this method happened to process" is no longer a safe summary: in call order a `close`
can be followed by a late `ping` whose own `timestamp` is *earlier*. Track two running maxima per chat
instead, `last_ping` and `last_close`; each only ever grows, so both are independent of arrival order by
construction, and the chat is active iff `last_ping` is inside the window and `last_close <= last_ping`.

`_clock` carries rule 3's bound $C$. Rule 1 makes every recorded `timestamp` a lower bound on the real
clock, so ingesting alone moves `_clock` forward — which is what bounds the state through a long run of
`record` calls with no query in between. A chat can be forgotten once
`max(last_ping, last_close) + window < _clock`: every call accepted from then on carries a `timestamp`
of at least `_clock - window`, above both maxima, so the next accepted event becomes the new maximum on
its own, and dropping the entry loses nothing.

One min-heap keyed by that "forget-at" time does double duty: while ping-dominant (counted active) the
key is `last_ping + window` and popping it deactivates the chat; while close-dominant it is
`last_close + window` and popping it only drops the entry. Each push carries the
`(last_ping, last_close)` behind it, so a pop can tell a current entry from a superseded one.

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

Every `record` pushes one heap entry and every entry is popped at most once, stale or not, so both
`record` and eviction are amortized $O(\log n)$; `active_sessions` adds one dict lookup.

### Part 4

1. Partition by `user_id`: Part 3's tracker runs unchanged on each machine, with no cross-machine
   coordination.
2. The upstream system must promise a *watermark* — how late an event may still arrive once `now` has
   passed a point; anything later is exactly rule 3's case, dropped, with no special-casing.
3. A hot `user_id` needs a second split by `chat_id`; a query for that user fans out and sums the
   partial counts.
4. State older than `window` is already forgotten, so a crashed machine only replays the last `window`
   of its partition's log — no snapshotting.

### Follow-ups

- Minute-granular timestamps with a fixed `window` turn Part 3's heap into a ring of `window + 1`
  buckets, back to O(1) per call.
- The watermark is a promise from delivery, not something Part 3 checks; a caller passing a `now` below
  `_clock` is silently answered as of `_clock` instead — worth one assertion.

<details>
<summary>Checks (runnable)</summary>

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
