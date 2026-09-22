# 内存分配器

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★★☆ | 困难 | SWE · MLE · RE | data-structure, intervals, balanced-bst | 75 分钟 |
<!-- meta:end -->

## 题目

一个容量为 `capacity` 字节的地址空间，是整数区间 `[0, capacity)`；其中每个地址在任意时刻要么已分配，要么空闲。
*块*（block）是一段极大的连续地址区间，整体已分配或整体空闲。由于 `free` 总会把新释放的块与相邻的空闲块合并，
两个空闲块永远不会彼此相邻。用 Python 完成下面两个部分，只使用标准库。

### Part 1 —— 首次适配，线性扫描

```py
class MemoryAllocator:
    def __init__(self, capacity: int) -> None: ...
    def allocate(self, size: int) -> int: ...
    def free(self, address: int, size: int) -> None: ...
```

`__init__(capacity)` 一开始整个地址空间都是空闲的。若 `capacity <= 0`，抛出 `ValueError`。

`allocate(size)` 创建一个大小为 `size` 字节的新分配块，按*首次适配*（first fit）放置：在所有大小不小于 `size`
的空闲块中，取起始地址最低的那一个，从它的低端截取 `size` 字节——如果该空闲块比 `size` 大，剩余部分继续保持
空闲，起始地址变为 `address + size`——并返回新块的起始地址。若 `size <= 0`，抛出 `ValueError`；若不存在大小
不小于 `size` 的空闲块，抛出 `MemoryError`。

`free(address, size)` 释放起始地址为 `address` 的块；`size` 必须等于当初 `allocate` 调用返回 `address` 时传入
的那个值。释放后的字节变为空闲，并与左侧、右侧或两侧相邻的空闲块合并。若 `size <= 0`，或者 `(address, size)`
与当前某个已分配块不匹配，抛出 `ValueError`——这一个条件同时覆盖了三种情况：`address` 从未被 `allocate` 返回
过、同一个地址被释放了两次、`size` 与记录的分配大小不一致。

例子，`capacity = 25`：

```text
allocate(5) -> 0, allocate(5) -> 5, allocate(5) -> 10, allocate(5) -> 15, allocate(5) -> 20   (地址空间全部分配)

free(5, 5)    # 两侧邻居都已分配                        -> 空闲：[5, 10)
free(10, 5)   # [5, 10) 在地址 10 处相邻                 -> 空闲：[5, 15)
free(20, 5)   # 两侧都没有空闲邻居                       -> 空闲：[5, 15), [20, 25)
free(15, 5)   # 左边与 [5, 15) 相邻，右边与 [20, 25) 相邻  -> 空闲：[5, 25)
free(0, 5)    # 右边与 [5, 25) 相邻                      -> 空闲：[0, 25)
```

### Part 2 —— O(log n) 的分配与释放

实现 `MemoryAllocatorLog`，构造函数与另外两个方法都与上面的 `MemoryAllocator` 相同，对任意输入返回相同的值、
抛出相同的错误——但 `allocate` 和 `free` 都要在 $O(\log n)$ 时间内完成，其中 $n$ 是当前跟踪的空闲块数量。

```py
class MemoryAllocatorLog:
    def __init__(self, capacity: int) -> None: ...
    def allocate(self, size: int) -> int: ...
    def free(self, address: int, size: int) -> None: ...
```

区分首次适配与只看大小的放置规则的例子：`capacity = 30`；依次调用
`allocate(12), allocate(3), allocate(6), allocate(9)`，返回 `0, 12, 15, 21`；接着 `free(0, 12)` 和
`free(15, 6)` 都没有合并任何邻居，因为它们的邻居（地址 12 和地址 21 处的块）仍然处于已分配状态，留下两个空闲块
`[0, 12)` 和 `[15, 21)`。`allocate(5)` 必须返回 `0`，即更低的地址，即便 `[15, 21)` 对大小为 5 的请求来说是
更贴合的块。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前值得向面试官确认：`free` 是否会拿到 size（本文按此假设，另一种做法放在追问里），以及加速之后是否仍须
保持首次适配——Part 2 全程按此假设。

