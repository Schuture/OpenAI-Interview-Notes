# Memory Allocator

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding | ★★★★☆ | Hard | SWE · MLE · RE | data-structure, intervals, balanced-bst | 75 min |
<!-- meta:end -->

## Problem

An address space of `capacity` bytes is the integer range `[0, capacity)`; every address in it is, at
any moment, either allocated or free. A *block* is a maximal contiguous range of addresses that is
entirely allocated or entirely free. Because `free` always merges a newly released block with a
touching free block, two free blocks are never adjacent to each other. Implement the following
two parts in Python, using only the standard library.

### Part 1 — First fit, linear scan

```py
class MemoryAllocator:
    def __init__(self, capacity: int) -> None: ...
    def allocate(self, size: int) -> int: ...
    def free(self, address: int, size: int) -> None: ...
```

`__init__(capacity)` starts with the whole address space free. Raises `ValueError` if `capacity <= 0`.

`allocate(size)` creates a new allocated block of `size` bytes, placed by *first fit*: among the free
blocks of size at least `size`, it uses the one with the lowest start address, taking `size` bytes from
its low end — if that free block is larger than `size`, the remaining bytes stay free, now starting at
`address + size` — and returns the new block's start address. Raises `ValueError` if `size <= 0`, and
`MemoryError` if no free block of size at least `size` exists.

`free(address, size)` releases the block that starts at `address`; `size` must equal the value passed to
the `allocate` call that returned `address`. The released bytes become free and merge with a touching
free block on the left, on the right, or both. Raises `ValueError` if `size <= 0`, or if `(address,
size)` does not match a block that is currently allocated — one condition that covers an address
`allocate` never returned, a second free of the same address, and a `size` that does not match the
recorded allocation.

Example, `capacity = 25`:

```text
allocate(5) -> 0, allocate(5) -> 5, allocate(5) -> 10, allocate(5) -> 15, allocate(5) -> 20   (fully allocated)

free(5, 5)    # both neighbours allocated                            -> free: [5, 10)
free(10, 5)   # [5, 10) touches at address 10                        -> free: [5, 15)
free(20, 5)   # no neighbour on either side is free                  -> free: [5, 15), [20, 25)
free(15, 5)   # touches [5, 15) on the left AND [20, 25) on the right -> free: [5, 25)
free(0, 5)    # touches [5, 25) on the right                         -> free: [0, 25)
```

### Part 2 — O(log n) allocation and release

Implement `MemoryAllocatorLog`, with the same constructor and the same two methods as `MemoryAllocator`
above, returning the same values and raising the same errors for every input — but with `allocate` and
`free` both running in $O(\log n)$, where $n$ is the number of free blocks currently tracked.

```py
class MemoryAllocatorLog:
    def __init__(self, capacity: int) -> None: ...
    def allocate(self, size: int) -> int: ...
    def free(self, address: int, size: int) -> None: ...
```

Example distinguishing first fit from a placement rule that only looks at size: `capacity = 30`; four
calls `allocate(12), allocate(3), allocate(6), allocate(9)` return `0, 12, 15, 21`; then `free(0, 12)`
and `free(15, 6)` each merge with nothing, since their neighbours (at address 12 and address 21) are
still allocated, leaving two free blocks, `[0, 12)` and `[15, 21)`. `allocate(5)` must return `0`, the
lower address, even though `[15, 21)` is the tighter fit for a request of size 5.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming with the interviewer before coding: whether `free` gets the size back (assumed here,
with the alternative in the follow-ups) and whether placement must stay first fit once sped up, which
Part 2 assumes throughout.

### Part 1

Keep the free blocks in a plain list sorted by start address. `allocate` scans left to right and stops
at the first block of sufficient size — first fit, by construction. `free` finds the index `i` of the
first block starting at or after `address`; block `i - 1` is the only possible left neighbour and block
`i` the only possible right neighbour, which gives the four merge cases directly. The `allocated` map
is for validation only: freeing `(address, size)` is legal exactly when `address` is a key of `allocated`
with value `size`, which is the three rejected conditions in one check.

