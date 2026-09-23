# 带重叠上限的分片再平衡

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE | intervals, greedy, heap, consistent-hashing | 2 个部分 |
<!-- meta:end -->

## 题目

一个*分片*（shard）拥有一段闭区间的整数键范围 `[start, end]`（`start <= end`，两端都包含在内）；
不同分片的区间可以重叠，键的量级可以达到 $10^9$。对键 $k$，它的*覆盖数*（coverage）是区间包含 $k$
的分片个数。

```py
class Shard:
    id: str        # distinct among the shards passed to one call
    start: int
    end: int
```

### Part 1 —— 给覆盖数设上限

实现 `rebalance(limit, shards)`：收窄或丢弃一些分片，使任何键的覆盖数都不超过 `limit`，同时从最小的
原始起点到最大的原始终点之间的每个键仍至少被一个分片覆盖。

```py
def rebalance(limit: int, shards: list[Shard]) -> list[Shard]:
    """limit >= 1. Returns the surviving shards. A surviving shard's start is >= its original
    start and its end is >= its original end -- never the other way around."""
```

按下面的规则依次执行：

1. 把输入按 `start` 升序、再按 `end` 升序、再按 `id` 升序排序（id 是互不相同的字符串，所以这是一个
   全序），按这个顺序逐个处理分片。
2. 处理分片 $s$ 时，记*已保留*（kept）为在此之前按同一规则已经决定保留的那些分片，取它们各自被
   处理时由这条规则给出的区间（还没有被步骤 5 延长过）。把 $s$ 的起点后移到 $[s.start, s.end]$ 内
   最小的、仅按*已保留*分片计算覆盖数就严格小于 `limit` 的那个键；如果 $s.start$ 本身已经满足，就不
   移动。
3. 如果 $[s.start, s.end]$ 内没有任何键满足条件，丢弃 $s$——它不出现在输出中。
4. 否则 $s$ 以区间 $[\text{新起点}, s.end]$ 被保留，加入*已保留*集合，供之后处理的分片使用。
5. 所有分片都经过步骤 2–4 之后，记 $E = [\min(start), \max(end)]$ 为*全部*输入分片（不论是否保留）
   的包络。*空洞*（hole）是 $E$ 中一段极大的连续键，其中没有任何键被保留分片覆盖（按步骤 4 得到的区间
   计算）。对每个空洞，找到终点恰好是空洞前一个键的那个保留分片，把它的 end 延长到空洞的最后一个键；
   如果有多个保留分片的终点都在那里，选起点最小的，再选 id 最小的。（$E$ 的最低键总是被覆盖，所以这样的
   分片一定存在。）

最后按 `(start, end, id)` 排序返回存活的分片。

例子（`limit = 2`）：

```text
north:  [5, 40]
south:  [5, 42]
east:   [5, 44]
west:   [5, 120]
inland: [6, 42]
coast:  [130, 150]
->
north:  [5, 40]
south:  [5, 42]
east:  [41, 44]     # 平移：north 和 south 已经把 [5, 40] 填到覆盖数 2
west:  [43, 129]    # 平移：[5, 42] 上覆盖数已经处处是 2；之后再延长，补上空洞 [121, 129]
coast: [130, 150]
                    # inland 被丢弃：[6, 42] 的每个键覆盖数都已经是 2
```

另外自己写一组测试用例，至少覆盖这些情形：两个分片之间的空洞、一个分片的区间被另一个完全包含、
几个分片的区间完全相同、以及 `limit = 1`。

### Part 2 —— 增量分片与键路由

像 Part 1 那样对一批固定的分片做再平衡，并不适合分片一个一个地增删：在键空间中间收窄一个区间，
可能牵动好几个相邻分片的边界。这一问不在 Part 1 之上继续，而是从头开始：分片不再拥有一段键范围，
键到分片的映射由你自己设计。实现 `ShardRouter`：它把每个整数键分配给一个分片，分片集合每次增加或
删除一个。

```py
class ShardRouter:
    def __init__(self): ...
    def add_shard(self, shard_id: str) -> None: ...     # ValueError if already present
    def remove_shard(self, shard_id: str) -> None: ...  # ValueError if absent
    def locate(self, key: int) -> str: ...              # owner's id; LookupError if there are no shards
```

要求：

- `locate` 的结果只取决于键和当前的分片 id 集合：与分片加入的先后次序无关，也与进程无关，所以重启之后
  同一个键仍然落到同一个分片。