### Part 1

把空闲块存进一个按起始地址排序的普通列表。`allocate` 从左到右扫描，遇到第一个大小足够的块就停下——按构造方式，
这就是首次适配。`free` 找到第一个起始地址不小于 `address` 的块的下标 `i`；下标 `i - 1` 处的块是唯一可能的左
邻居，下标 `i` 处的块是唯一可能的右邻居，四种合并情形由此直接得到。`allocated` 这个映射只用于校验：释放
`(address, size)` 合法当且仅当 `address` 是 `allocated` 的键且其值等于 `size`，这一个条件恰好就是要拒绝的
三种情况。

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

两个操作耗时都是 $O(n)$，$n$ 为空闲块数量：扫描本身如此；而且因为块存在普通列表里，`list.insert` 和
`list.remove` 都要移动后面的所有元素。

### Part 2

加速 `free` 是简单的一半：把每个空闲块存进一棵按起始地址排序的树，它能在 $O(\log n)$ 内回答某个键的“前驱”和
“后继”，Part 1 的四种合并情形就变成恰好一次前驱查询和一次后继查询。

`allocate` 则要仔细选“用哪棵树”。*最佳适配*（best fit）——返回仍然 `>= size` 的最小空闲块——可以归结为在一棵
按*大小*排序的树上做前驱查询，但必须是真正的平衡树，而不是普通的 Python 列表：`bisect.bisect_left` 能在
$O(\log n)$ 内找到插入位置，但 `list.insert` 在那个位置插入仍然要移动后面的所有元素，不管位置是怎么找到的，
都是 $O(n)$。*首次适配*问的是按大小排序的树回答不了的问题：起始地址**最低**、且大小 `>= size` 的那个块——这
同时涉及地址和大小两种顺序，而按大小排序的树早已丢掉了地址信息。

一棵树可以同时承担两个角色：按起始地址排序（这样合并查询仍是 $O(\log n)$），并在每个节点上额外维护*自身子树
内的最大块大小*。首次适配查询从根开始向下走：如果左子树的最大值 `>= size`，答案就在左子树里，因为左子树里的
地址都比当前节点小；否则，如果当前节点本身足够大，它就是答案，因为它是目前为止遇到的最小地址；否则答案（如果
存在）在右子树里——每一步都排除掉一整棵子树，查询代价是 $O(h)$，$h$ 为树高。下面的代码是一棵*树堆*（treap）：
一棵按地址排序的二叉搜索树，通过给每个节点一个独立的随机优先级、并借助 `split`/`merge` 这对操作维护优先级上
的大根堆性质，使树在期望意义下保持平衡；插入、删除，以及重新计算最大值这个附加信息，因此也都是期望 $O(\log n)$。

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

一个刻意构造的优先级序列可能让这棵树堆失衡——这是任何随机化平衡树都有的老问题——换成确定性的 AVL 树或红黑树
可以消除这一点，代价是更多的簿记开销。

### 追问

- **对齐。** 要让地址都是某个 `a`（如 8）的倍数，截取块之前把 `size` 向上取整到 `a` 的倍数，后面那个块也就从
  对齐地址开始。
- **Realloc。** 原地扩大只有在后面紧跟足够大的空闲块时才行得通；否则内容必须拷贝到 `allocate` 给出的新块，
  调用者看到的是一个新地址。
- **线程安全。** 给整个分配器加一把锁最简单也最正确；按大小分类拆成多把锁则需要加锁顺序，因为一次 `free`
  可能碰到另一个分类管理的邻居块。
- **外部碎片。** 分级空闲链表把每个请求导向大小相近的一组块；*伙伴系统*（buddy system）让每个块的大小都是
  2 的幂，释放的块的“伙伴”只需翻转地址的某一位就能找到，合并因此是 $O(1)$，代价是每个请求都要向上取整。
- **不传 size 的 free。** 必须在分配时记下大小——本文里是 `allocated` 映射，真实分配器里通常是返回地址之前的
  一小段头部——否则没有东西能告诉 `free(address)` 该释放多少字节。

<details>
<summary>验证代码（可运行）</summary>

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
