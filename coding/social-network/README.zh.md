# 关注图与两跳推荐（社交网络）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★★ | 中等 | SWE · RE | graph, hashmap, snapshot, binary-search | 4 个部分 |
<!-- meta:end -->

## 题目

一个社交网络维护一组用户，以及用户之间有方向的*关注*（follow）关系：`A` 关注 `B` 并不意味着 `B` 也关注 `A`。
完成下面四个部分。

### Part 1 —— 用户、关注与快照

`SocialNetwork` 维护实时的、可变的状态。`Snapshot` 把这个状态冻结在某一时刻：无论之后 `SocialNetwork`
发生什么变化，一个已经返回的 `Snapshot` 始终只回答它被创建那一刻的状态。

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

例子：注册 `alice`、`bob`、`carol`、`dave`；调用 `follow("alice", "bob")` 和 `follow("alice", "carol")`；
取一个快照 `s1`。之后在这个实时网络上调用 `follow("bob", "dave")`。`s1.is_following("alice", "carol")`
是 `True`，但 `s1.is_following("bob", "dave")` 是 `False`——`s1` 创建时这条边还不存在。在第二次 `follow`
调用之后再取一个快照，对同样的查询会返回 `True`。（在任意时刻再调用一次 `follow("alice", "bob")`，
或者调用 `follow("alice", "alice")`，都不会改变以上任何结果。）

### Part 2 —— 关注列表与粉丝列表

给 `Snapshot` 扩充下面两个方法，返回的列表都按用户 id 升序排列。

```py
class Snapshot:
    def get_following(self, user_id: str) -> list[str]:
        """Users user_id follows, as of this snapshot, sorted by user id ascending.
        Raises ValueError if user_id is unknown to this snapshot."""

    def get_followers(self, user_id: str) -> list[str]:
        """Users who follow user_id, as of this snapshot, sorted by user id ascending.
        Raises ValueError if user_id is unknown to this snapshot."""
```

例子：接着 Part 1，假设在取第二个快照 `s2` 之前，`bob` 又关注了 `erin`，`carol` 关注了 `dave`、`frank`、
`bob`、`alice`。`s2.get_following("carol")` 是 `["alice", "bob", "dave", "frank"]`，
`s2.get_followers("dave")` 是 `["bob", "carol"]`。

### Part 3 —— 两跳推荐

对 `user_id` 而言，一个*候选人*（candidate）是指通过 `user_id` 的某个关注对象可以到达的用户，
但要排除 `user_id` 自己，以及 `user_id` 已经直接关注的人。一个候选人的*得分*（score）是能到达它的、
`user_id` 的不同关注对象的个数。

```py
class Snapshot:
    def recommend(self, user_id: str, k: int) -> list[str]:
        """Top-k two-hop recommendations for user_id, ranked by score descending, ties
        broken by user id ascending. Returns fewer than k entries if fewer candidates
        exist. Raises ValueError if user_id is unknown to this snapshot."""
```

例子：用 Part 2 的 `s2`（`alice` 关注 `bob`、`carol`；`bob` 关注 `dave`、`erin`；`carol` 关注 `dave`、
`frank`、`bob`、`alice`），`s2.recommend("alice", 2)` 是 `["dave", "erin"]`——`dave` 同时经 `bob`
和 `carol` 到达（得分 2），`erin` 只经 `bob` 到达（得分 1，按用户 id 排在同为得分 1 的 `frank` 之前）。
`bob` 虽然也能经 `carol` 到达，但因为 `alice` 已经直接关注他而被排除。`s2.recommend("alice", 5)` 是
`["dave", "erin", "frank"]`，因为候选人一共只有三个。

### Part 4 —— 按时间点查询

现在不再只能在显式调用 `create_snapshot()` 的那些时刻查询，而要让网络支持直接查询任意过去的时刻。
每次 `follow`/`unfollow` 调用都带上发生的时间 `t`；对同一个 `FollowTimeline`，`follow()`/`unfollow()`
调用按 `t` 非降序到达，但 `is_following()` 可以用任意 `t` 调用，不必是最近的那个。这个类不需要
`add_user`：一个用户 id 从它第一次出现在某次调用里开始就存在；对从未有过记录的一对用户，
`is_following` 恒为 `False`。

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

例子：依次调用 `follow("x", "y", 10)`、`unfollow("x", "y", 20)`、`follow("x", "y", 30)`。
`is_following("x", "y", t)` 在 `t < 10` 时是 `False`，在 `10 <= t < 20` 时是 `True`，
在 `20 <= t < 30` 时是 `False`，在 `t >= 30` 时是 `True`。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得确认：`Snapshot` 查询未知 id 时应该报错还是当作“没有关注关系”处理（本文选择报错，
与 `follow()` 一致）；Part 4 的事件流是否真的保证按 `t` 非降序到达——这正是每一对用户自己的
事件列表天然有序、不必额外排序的前提。