- 只迁移必须迁移的键：`add_shard(x)` 之后，每个换了主人的键现在都归 `x`；`remove_shard(x)` 之后，每个
  换了主人的键原来都归 `x`。
- 键分布大致均匀：有 $N$ 个分片时，每个分片大约拥有 $1/N$ 的键。

例子（在键 `0..29_999` 上）：

```text
r = ShardRouter()
r.add_shard("amber"); r.add_shard("cobalt"); r.add_shard("jade")
    # 三个分片各拥有大约三分之一的键
r.add_shard("slate")
    # 大约四分之一的键换了主人，而且全都归了 "slate"
r.remove_shard("cobalt")
    # 换主人的恰好是原来归 "cobalt" 的那些键（同样大约四分之一）
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得先确认：多个分片的 `start` 和 `end` 都相同时用什么次序决胜（这里用 id 排序）；
`rebalance` 能不能修改传入的 `Shard` 对象（这里的实现不会）。

### Part 1

这条平移规则，其实就是把作业分配给 `limit` 台同型机器中最早可用的那一台的经典贪心算法（区间划分 /
房间数固定的“会议室”问题）。给每台机器记一个“下一次空闲的键”（每台机器一开始就是空闲的）。把分片
$s$ 交给空闲键最小的那台机器，取值为 $t$：如果 $t \le s.start$，$s$ 保留自己的起点；否则起点变成
$t$；如果这个起点超过了 $s.end$，就把这台机器原样还回去、丢弃 $s$；否则这台机器的空闲键变成
$s.end + 1$。

这个起点 $\max(s.start, t)$ 恰好就是规则要找的那个键。每台机器从 $s.start$ 到它的空闲键减一之间的每个键
上都是忙的：它最近分到的区间要么保留了自己的起点，而分片按起点顺序到达，所以这个起点不超过 $s.start$；
要么被平移到恰好从这台机器上一个区间结束的地方开始，对上一个区间同样可以这样论证。所以
$[s.start, t - 1]$ 中的每个键都被全部 `limit` 台机器覆盖，而在 $\max(s.start, t)$ 处被选中的那台机器
是空闲的；这个键如果超过了 $s.end$，规则就丢弃 $s$，正是步骤 3 的要求。

因为一个分片只有在某台机器上一个区间彻底结束之后才会加入它，所以每台机器自己分到的区间两两不相交，
任何一个键最多只能被其中一台机器覆盖——一共 `limit` 台机器，覆盖数就永远不会超过 `limit`。移动一次
就够了，不需要在 $[\text{新起点}, s.end]$ 内部再去找后面某个覆盖数又冲回 `limit` 的键：被选中的机器
在全部 `limit` 台里空闲键*最小*，所以它一旦空闲，之后的每一个键它也都是空闲的，从此永远贡献 $0$；
其余 `limit - 1` 台机器每台最多贡献 $1$，加在一起，在新起点及之后的任何键上覆盖数最多是
`limit - 1`，加上 $s$ 之后最多是 `limit`。

平移从来不会造出空洞：平移跳过的每个键、被丢弃分片的每个键，在保留分片中的覆盖数都已经是
`limit` $\ge 1$，而保留分片之后不会再被缩短。所以步骤 5 的空洞恰好就是输入里本来就有的空洞，每个空洞只
用一个分片去补，覆盖数从 $0$ 变成 $1$。

```python
import heapq

NEG_INF = float('-inf')


class Shard:
    def __init__(self, id, start, end):
        self.id, self.start, self.end = id, start, end

    def __repr__(self):
        return f"Shard({self.id!r}, {self.start}, {self.end})"