```python
class MemoryAllocator:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.gaps = [[0, capacity]]        # NOTE: not self.free -- would shadow the free() method below
        self.allocated = {}                # address -> size, for validating free()

    def allocate(self, size):
        if size <= 0:
            raise ValueError("size must be positive")
        for gap in self.gaps:              # NOTE: linear scan; the first block with enough room wins
            if gap[1] >= size:
                start = gap[0]
                if gap[1] == size:
                    self.gaps.remove(gap)
                else:
                    gap[0] += size
                    gap[1] -= size
                self.allocated[start] = size
                return start
        raise MemoryError(f"no free block of size >= {size}")

    def free(self, address, size):
        if size <= 0 or self.allocated.get(address) != size:
            raise ValueError(f"invalid free({address}, {size})")
        del self.allocated[address]
        i = 0
        while i < len(self.gaps) and self.gaps[i][0] < address:
            i += 1
        # NOTE: read both flags first -- merging into gaps[i - 1] must not disturb index i below
        merge_left = i > 0 and self.gaps[i - 1][0] + self.gaps[i - 1][1] == address
        merge_right = i < len(self.gaps) and address + size == self.gaps[i][0]
        if merge_left and merge_right:
            self.gaps[i - 1][1] += size + self.gaps[i][1]
            del self.gaps[i]
        elif merge_left:
            self.gaps[i - 1][1] += size
        elif merge_right:
            self.gaps[i][0] = address
            self.gaps[i][1] += size
        else:
            self.gaps.insert(i, [address, size])
```

Both operations cost $O(n)$ time, $n$ the count of free blocks: the scan itself, and — because blocks
live in a plain list — `list.insert` and `list.remove`, which shift every later element.

### Part 2

Speeding up `free` is the easy half: keep every free block in a tree ordered by start address, which
answers "predecessor" and "successor" of a key in $O(\log n)$, and Part 1's four merge cases become
exactly one predecessor lookup and one successor lookup.

`allocate` needs care about *which* tree. *Best fit* (smallest free block that is still `>= size`)
reduces to a predecessor query in a tree ordered by *size* — it must be a real balanced tree, not a
plain Python list: `bisect.bisect_left` finds the position in $O(\log n)$, but `list.insert` there still
shifts every later element, $O(n)$ regardless of how the position was found. *First fit* asks for
something a size-ordered tree cannot answer: the block with the **lowest address** whose size is
`>= size` — two orderings at once, and the size tree has already discarded the address one.

One tree can serve both roles: order it by start address (so merge stays $O(\log n)$), and additionally
store, at every node, the *maximum block size in its own subtree*. The first-fit query walks down from
the root: if the left subtree's maximum is `>= size`, the answer is there, since every address in it is
smaller than the current node's; else the current node is the answer if it is big enough, being the
smallest address reached so far; else the answer is in the right subtree — one discarded subtree per
step, so the query costs $O(h)$, $h$ the tree's height. The code below is a *treap*: a binary search tree
keyed by address, kept balanced in expectation by giving every node an independent random priority and
maintaining a max-heap on it through the `split`/`merge` pair, so insertion, deletion and re-deriving the
max-size augmentation are all $O(\log n)$ in expectation too.

