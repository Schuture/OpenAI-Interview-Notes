# Shard Rebalancing with an Overlap Limit

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★☆☆ | Medium | SWE | intervals, greedy, heap, consistent-hashing | 2 parts |
<!-- meta:end -->

## Problem

A *shard* owns a closed range of integer keys `[start, end]` (`start <= end`, both ends included);
the ranges of different shards may overlap, and keys can be as large in magnitude as $10^9$. For a
key $k$, its *coverage* is the number of shards whose range contains $k$.

```py
class Shard:
    id: str        # distinct among the shards passed to one call
    start: int
    end: int
```

### Part 1 — Capping overlap

Implement `rebalance(limit, shards)`, which narrows and drops shards so that no key's coverage
exceeds `limit`, while every key from the smallest original start to the largest original end stays
covered by at least one shard.

```py
def rebalance(limit: int, shards: list[Shard]) -> list[Shard]:
    """limit >= 1. Returns the surviving shards. A surviving shard's start is >= its original
    start and its end is >= its original end -- never the other way around."""
```

Apply the following rule, in order:

1. Sort the input by `start` ascending, then `end` ascending, then `id` ascending (ids are
   distinct strings, so this is a total order), and process the shards one at a time in that
   order.
2. When shard $s$ is processed, let *kept* be the shards already decided to be kept earlier in
   this order, each with the range this same rule gave it when it was processed (never yet
   extended by step 5). Shift $s$'s start forward to the smallest key in $[s.start, s.end]$
   at which the coverage counted over *kept* alone is strictly less than `limit`; if $s.start$
   itself already qualifies, nothing is shifted.
3. If no key in $[s.start, s.end]$ qualifies, drop $s$ -- it does not appear in the output.
4. Otherwise $s$ is kept with range $[\text{new start}, s.end]$ and joins *kept* for the shards
   processed afterwards.
5. Once every shard has been through steps 2-4, let $E = [\min(start), \max(end)]$ be the
   envelope over *every* input shard, kept or not. A *hole* is a maximal run of keys in $E$ that
   no kept shard covers, using the ranges from step 4. Close each hole by extending the end of the
   kept shard that ends at the key just before the hole up to the hole's last key; if several kept
   shards end there, extend the one with the smallest start, then the smallest id. ($E$'s lowest
   key is always covered, so such a shard always exists.)

Return the survivors sorted by their final `(start, end, id)`.

Example, with `limit = 2`:

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
east:  [41, 44]     # shifted: north and south already fill [5, 40] to coverage 2
west:  [43, 129]    # shifted: coverage is already 2 on all of [5, 42]; extended over the hole [121, 129]
coast: [130, 150]
                    # inland is dropped: every key of [6, 42] already has coverage 2
```

### Part 2 — Incremental shards and key routing

Rebalancing a fixed batch, as in Part 1, does not fit a shard being added or removed one at a
time: narrowing one range in the middle of the key space can shift several neighbours' boundaries.
Implement `ShardRouter`, which assigns every integer key to one shard of a set that changes one
shard at a time.

```py
class ShardRouter:
    def __init__(self): ...
    def add_shard(self, shard_id: str) -> None: ...     # ValueError if already present
    def remove_shard(self, shard_id: str) -> None: ...  # ValueError if absent
    def locate(self, key: int) -> str: ...              # owner's id; LookupError if there are no shards
```

Requirements:

- `locate` depends only on the key and the current set of shard ids: not on the order in which the
  shards were added, and not on the process, so a key maps to the same shard after a restart.
- Only the keys that must move do: after `add_shard(x)`, every key whose owner changed is now
  owned by `x`; after `remove_shard(x)`, every key whose owner changed was owned by `x`.
- Keys spread about evenly: with $N$ shards, each owns roughly $1/N$ of them.

Example, over the keys `0..29_999`:

```text
r = ShardRouter()
r.add_shard("amber"); r.add_shard("cobalt"); r.add_shard("jade")
    # each of the three owns roughly a third of the keys
r.add_shard("slate")
    # roughly a quarter of the keys change owner, and every one of them now belongs to "slate"
r.remove_shard("cobalt")
    # exactly the keys "cobalt" owned (again roughly a quarter) change owner
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming first: the tie-break when several shards share both `start` and `end` (id order
here), and whether `rebalance` may mutate the `Shard` objects passed in (this implementation does
not).

### Part 1

The shift rule is exactly the classic greedy for assigning jobs to the earliest-available one of
`limit` identical machines (interval partitioning / "meeting rooms" with a fixed room count).
Track, for each machine, the next key at which it is free (every machine starts free). Give shard
$s$ to the machine with the smallest free key $t$: if $t \le s.start$, $s$ keeps its own start,
otherwise its start becomes $t$; if that start is past $s.end$, hand the machine back unused and
drop $s$, otherwise the machine's free key becomes $s.end + 1$.