def rebalance(limit, shards):
    if not shards:
        return []
    order = sorted(shards, key=lambda sh: (sh.start, sh.end, sh.id))

    free_times = []    # min-heap of "next free key" for machines in use; size <= limit
    kept = []
    for sh in order:
        if len(free_times) < limit:
            t_min = NEG_INF                       # an unused machine: always free
        else:
            t_min = heapq.heappop(free_times)
        new_start = sh.start if t_min <= sh.start else t_min
        if new_start > sh.end:
            if t_min != NEG_INF:
                heapq.heappush(free_times, t_min)  # NOTE: hand the machine back unused, don't drop it
            continue
        kept.append(Shard(sh.id, new_start, sh.end))
        heapq.heappush(free_times, sh.end + 1)

    if not kept:
        return []

    # Gap fill: scan the kept shards in (start, end, id) order of their step-4 ranges.
    kept.sort(key=lambda sh: (sh.start, sh.end, sh.id))
    frontier = kept[0].start - 1        # NOTE: the very first PROCESSED shard is never shifted (the
    frontier_owner = None               #       heap starts empty), so kept[0].start == min(all starts)
    for sh in kept:
        if sh.start > frontier + 1:
            frontier_owner.end = sh.start - 1     # NOTE: only stretches over keys with coverage 0
        if sh.end > frontier:           # NOTE: strict '>': ties go to the smallest (start, id)
            frontier, frontier_owner = sh.end, sh
    # NOTE: no hole after the last kept shard -- the largest input end is always covered

    kept.sort(key=lambda sh: (sh.start, sh.end, sh.id))
    return kept
```

排序是 $O(n \log n)$；堆里最多同时放 `limit` 个空闲键，所以 $n$ 个分片里每一个只花
$O(\log(\min(n, limit)))$ 做一次出堆和一次入堆，补洞那一段的两次排序又是 $O(n \log n)$——合起来是
$O(n \log n)$，任何一步都不会去挨个扫描键。

### Part 2

用*一致性哈希*（consistent hashing）加*虚拟节点*（virtual node）：把每个分片哈希到一个由哈希值构成的环上的
`num_vnodes` 个点（虚拟节点），把键也哈希到同一个环上，键归沿顺时针方向离它最近的虚拟节点，越过最大的
就绕回最小的。哈希用 `hashlib.md5`，不用内置的 `hash()`，因为后者会被 `PYTHONHASHSEED` 在不同进程间
随机化；这样虚拟节点的位置只取决于分片 id，满足第一条要求。环用两个按哈希值排好序的平行列表保存；`locate`
就是用 `bisect` 找到第一个不小于这个键自身哈希值的虚拟节点，越过末尾就绕回下标 0。

一个键的主人是沿顺时针方向离它最近的虚拟节点。插入一个新的虚拟节点 $v$，只会改变 $v$ 和它前一个
虚拟节点之间那段弧上的键的归属——它们从原来拥有整段弧的那个分片，换给 $v$ 所在的分片；其余每一段弧、
从而其余每一个键都不受影响。删除一个虚拟节点是同一句话反过来说：它那段弧上的键换给现在紧接在它之后
的虚拟节点，其余不变。`add_shard` 和 `remove_shard` 各自恰好触及 `num_vnodes` 段这样的弧，所以只有
这些弧里的键会移动。

虚拟节点是为第三条要求准备的。每个分片只有一个点时，各段弧长短悬殊：20 个分片里，实测最大的份额是
公平份额 $1/N$ 的 3.5 倍。一个分片的份额是 `num_vnodes` 段相互独立的弧长之和，所以它的相对离散程度
缩小到大约 $1/\sqrt{\text{num\_vnodes}}$：取 150 时是 8%，同样 20 个分片的实测值是 11%。

```python
import bisect
import hashlib


def _ring_hash(text):
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


class ShardRouter:
    def __init__(self, num_vnodes=150):
        self.num_vnodes = num_vnodes
        self._ring_hashes = []     # sorted
        self._ring_owner = []      # _ring_owner[i] owns _ring_hashes[i]
        self._shards = set()

    def add_shard(self, shard_id):
        if shard_id in self._shards:
            raise ValueError(f"shard already present: {shard_id}")
        self._shards.add(shard_id)
        for v in range(self.num_vnodes):
            h = _ring_hash(f"{shard_id}#{v}")
            i = bisect.bisect_left(self._ring_hashes, h)
            self._ring_hashes.insert(i, h)          # NOTE: O(T) per insertion -- a plain sorted list
            self._ring_owner.insert(i, shard_id)

    def remove_shard(self, shard_id):
        if shard_id not in self._shards:
            raise ValueError(f"no such shard: {shard_id}")
        self._shards.discard(shard_id)
        keep = [(h, o) for h, o in zip(self._ring_hashes, self._ring_owner) if o != shard_id]
        self._ring_hashes = [h for h, _ in keep]
        self._ring_owner = [o for _, o in keep]

    def locate(self, key):
        if not self._ring_hashes:
            raise LookupError("locate() called with no shards")
        h = _ring_hash(str(key))
        i = bisect.bisect_left(self._ring_hashes, h)
        if i == len(self._ring_hashes):
            i = 0                                   # wrap past the largest hash
        return self._ring_owner[i]