### Part 1

两个类都用 `dict[str, set[str]]` 存邻接关系。用 `set` 之后，`follow` 和判断重复关注都是 O(1) 的：
对已存在的元素调用 `set.add` 本身就是空操作，所以唯一需要显式判断的规则是自己关注自己。
真正的坑在 `create_snapshot`：只拷贝*外层*字典是不够的，因为*内层*的 set 仍然是原来那些对象，
实时的 `SocialNetwork` 还在改它们。

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

`get_following` 只是把存好的 set 排序返回。`get_followers` 如果在调用时才去扫描每个用户的关注集合，
无论答案有多小，代价都是每次 O(用户数 + 边数)；把反向索引放到上面那个本来就是 O(用户数 + 边数) 的
构造过程里一次性建好，两个方法的开销就都只取决于各自答案的大小。

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

对 `user_id` 的每个关注对象 `f`，`f` 自己关注的每个 `c` 都在 `Counter` 里记一分；因为 `_following[f]`
是一个 set，每个 `f` 对同一个 `c` 最多贡献一次，所以候选人最终的得分恰好就是能到达它的、不同 `f`
的个数。按 `(-score, user_id)` 排序，一步就同时得到“得分降序”和“按字母序打破并列”；切片 `[:k]`
顺带处理了 `k` 大于候选人数量的情况。

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

设 $n$ 为快照时刻的用户数，$m$ 为关注边数，$d(u)$ 为 $u$ 关注的人数，$d^-(u)$ 为关注 $u$ 的人数。
对 `recommend`，记 $F = d(\text{user\_id})$，$C$ 为找到的候选人个数；内层双重循环一共要访问
$\sum_{f} d(f) = O(F \cdot G)$ 对 $(f, c)$，其中 $G$ 是 `user_id` 各个关注对象出度的平均值。

| 方法 | 时间 | 空间 |
| --- | --- | --- |
| `add_user`、`follow` | O(1) | O(1) |
| `create_snapshot` | O(n + m) | O(n + m) |
| `is_following` | O(1) | O(1) |
| `get_following(u)` | $O(d(u) \log d(u))$ | $O(d(u))$ |
| `get_followers(u)` | $O(d^-(u) \log d^-(u))$ | $O(d^-(u))$ |
| `recommend(u, k)` | $O(F \cdot G + C \log C)$ | $O(C)$ |

### Part 4

对每一对 `(follower, followee)`，只保存它状态翻转的那些时刻，按调用发生的先后顺序存放。
因为整体的调用流按 `t` 非降序到达，每一对用户自己的列表也是递增地被追加的，天然有序，
不需要额外排序。这个列表的内容永远是 开始、结束、开始、结束……交替，并且以“开始”打头，
因为在没有关注时调用 `unfollow` 是空操作，在已经关注时调用 `follow` 也是空操作；因此
`is_following(follower, followee, t)` 只需要数出“时刻不超过 `t` 的事件有多少个”：这个数是奇数，
就说明最近一次事件是“开始”。

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

用 `bisect_right` 而不是 `bisect_left`，正是为了让恰好发生在 `t` 时刻的事件已经生效——这等价于把每一段
关注关系存成一个 `[开始, 结束)` 区间，再判断 `t` 是否落在其中一段里。`follow`/`unfollow` 均摊 O(1)；
`is_following` 是 $O(\log e)$，$e$ 为这一对用户目前记录下的翻转事件数。朴素做法——每次查询都从头
重放整个调用日志——则要付出 O(目前为止全部调用次数) 的代价。

### 追问

- 每次 `create_snapshot()` 都深拷贝全部关注集合，图很大、快照又频繁时很浪费。写时复制
  （copy-on-write）能把这个代价降到 O(1)：快照之后的 `follow()` 只替换它实际改动的那一个关注集合，
  不去碰仍然与更早快照共享的那些，而任何早先的快照都不会看到这次替换。
- 只保存相邻快照之间的差量，或者给每条边单独存一个 `[开始, 结束)` 有效区间，都能避免每次快照都
  拷贝一整张图，并且可以靠过滤这份记录还原任意历史时刻。
- 多个 `Snapshot` 的读操作可以完全并行，因为它们只读冻结的状态；一把读写锁（或者上面那种
  写时复制方案，读者甚至完全不需要加锁）就能让 `follow()` 的写操作与它们互斥，而不阻塞读。
- `recommend` 可以不对每个中间人一视同仁，而是按 `user_id` 与其互动的新近程度加权；也可以把同一个
  计数步骤再往外推一层，得到三跳推荐。

<details>
<summary>验证代码（可运行）</summary>

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