```python
import random


class _Node:
    __slots__ = ("start", "size", "priority", "left", "right", "max_size")

    def __init__(self, start, size):
        self.start, self.size, self.max_size = start, size, size
        self.priority = random.random()        # NOTE: random priorities -> balanced in expectation
        self.left = self.right = None

def _pull(node):                                # recompute the augmentation from the two children
    node.max_size = max(node.size, node.left.max_size if node.left else 0,
                         node.right.max_size if node.right else 0)

def _merge(a, b):                               # every key in a is < every key in b; max-heap on priority
    if a is None or b is None:
        return a or b
    if a.priority > b.priority:
        a.right = _merge(a.right, b)
        _pull(a)
        return a
    b.left = _merge(a, b.left)
    _pull(b)
    return b

def _split(node, key):                          # -> (start <= key, start > key), same relative order
    if node is None:
        return None, None
    if node.start <= key:
        lo, hi = _split(node.right, key)
        node.right = lo
        _pull(node)
        return node, hi
    lo, hi = _split(node.left, key)
    node.left = hi
    _pull(node)
    return lo, node

def _insert(root, start, size):
    lo, hi = _split(root, start)
    return _merge(_merge(lo, _Node(start, size)), hi)

def _delete(root, start):
    lo, hi = _split(root, start)                # lo: start <= key, hi: start > key
    lo2, _mid = _split(lo, start - 1)           # NOTE: unique keys -> isolates exactly one node
    return _merge(lo2, hi)

def _first_fit(node, size):                     # leftmost node with size >= `size`, else None
    if node is None or node.max_size < size:
        return None
    if node.left and node.left.max_size >= size:    # NOTE: left subtree only has smaller addresses
        return _first_fit(node.left, size)
    return node if node.size >= size else _first_fit(node.right, size)

def _neighbours(node, key):                     # (predecessor, successor) of `key`, one walk down
    pred = succ = None
    while node:
        if node.start < key:
            pred, node = node, node.right
        else:
            succ, node = node, node.left
    return pred, succ


class MemoryAllocatorLog:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._free = _Node(0, capacity)         # treap root; None once memory is exhausted
        self.allocated = {}                     # address -> size, for validating free()

    def allocate(self, size):
        if size <= 0:
            raise ValueError("size must be positive")
        node = _first_fit(self._free, size)
        if node is None:
            raise MemoryError(f"no free block of size >= {size}")
        start = node.start
        self._free = _delete(self._free, start)
        if node.size > size:
            self._free = _insert(self._free, start + size, node.size - size)
        self.allocated[start] = size
        return start

    def free(self, address, size):
        if size <= 0 or self.allocated.get(address) != size:
            raise ValueError(f"invalid free({address}, {size})")
        del self.allocated[address]
        pred, succ = _neighbours(self._free, address)
        start, total = address, size
        if pred is not None and pred.start + pred.size == address:
            start, total = pred.start, pred.size + total
            self._free = _delete(self._free, pred.start)
        if succ is not None and address + size == succ.start:
            total += succ.size
            self._free = _delete(self._free, succ.start)
        self._free = _insert(self._free, start, total)
```

An adversarial sequence of priorities could unbalance this treap — the usual caveat for any randomized
balanced tree — which a deterministic AVL or red-black tree would remove at the cost of more bookkeeping.

### Follow-ups

- **Alignment.** To keep every address a multiple of some `a` (e.g. 8), round `size` up to the next
  multiple of `a` before carving the block, so the following block also starts aligned.
- **Realloc.** Growing in place only works when a large-enough free block follows; otherwise the
  contents must be copied into a fresh block from `allocate`, which the caller sees as a new address.
- **Thread safety.** One lock around the whole allocator is the simplest correct option; splitting it by
  size class needs a lock order, since a `free` can touch a neighbour tracked under another class.
- **External fragmentation.** Segregated free lists route each request to a list of same-size blocks;
  the buddy system keeps every block a power of two, so a freed block's buddy is found by flipping one
  address bit, making merging $O(1)$ at the cost of rounding every request up.
- **`free` without a size.** Recording the size at allocation time — the `allocated` map here, or a
  header just before the returned address in a real allocator — is required, or nothing tells
  `free(address)` how many bytes to release.

<details>
<summary>Checks (runnable)</summary>