```

`locate` 是 $O(\log T)$，$T$ 是环上虚拟节点总数。`add_shard` 要做 `num_vnodes` 次独立的
`list.insert`，每次都要花 $O(T)$ 搬动列表后半段，所以一次调用是 $O(\text{num\_vnodes} \cdot T)$；
`remove_shard` 改成一次线性扫描重建两个列表，代价是 $O(T)$，与 `num_vnodes` 无关。换成平衡树或跳表
也能把 `add_shard` 降到 $O(\text{num\_vnodes} \log T)$。取 12 个分片、每个 150 个虚拟节点，新增第
13 个分片让键 `0..19_999` 中 8.1% 换了主人，接近平均分配下 $1/13 \approx 7.7\%$ 的理论值；删掉 13 个里的
1 个，换主人的是 8.4%。*最高随机权重哈希*（rendezvous hashing）把每个键交给 `(key, shard_id)` 这对值哈希最大的
分片，不需要环也满足同样三条要求，代价是每次 `locate` 为 $O(N)$。

### 追问

- Part 1 的规则并没有显式地让数据移动量最小，它只是把起点或终点往后移。这样做的代价取决于移动量按键的
  个数算还是按字节数算——分片之间单键负载差别很大时，两者会给出不同答案。
- 处理顺序决定谁让路：起点相同的分片里，较短的先处理，平移落在较长的分片身上。如果改成先处理范围大或
  存活时间长的分片，只移动起点的做法就不再够用，因为后处理的分片里覆盖数已达 `limit` 的键可能落在它区间的中间。
- Part 2 的哈希环平衡的是每个分片的键*个数*，不是查询量；如果某个分片因为少数几个热键而负载偏高，
  需要另外的手段，比如给这些键单独配一张路由表，或者把它们复制到多个分片上。
- 给一个已经再平衡过的 Part 1 结果新增一个区间分片，不需要整体重跑：只有区间与新分片相交的保留分片可能
  变化；另外，如果新分片的起点在包络终点之后、中间隔着空洞，被延长去接上它的那个保留分片也会变。

<details>
<summary>验证代码（可运行）</summary>

```python
import collections
import hashlib
import itertools
import random
import statistics


def reference_rebalance(limit, shards):
    """Independent reading of the rule: sort by (start, end, id); for each shard scan its own
    range key by key and stop at the first key where coverage among ALREADY-KEPT shards is below
    `limit`; if no such key exists, drop it. Then walk the envelope key by key and give every
    zero-coverage key to the kept shard that ends right before it (smallest start, then id).
    No heap, no helper shared with rebalance() -- only meant for small coordinate ranges."""
    order = sorted(shards, key=lambda sh: (sh.start, sh.end, sh.id))
    kept = []  # [id, start, end]
    for sh in order:
        new_start = None
        for k in range(sh.start, sh.end + 1):
            cov = sum(1 for _, ks, ke in kept if ks <= k <= ke)
            if cov < limit:
                new_start = k
                break
        if new_start is not None:
            kept.append([sh.id, new_start, sh.end])
    if not kept:
        return []
    lo, hi = min(sh.start for sh in shards), max(sh.end for sh in shards)
    for k in range(lo, hi + 1):
        if sum(1 for _, ks, ke in kept if ks <= k <= ke) == 0:
            assert not any(sh.start <= k <= sh.end for sh in shards)   # holes come only from the input
            owner = min((g for g in kept if g[2] == k - 1), key=lambda g: (g[1], g[0]))
            owner[2] = k
    kept.sort(key=lambda g: (g[1], g[2], g[0]))
    return [Shard(i, s, e) for i, s, e in kept]


def check_properties(limit, shards, out):
    by_id = {s.id: s for s in shards}
    for sh in out:
        orig = by_id[sh.id]
        assert sh.start >= orig.start and sh.end >= orig.end, (sh, orig)   # NOTE: truncate then extend only
    lo, hi = min(s.start for s in shards), max(s.end for s in shards)
    for k in range(lo, hi + 1):
        cov = sum(1 for sh in out if sh.start <= k <= sh.end)
        assert cov <= limit, (limit, shards, out, k, cov)
        assert cov >= 1, (limit, shards, out, k, cov)


def as_tuples(out):
    return [(s.id, s.start, s.end) for s in out]