This start, $\max(s.start, t)$, is exactly the key the rule looks for. Every machine is busy on
every key from $s.start$ up to its free key minus one: its latest range either kept its own start,
which is at most $s.start$ because shards arrive in start order, or was shifted to begin right
where the machine's previous range ended, and the same argument applies to that range. So every
key in $[s.start, t - 1]$ is covered by all `limit` machines, while at $\max(s.start, t)$ the
chosen machine is free; when that key is past $s.end$, the rule drops $s$, as step 3 requires.

Because a shard only ever joins a machine once that machine's previous range has fully ended,
every machine's own assigned ranges are pairwise disjoint, so at most one of them can cover any
given key -- with `limit` machines, coverage can never exceed `limit`. A single shift is enough,
with no need to check further inside $[\text{new start}, s.end]$ for a later key where coverage
climbs back to `limit`: the chosen machine has the *smallest* free key among all `limit` machines,
so once it is free it stays free at every later key too, contributing $0$ there for good; the
other `limit - 1` machines contribute at most $1$ each, so together they cover any key at or past
$\text{new start}$ at most `limit - 1` times, and adding $s$ brings that to at most `limit`.

Shifts never open a hole: every key a shift skips, and every key of a dropped shard, already has
coverage `limit` $\ge 1$ among the kept shards, and kept shards are never shortened afterwards. So
the holes of step 5 are exactly the holes already present in the input, and filling each with a
single shard raises its coverage from $0$ to $1$.

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

Sorting is $O(n \log n)$; the heap never holds more than `limit` free times, so each of the $n$
shards costs $O(\log(\min(n, limit)))$ for one pop and one push, and the two sorts in the gap-fill
pass are $O(n \log n)$ again -- $O(n \log n)$ total, and no step ever inspects an individual key.

### Part 2

Use *consistent hashing* with *virtual nodes*: hash each shard to `num_vnodes` points (vnodes) on a
ring of hash values, hash each key onto the same ring, and give the key to the nearest vnode
clockwise from it, wrapping past the largest back to the smallest. Hash with `hashlib.md5` -- not
the built-in `hash()`, which `PYTHONHASHSEED` randomizes across processes -- so the vnode positions
depend only on the shard ids, as the first requirement asks. Keep the ring as two parallel lists
sorted by hash; `locate` is a `bisect` lookup for the first vnode at or after the key's own hash,
wrapping to index 0 past the end.

A key's owner is the nearest vnode clockwise from it. Inserting one new vnode $v$ changes
the owner of exactly the keys in the arc between $v$ and the vnode immediately before it -- they
move from whatever shard owned that whole arc before to $v$'s shard; every other arc, and hence
every other key, is untouched. Removing a vnode is the same statement backwards: its arc's keys
move to the vnode now immediately after it, and nothing else changes. Since `add_shard` and
`remove_shard` each touch exactly `num_vnodes` such arcs, only keys in those arcs ever move.

The vnodes are there for the third requirement. With one point per shard, arc lengths vary widely:
among 20 shards, the largest share measured was 3.5 times the fair $1/N$. A shard's share is the
sum of `num_vnodes` independent arcs, so its relative spread shrinks to about
$1/\sqrt{\text{num\_vnodes}}$: 8% at 150, and 11% measured over the same 20 shards.

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

`locate` is $O(\log T)$ for a ring of $T$ vnodes total. `add_shard` does `num_vnodes` separate
`list.insert` calls, each $O(T)$ to shift the tail of the list, so $O(\text{num\_vnodes} \cdot T)$
per call; `remove_shard` rebuilds both lists in one linear pass instead, so it costs $O(T)$
regardless of `num_vnodes`. A balanced tree or skip list in place of the plain list would bring
`add_shard` down to $O(\text{num\_vnodes} \log T)$ too. With 12 shards and 150 virtual nodes each,
adding a 13th shard moved 8.1% of the keys `0..19_999`, close to the $1/13 \approx 7.7\%$ an evenly
split ring would move; removing one of the 13 moved 8.4%. *Rendezvous hashing* (each key goes to
the shard with the largest hash of the pair `(key, shard_id)`) meets the same three requirements
without a ring, at $O(N)$ per `locate`.

### Follow-ups

- Part 1's rule does not explicitly minimize how much data moves; it only ever moves a start or an
  end forward. What that costs depends on whether movement is counted in keys or in bytes, which
  diverge when per-key payload sizes vary a lot between shards.
- The processing order decides who yields: among shards with the same start, the shorter ones are
  processed first and the longer ones take the shifts. Processing large or long-lived shards first
  instead breaks the start-only shift, since a later shard's keys at coverage `limit` may then sit
  in the middle of its range.
- The hash ring in Part 2 balances key *count* per shard, not query rate; a shard that is hot
  because of a handful of very popular keys needs separate handling, such as routing those keys
  through a per-key override table or replicating them.
- Adding one new range shard to an already-rebalanced Part 1 output does not need a full re-run:
  only the kept shards whose range intersects the new one can change, plus, if the new shard starts
  past the envelope's end with a hole in between, the kept shard extended to meet it.

<details>
<summary>Checks (runnable)</summary>

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
