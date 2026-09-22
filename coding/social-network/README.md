# Follow Graph & Recommendations (Social Network)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★★ | Medium | SWE · RE | graph, hashmap, snapshot, binary-search | 4 parts |
<!-- meta:end -->

## Problem

A social network holds a set of users and a directed *follow* relation between them: if `A` follows
`B` that does not imply `B` follows `A`. Implement the following four parts.

### Part 1 — Users, follows, and snapshots

`SocialNetwork` holds the live, mutable state. A `Snapshot` freezes that state at one instant: no
matter what happens to the `SocialNetwork` afterwards, a `Snapshot` that has already been returned
keeps answering as of the moment it was created.

```py
class SocialNetwork:
    def add_user(self, user_id: str) -> None:
        """Registers a new user. Raises ValueError if user_id already exists."""

    def follow(self, follower: str, followee: str) -> None:
        """follower starts following followee. Raises ValueError if follower or followee is
        not a registered user. follower == followee is a no-op, and so is a call for a pair
        that already follows."""

    def create_snapshot(self) -> "Snapshot":
        """Freezes the current users and follow edges into a Snapshot. Any add_user() or
        follow() call made on this SocialNetwork afterwards must not change a Snapshot that
        has already been returned."""


class Snapshot:
    def is_following(self, follower: str, followee: str) -> bool:
        """Raises ValueError if follower or followee was not a user of this snapshot."""
```

Example: register `alice`, `bob`, `carol`, `dave`; call `follow("alice", "bob")` and
`follow("alice", "carol")`; take a snapshot `s1`. Afterwards, `follow("bob", "dave")` is called on
the live network. `s1.is_following("alice", "carol")` is `True`, but `s1.is_following("bob", "dave")`
is `False` — that edge did not exist yet when `s1` was created. A snapshot taken after the second
call would return `True` for the same query. (A repeated `follow("alice", "bob")`, or a
`follow("alice", "alice")` call, at any point would not change any of this.)

### Part 2 — Following and follower lists

Extend `Snapshot` with the two lists below, each returned sorted by user id, ascending.

```py
class Snapshot:
    def get_following(self, user_id: str) -> list[str]:
        """Users user_id follows, as of this snapshot, sorted by user id ascending.
        Raises ValueError if user_id is unknown to this snapshot."""

    def get_followers(self, user_id: str) -> list[str]:
        """Users who follow user_id, as of this snapshot, sorted by user id ascending.
        Raises ValueError if user_id is unknown to this snapshot."""
```

Example: continuing Part 1, suppose that by the time a second snapshot `s2` is taken, `bob`
additionally follows `erin`, and `carol` follows `dave`, `frank`, `bob`, and `alice`.
`s2.get_following("carol")` is `["alice", "bob", "dave", "frank"]`, and `s2.get_followers("dave")`
is `["bob", "carol"]`.

### Part 3 — Two-hop recommendations

A *candidate* for `user_id` is any user reached by following one of `user_id`'s own followees,
excluding `user_id` itself and anyone `user_id` already follows directly. A candidate's *score* is
the number of distinct followees of `user_id` through which it is reached.

```py
class Snapshot:
    def recommend(self, user_id: str, k: int) -> list[str]:
        """Top-k two-hop recommendations for user_id, ranked by score descending, ties
        broken by user id ascending. Returns fewer than k entries if fewer candidates
        exist. Raises ValueError if user_id is unknown to this snapshot."""
```