def gen_shard_sets(n, coord_max):
    ids = [chr(ord('A') + i) for i in range(n)]
    for combo in itertools.product(itertools.combinations_with_replacement(range(coord_max + 1), 2), repeat=n):
        yield [Shard(ids[i], combo[i][0], combo[i][1]) for i in range(n)]


checked = 0
for n in (1, 2, 3, 4):
    for limit in (1, 2, 3):
        for shards in gen_shard_sets(n, coord_max=4):
            got = rebalance(limit, shards)
            assert as_tuples(got) == as_tuples(reference_rebalance(limit, shards)), (limit, shards, got)
            check_properties(limit, shards, got)
            checked += 1
print(f"exhaustive: {checked} shard sets (<= 4 shards, coordinates 0..4), 0 mismatches with the reference")

rng = random.Random(0)
for trial in range(6000):
    n = rng.randint(0, 8)
    limit = rng.randint(1, 4)
    span = 12 if trial % 2 else 40              # the narrow span produces many ties
    ids = rng.sample("abcdefghij", n)
    shards = [Shard(ids[i], *sorted((rng.randint(0, span), rng.randint(0, span)))) for i in range(n)]
    got = rebalance(limit, shards)
    assert as_tuples(got) == as_tuples(reference_rebalance(limit, shards)), (limit, shards, got)
    if shards:
        check_properties(limit, shards, got)
print("random: 6000 trials against the reference, all agree, all three properties hold")

ex1 = [Shard('north', 5, 40), Shard('south', 5, 42), Shard('east', 5, 44), Shard('west', 5, 120),
       Shard('inland', 6, 42), Shard('coast', 130, 150)]
assert as_tuples(rebalance(2, ex1)) == [
    ('north', 5, 40), ('south', 5, 42), ('east', 41, 44), ('west', 43, 129), ('coast', 130, 150)]
assert as_tuples(ex1) == [('north', 5, 40), ('south', 5, 42), ('east', 5, 44), ('west', 5, 120),
                          ('inland', 6, 42), ('coast', 130, 150)]   # the input is not mutated

# y (processed first) and x both end up as [3, 6]; the hole [7, 9] goes to x, the smaller id
tie = [Shard('m', 0, 2), Shard('n', 0, 2), Shard('y', 1, 6), Shard('x', 3, 6), Shard('p', 10, 12)]
assert as_tuples(rebalance(2, tie)) == [('m', 0, 2), ('n', 0, 2), ('y', 3, 6), ('x', 3, 9), ('p', 10, 12)]

# keys up to 1e9 in magnitude: check the cap and the absence of holes with an endpoint sweep
rng = random.Random(3)
big = []
for i in range(20_000):
    lo_key = rng.randint(-10**9, 10**9)
    big.append(Shard(f"b{i}", lo_key, lo_key + rng.randint(0, 10**6)))
out = rebalance(3, big)
events = sorted([(s.start, 1) for s in out] + [(s.end + 1, -1) for s in out])   # -1 sorts first
assert events[0][0] == min(s.start for s in big) and events[-1][0] == max(s.end for s in big) + 1
active, position = 0, events[0][0]
for key, delta in events:
    assert key == position or active >= 1       # every key of [position, key - 1] is covered
    active, position = active + delta, key
    assert active <= 3
print(f"large keys: {len(big)} shards -> {len(out)} kept, cap and coverage hold")

# Follow-up: adding one shard to a rebalanced output only changes the shards it intersects,
# plus the shard extended to meet it when it starts past the envelope with a hole in between
rng = random.Random(2)
for _ in range(3000):
    limit = rng.randint(1, 3)
    base = [Shard(f"s{i}", *sorted((rng.randint(0, 25), rng.randint(0, 25)))) for i in range(rng.randint(1, 6))]
    out = rebalance(limit, base)
    new = Shard("new", *sorted((rng.randint(0, 30), rng.randint(0, 30))))
    again = {s.id: (s.start, s.end) for s in rebalance(limit, out + [new])}
    hi = max(s.end for s in out)
    may_change = {s.id for s in out if s.start <= new.end and new.start <= s.end}
    if new.start > hi + 1:
        may_change.add(min((s for s in out if s.end == hi), key=lambda s: (s.start, s.id)).id)
    assert all(again.get(s.id) == (s.start, s.end) for s in out if s.id not in may_change)