```python
def free_blocks(impl):
    """(start, size) of every free block, in address order. Works for either implementation."""
    if hasattr(impl, "gaps"):
        return [tuple(g) for g in impl.gaps]
    out = []

    def walk(node):
        if node is None:
            return
        walk(node.left)
        out.append((node.start, node.size))
        walk(node.right)

    walk(impl._free)
    return out


for cls in (MemoryAllocator, MemoryAllocatorLog):
    a = cls(25)
    assert [a.allocate(5) for _ in range(5)] == [0, 5, 10, 15, 20]
    a.free(5, 5)
    assert free_blocks(a) == [(5, 5)]
    a.free(10, 5)
    assert free_blocks(a) == [(5, 10)]
    a.free(20, 5)
    assert free_blocks(a) == [(5, 10), (20, 5)]
    a.free(15, 5)
    assert free_blocks(a) == [(5, 20)]
    a.free(0, 5)
    assert free_blocks(a) == [(0, 25)]

    b = cls(30)
    assert (b.allocate(12), b.allocate(3), b.allocate(6), b.allocate(9)) == (0, 12, 15, 21)
    b.free(0, 12)
    b.free(15, 6)
    assert free_blocks(b) == [(0, 12), (15, 6)]
    assert b.allocate(5) == 0                 # first fit, not the tighter block at 15

    for args in ((0,), (-3,)):
        try:
            cls(*args)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    c = cls(10)
    for method, margs, exc in [("allocate", (0,), ValueError), ("allocate", (-1,), ValueError),
                                ("allocate", (11,), MemoryError)]:
        try:
            getattr(c, method)(*margs)
            raise AssertionError(f"expected {exc}")
        except exc:
            pass
    x = c.allocate(5)
    for margs in [(x, 4), (x, 6)]:             # wrong size
        try:
            c.free(*margs)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    c.free(x, 5)
    try:
        c.free(x, 5)                            # double free
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        c.free(3, 5)                            # never allocated
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

print("worked examples and error paths: OK for both implementations")


class BruteForceAllocator:
    """Byte-array oracle: byte i is 1 if address i is allocated. O(capacity) per call,
    used only to check the two implementations above, never for its own performance."""

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.used = bytearray(capacity)
        self.allocated = {}

    def allocate(self, size):
        if size <= 0:
            raise ValueError("size must be positive")
        run = 0
        for i in range(self.capacity):
            run = run + 1 if self.used[i] == 0 else 0
            if run == size:
                start = i - size + 1
                for j in range(start, start + size):
                    self.used[j] = 1
                self.allocated[start] = size
                return start
        raise MemoryError(f"no free block of size >= {size}")

    def free(self, address, size):
        if size <= 0 or self.allocated.get(address) != size:
            raise ValueError(f"invalid free({address}, {size})")
        del self.allocated[address]
        for j in range(address, address + size):
            self.used[j] = 0

    def gaps(self):
        out, i = [], 0
        while i < self.capacity:
            if self.used[i] == 0:
                j = i
                while j < self.capacity and self.used[j] == 0:
                    j += 1
                out.append((i, j - i))
                i = j
            else:
                i += 1
        return out


def call(impl, method, args):
    try:
        return ("ok", getattr(impl, method)(*args))
    except (ValueError, MemoryError) as e:
        return (type(e).__name__, None)


rng = random.Random(0)
for trial in range(400):
    capacity = rng.randint(1, 40)
    oracle = BruteForceAllocator(capacity)
    fast1 = MemoryAllocator(capacity)
    fast2 = MemoryAllocatorLog(capacity)
    live = []                                  # (address, size) currently allocated, per the oracle

    for _ in range(60):
        if live and rng.random() < 0.55:
            addr, size = rng.choice(live)
            if rng.random() < 0.15 and size > 1:       # occasionally pass the wrong size
                size += rng.choice([-1, 1])
            method, args = "free", (addr, size)
        else:
            size = rng.choice([0, -1]) if rng.random() < 0.05 else rng.randint(1, capacity + 2)
            method, args = "allocate", (size,)

        r0, r1, r2 = call(oracle, method, args), call(fast1, method, args), call(fast2, method, args)
        assert r0 == r1 == r2, (trial, method, args, r0, r1, r2)
        if method == "free" and r0[0] == "ok":
            live.remove((args[0], args[1]))
        elif method == "allocate" and r0[0] == "ok":
            live.append((r0[1], args[0]))

        g0 = oracle.gaps()
        assert g0 == free_blocks(fast1) == free_blocks(fast2)
        assert all(g0[k][0] + g0[k][1] < g0[k + 1][0] for k in range(len(g0) - 1))    # no two touch

print("random cross-check against the byte-array oracle: OK (400 trials x 60 ops)")
```

</details>

</details>