Example: using `s2` from Part 2 (`alice` follows `bob`, `carol`; `bob` follows `dave`, `erin`;
`carol` follows `dave`, `frank`, `bob`, `alice`), `s2.recommend("alice", 2)` is
`["dave", "erin"]` — `dave` is reached through both `bob` and `carol` (score 2), `erin` only through
`bob` (score 1, ahead of `frank`'s score 1 by user id). `bob` is reached through `carol` too, but is
excluded because `alice` already follows him. `s2.recommend("alice", 5)` is
`["dave", "erin", "frank"]`, since only three candidates exist.

### Part 4 — Point-in-time queries

Instead of only answering queries at the instants where `create_snapshot()` was explicitly called,
extend the network so any past instant can be queried directly. Every `follow`/`unfollow` call now
carries the time `t` at which it happens; calls to `follow()`/`unfollow()` on the same
`FollowTimeline` arrive with non-decreasing `t`, though `is_following()` may be called with any `t`,
not only the latest one. This class needs no `add_user`: a user id exists the moment it first
appears in a call, and `is_following` is `False` for any pair that has never had a recorded event.

```py
class FollowTimeline:
    def follow(self, follower: str, followee: str, t: int) -> None:
        """follower starts following followee at time t. follower == followee is a no-op,
        and so is a call that would repeat the pair's current state."""

    def unfollow(self, follower: str, followee: str, t: int) -> None:
        """follower stops following followee at time t. Same no-op rules as follow()."""

    def is_following(self, follower: str, followee: str, t: int) -> bool:
        """Whether follower was following followee at time t. If follow() and unfollow()
        were both called with the same t for this pair, the call made later decides the
        state at that t."""
```

Example: `follow("x", "y", 10)`, then `unfollow("x", "y", 20)`, then `follow("x", "y", 30)`.
`is_following("x", "y", t)` is `False` for `t < 10`, `True` for `10 <= t < 20`, `False` for
`20 <= t < 30`, and `True` for `t >= 30`.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming before coding: whether a `Snapshot` query about an id it does not know should raise
or be treated as "no relationship" (taken here to raise, matching `follow()`); and whether the Part 4
event stream is really guaranteed non-decreasing in `t`, since that assumption is what keeps every
per-pair event list sorted for free.

### Part 1

Both classes store adjacency as `dict[str, set[str]]`. A `set` makes `follow` and duplicate-follow
detection O(1) for free (`set.add` on an existing element is a no-op), so the only rule that needs an
explicit check is self-follow. The one real trap is `create_snapshot`: copying the *outer* dict is not
enough, because the *inner* sets would still be the same objects the live `SocialNetwork` keeps
mutating.

```python
class SocialNetwork:
    def __init__(self):
        self._users = set()
        self._following = {}

    def add_user(self, user_id):
        if user_id in self._users:
            raise ValueError(f"user already exists: {user_id!r}")
        self._users.add(user_id)
        self._following[user_id] = set()

    def follow(self, follower, followee):
        if follower not in self._users or followee not in self._users:
            raise ValueError("unknown user")
        if follower == followee:          # NOTE: checked before any mutation, so self-follow is a no-op
            return
        self._following[follower].add(followee)   # NOTE: set.add is idempotent -> duplicate follow is a no-op too

    def create_snapshot(self):
        return Snapshot(self._users, self._following)


class Snapshot:
    def __init__(self, users, following):
        self._users = set(users)
        # NOTE: copy EACH inner set. following.copy() alone would copy the outer dict but keep the
        # same inner set objects, so a later SocialNetwork.follow() would still mutate this snapshot.
        self._following = {u: set(fs) for u, fs in following.items()}
        self._followers = {u: set() for u in self._users}   # reverse index, used starting get_followers below
        for u, followees in self._following.items():
            for v in followees:
                self._followers[v].add(u)

    def _check(self, user_id):
        if user_id not in self._users:
            raise ValueError(f"unknown user: {user_id!r}")

    def is_following(self, follower, followee):
        self._check(follower)
        self._check(followee)
        return followee in self._following[follower]
```

### Part 2

`get_following` just sorts the stored set. `get_followers` could instead scan every user's followee
set at call time, but that costs O(users + edges) per call no matter how small the answer is; building
the reverse index once, during the O(users + edges) construction pass above, makes both methods cost
only as much as the size of their own answer.

```python
def get_following(self, user_id):
    self._check(user_id)
    return sorted(self._following[user_id])          # NOTE: sets have no reliable order; sort for determinism


def get_followers(self, user_id):
    self._check(user_id)
    return sorted(self._followers[user_id])


Snapshot.get_following = get_following      # attach both methods to the Snapshot class of Part 1
Snapshot.get_followers = get_followers
```

### Part 3

For each followee `f` of `user_id`, every one of `f`'s own followees `c` gets one point, tallied in a
`Counter`; a candidate's final score is exactly the number of distinct `f` through which it is
reached, since `_following[f]` is a set and so contributes at most once per `f`. Sorting by
`(-score, user_id)` gives score descending with an alphabetical tie-break in a single pass, and
slicing `[:k]` handles `k` larger than the candidate count for free.

```python
from collections import Counter


def recommend(self, user_id, k):
    self._check(user_id)
    direct = self._following[user_id]
    counts = Counter()
    for f in direct:
        for c in self._following[f]:
            if c != user_id and c not in direct:   # NOTE: exclude the user itself and already-followed accounts
                counts[c] += 1
    ranked = sorted(counts, key=lambda c: (-counts[c], c))   # NOTE: ties broken by user id ascending
    return ranked[:k]           # NOTE: k > len(ranked) just returns every candidate, no error or padding


Snapshot.recommend = recommend              # attach to the Snapshot class of Part 1
```

Let $n$ be the number of users and $m$ the number of follow edges at snapshot time, $d(u)$ the number
of accounts $u$ follows and $d^-(u)$ the number that follow $u$. For `recommend`, let $F = d(\text{user\_id})$
and $C$ be the number of distinct candidates found; the inner double loop visits $\sum_{f} d(f) = O(F \cdot G)$
pairs, where $G$ is the average out-degree among `user_id`'s own followees.

| Method | Time | Space |
| --- | --- | --- |
| `add_user`, `follow` | O(1) | O(1) |
| `create_snapshot` | O(n + m) | O(n + m) |
| `is_following` | O(1) | O(1) |
| `get_following(u)` | $O(d(u) \log d(u))$ | $O(d(u))$ |
| `get_followers(u)` | $O(d^-(u) \log d^-(u))$ | $O(d^-(u))$ |
| `recommend(u, k)` | $O(F \cdot G + C \log C)$ | $O(C)$ |

### Part 4

Store, per `(follower, followee)` pair, only the timestamps at which its state toggled, in the order
the calls happened. Because the global call stream is non-decreasing in `t`, each pair's own list is
appended to in increasing order and is therefore already sorted — no separate sort step is needed. The
list always alternates start, stop, start, stop, ... beginning with a start, because `unfollow` is a
no-op whenever the pair is not currently following and `follow` is a no-op whenever it already is; so
`is_following(follower, followee, t)` only needs the *count* of events at or before `t`: an odd count
means the most recent one was a start.

```python
import bisect


class FollowTimeline:
    def __init__(self):
        self._events = {}  # (follower, followee) -> toggle timestamps, always sorted by construction

    def _following_at(self, key, t):
        events = self._events.get(key)
        if not events:
            return False
        i = bisect.bisect_right(events, t)   # NOTE: bisect_right, so a stop/start AT t is already in effect
        return i % 2 == 1                    # NOTE: relies on the log alternating start/stop, first event a start

    def follow(self, follower, followee, t):
        if follower == followee:
            return
        key = (follower, followee)
        if self._following_at(key, t):       # already following -> duplicate call, no-op
            return
        self._events.setdefault(key, []).append(t)

    def unfollow(self, follower, followee, t):
        if follower == followee:
            return
        key = (follower, followee)
        if not self._following_at(key, t):   # not following -> duplicate call, no-op
            return
        self._events[key].append(t)

    def is_following(self, follower, followee, t):
        return self._following_at((follower, followee), t)
```

Using `bisect_right` rather than `bisect_left` is what makes an event at exactly `t` already count —
equivalent to storing each `[start, stop)` interval and testing whether `t` falls inside one of them.
`follow`/`unfollow` are O(1) amortized (one list append); `is_following` is $O(\log e)$, where $e$ is
the number of toggle events recorded so far for that one pair, against $O(1)$ amortized appends for
the writes. A naive alternative — replaying the entire call log from the start on every query — costs
O(total calls so far) per query instead.

### Follow-ups

- Deep-copying every followee set on every `create_snapshot()` call is wasteful once graphs are large
  and snapshots are frequent. A copy-on-write representation, where a `follow()` after a snapshot
  replaces only the one followee set it touches instead of the ones still shared with earlier
  snapshots, turns `create_snapshot()` into O(1) without any of them observing later writes.
- Storing only the delta between consecutive snapshots, or storing every edge with its own
  `[start, end)` validity interval, avoids paying for a full graph copy on every snapshot and lets any
  historical instant be reconstructed by filtering.
- Many `Snapshot` reads can run in parallel, since they only read frozen state; a read-write lock (or
  the copy-on-write scheme above, which needs no lock for readers at all) serializes `follow()` writes
  against them without blocking the reads.
- `recommend` could weight each intermediary by how recently `user_id` interacted with them instead of
  counting every one equally, or repeat the same counting step one level further out for 3-hop
  suggestions.

<details>
<summary>Checks (runnable)</summary>

```python
import random

net = SocialNetwork()
for u in ["alice", "bob", "carol", "dave", "erin", "frank"]:
    net.add_user(u)
net.follow("alice", "bob")
net.follow("alice", "carol")
net.follow("alice", "alice")   # self-follow -> no-op
net.follow("alice", "bob")     # duplicate -> no-op
s1 = net.create_snapshot()
net.follow("bob", "dave")
net.follow("bob", "erin")
net.follow("carol", "dave")
net.follow("carol", "frank")
net.follow("carol", "bob")
net.follow("carol", "alice")
s2 = net.create_snapshot()

assert s1.is_following("alice", "carol") is True
assert s1.is_following("bob", "dave") is False       # not yet followed when s1 was taken
assert s2.is_following("bob", "dave") is True
assert s1.get_following("alice") == ["bob", "carol"]
assert s2.get_following("carol") == ["alice", "bob", "dave", "frank"]
assert s2.get_followers("dave") == ["bob", "carol"]
assert s2.get_followers("alice") == ["carol"]
assert s2.recommend("alice", 2) == ["dave", "erin"]
assert s2.recommend("alice", 5) == ["dave", "erin", "frank"]   # only 3 candidates exist
assert s2.recommend("alice", 0) == []

for missing_call in (lambda: net.add_user("alice"), lambda: net.follow("ghost", "bob"),
                     lambda: s1.is_following("ghost", "bob"), lambda: s1.get_following("ghost")):
    try:
        missing_call()
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

tl = FollowTimeline()
tl.follow("x", "y", 10)
tl.unfollow("x", "y", 20)
tl.follow("x", "y", 30)
tl.follow("x", "y", 35)   # duplicate: already following as of the t=30 event -> no-op
expected = {5: False, 10: True, 15: True, 20: False, 25: False, 30: True, 32: True, 100: True}
for t, exp in expected.items():
    assert tl.is_following("x", "y", t) == exp

tl2 = FollowTimeline()      # a tie at the same timestamp: the later call wins
tl2.follow("p", "q", 50)
tl2.unfollow("p", "q", 50)
assert tl2.is_following("p", "q", 50) is False
assert tl2.is_following("p", "q", 49) is False

tl3 = FollowTimeline()
tl3.follow("m", "m", 5)     # self-follow -> no-op
assert tl3.is_following("m", "m", 999) is False
assert tl3.is_following("nobody", "else", 999) is False   # a pair with no recorded event


# --- cross-validation against a naive reference ---
class NaiveSnapshot:
    """Deep-copies the whole graph and brute-force scans every query; used only to check Snapshot."""

    def __init__(self, users, following):
        self.users = set(users)
        self.following = {u: set(fs) for u, fs in following.items()}

    def is_following(self, a, b):
        if a not in self.users or b not in self.users:
            raise ValueError("unknown")
        return b in self.following[a]

    def get_following(self, u):
        if u not in self.users:
            raise ValueError("unknown")
        return sorted(self.following[u])

    def get_followers(self, u):
        if u not in self.users:
            raise ValueError("unknown")
        return sorted(a for a in self.users if u in self.following[a])

    def recommend(self, u, k):
        if u not in self.users:
            raise ValueError("unknown")
        direct = self.following[u]
        counts = Counter()
        for a in self.users:
            if a == u or a in direct:
                continue
            score = sum(1 for f in direct if a in self.following.get(f, ()))
            if score:
                counts[a] = score
        ranked = sorted(counts, key=lambda c: (-counts[c], c))
        return ranked[:k]


def random_cross_check_snapshot(trials=300, seed=0):
    rng = random.Random(seed)
    names = list("abcdefgh")
    for _ in range(trials):
        net = SocialNetwork()
        naive_users, naive_following = set(), {}
        snaps, naive_snaps = [], []
        for _ in range(rng.randint(5, 40)):
            op = rng.random()
            if op < 0.25:                                    # add_user, including duplicates
                u = rng.choice(names)
                would_ok = u not in naive_users
                try:
                    net.add_user(u)
                    assert would_ok
                except ValueError:
                    assert not would_ok
                if would_ok:
                    naive_users.add(u)
                    naive_following[u] = set()
            elif op < 0.75:                                  # follow, including self- and duplicate follows
                a, b = rng.choice(names), rng.choice(names)
                would_ok = a in naive_users and b in naive_users
                try:
                    net.follow(a, b)
                    assert would_ok
                except ValueError:
                    assert not would_ok
                if would_ok and a != b:
                    naive_following[a].add(b)
            else:                                             # snapshot, possibly followed by more edits
                snaps.append(net.create_snapshot())
                naive_snaps.append(NaiveSnapshot(naive_users, naive_following))

        for s, ns in zip(snaps, naive_snaps):                 # every earlier snapshot must still match
            for u in list(naive_users) + ["unseen"]:
                try:
                    exp, exp_err = ns.get_following(u), False
                except ValueError:
                    exp, exp_err = None, True
                try:
                    got, got_err = s.get_following(u), False
                except ValueError:
                    got, got_err = None, True
                assert exp_err == got_err
                if not exp_err:
                    assert exp == got
                    assert ns.get_followers(u) == s.get_followers(u)
                    for k in (0, 1, 2, 100):
                        assert ns.recommend(u, k) == s.recommend(u, k)
            for a in list(naive_users)[:3]:
                for b in list(naive_users)[:3]:
                    try:
                        exp, exp_err = ns.is_following(a, b), False
                    except ValueError:
                        exp, exp_err = None, True
                    try:
                        got, got_err = s.is_following(a, b), False
                    except ValueError:
                        got, got_err = None, True
                    assert exp_err == got_err and (exp_err or exp == got)


class NaiveFollowTimeline:
    """Replays the full call log, in call order, up to time t on every query."""

    def __init__(self):
        self.log = []

    def follow(self, follower, followee, t):
        if follower == followee or self.is_following(follower, followee, t):
            return
        self.log.append(("follow", follower, followee, t))

    def unfollow(self, follower, followee, t):
        if follower == followee or not self.is_following(follower, followee, t):
            return
        self.log.append(("unfollow", follower, followee, t))

    def is_following(self, follower, followee, t):
        state = False
        for kind, a, b, et in self.log:
            if a == follower and b == followee and et <= t:
                state = kind == "follow"
        return state


def random_cross_check_timeline(trials=300, seed=1):
    rng = random.Random(seed)
    names = list("xyz")
    for _ in range(trials):
        eff, naive = FollowTimeline(), NaiveFollowTimeline()
        t = 0
        for _ in range(rng.randint(5, 30)):
            t += rng.choice([0, 1, 1, 2])             # non-decreasing, with repeated timestamps sometimes
            a, b = rng.choice(names), rng.choice(names)
            if rng.random() < 0.5:
                eff.follow(a, b, t)
                naive.follow(a, b, t)
            else:
                eff.unfollow(a, b, t)
                naive.unfollow(a, b, t)
        for _ in range(60):                           # includes t before the first event and between events
            qt = rng.randint(-1, t + 2)
            a, b = rng.choice(names), rng.choice(names)
            assert eff.is_following(a, b, qt) == naive.is_following(a, b, qt)


random_cross_check_snapshot()
random_cross_check_timeline()
```

</details>

</details>