print("follow-up: 3000 single-shard additions touched only the predicted shards")


def md5_int(text):
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


def clockwise_owner(shard_ids, num_vnodes, key):
    """Independent of ShardRouter's lists and bisect: the vnode at the smallest clockwise distance."""
    kh = md5_int(str(key))
    dist, owner = min(((md5_int(f"{sid}#{v}") - kh) % (1 << 128), sid)
                      for sid in shard_ids for v in range(num_vnodes))
    return owner


trio = ["amber", "cobalt", "jade"]
small = ShardRouter(num_vnodes=5)
for sid in trio:
    small.add_shard(sid)
top = max(md5_int(f"{sid}#{v}") for sid in trio for v in range(5))
wrap_keys = [k for k in range(5000) if md5_int(str(k)) > top]    # hash past the largest vnode
assert len(wrap_keys) > 50
for k in list(range(2000)) + wrap_keys:
    assert small.locate(k) == clockwise_owner(trio, 5, k)
reverse = ShardRouter(num_vnodes=5)
for sid in reversed(trio):
    reverse.add_shard(sid)
assert all(reverse.locate(k) == small.locate(k) for k in range(5000))   # independent of add order
print(f"Part 2: locate agrees with the clockwise-distance owner, including {len(wrap_keys)} wrap-around keys")

rng = random.Random(1)
router, present, keys, owners = ShardRouter(), [], range(4000), None
for step in range(30):
    if present and (len(present) > 6 or rng.random() < 0.4):
        x = rng.choice(present)
        present.remove(x)
        router.remove_shard(x)
    else:
        x = f"shard-{step}"
        present.append(x)
        router.add_shard(x)
    now = {k: router.locate(k) for k in keys} if present else None
    if owners and now:
        for k in keys:
            if now[k] != owners[k]:
                assert x in (now[k], owners[k]) and (now[k] == x) == (x in present)
    owners = now
print("Part 2: 30 random additions and removals, every moved key moved to or from that shard")

ex = ShardRouter()
for sid in trio:
    ex.add_shard(sid)
keys = range(30_000)
before = {k: ex.locate(k) for k in keys}
share = collections.Counter(before.values())
assert all(0.28 < share[s] / len(keys) < 0.39 for s in trio)
ex.add_shard("slate")
after_add = {k: ex.locate(k) for k in keys}
moved = [k for k in keys if before[k] != after_add[k]]
assert all(after_add[k] == "slate" for k in moved) and 0.2 < len(moved) / len(keys) < 0.3
ex.remove_shard("cobalt")
after_remove = {k: ex.locate(k) for k in keys}
moved = {k for k in keys if after_add[k] != after_remove[k]}
assert moved == {k for k in keys if after_add[k] == "cobalt"} and 0.2 < len(moved) / len(keys) < 0.3

ring = ShardRouter(num_vnodes=150)
for sid in [f"shard-{i}" for i in range(12)]:
    ring.add_shard(sid)
sample_keys = range(20_000)
before = {k: ring.locate(k) for k in sample_keys}
ring.add_shard("shard-new")
after_add = {k: ring.locate(k) for k in sample_keys}
moved_add = sum(before[k] != after_add[k] for k in sample_keys) / len(sample_keys)
ring.remove_shard("shard-0")
moved_remove = sum(after_add[k] != ring.locate(k) for k in sample_keys) / len(sample_keys)
assert 0.06 < moved_add < 0.10 and 0.06 < moved_remove < 0.10
print(f"Part 2: adding a 13th shard moved {moved_add:.1%} of the keys, removing 1 of 13 moved {moved_remove:.1%}")

twenty = [f"shard-{i}" for i in range(20)]
for num_vnodes in (1, 150):
    r = ShardRouter(num_vnodes=num_vnodes)
    for sid in twenty:
        r.add_shard(sid)
    count = collections.Counter(r.locate(k) for k in range(20_000))
    fair = [count[s] * len(twenty) / 20_000 for s in twenty]     # 1.0 = exactly 1/N
    print(f"Part 2: 20 shards x {num_vnodes} vnodes: largest share {max(fair):.2f}x fair, "
          f"relative spread {statistics.pstdev(fair):.0%}")
    if num_vnodes == 1:
        assert max(fair) > 2.5
    else:
        assert statistics.pstdev(fair) < 0.15 and 0.65 < min(fair) and max(fair) < 1.35

print("all checks passed")
```

</details>

</details>
