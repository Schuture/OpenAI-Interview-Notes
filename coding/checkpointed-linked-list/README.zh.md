# 带检查点的链表

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 | 轮次 |
| --- | --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | linked-list, data-structure, indexing | 3 个部分 / 60 分钟 | 现场面 |
<!-- meta:end -->

## 题目

*向量*（vector，即动态数组，如 C++ 的 `std::vector` 或 Java 的 `ArrayList`）保存一个有序的字符串序列
`a[0], ..., a[n-1]`，共 `n >= 0` 个；`n` 是它的*大小*（size），`a[i]` 中的 `i` 是该元素的*下标*（index）。
实现一个元素存放在*单向链表*（singly linked list）里的向量：每个元素放在一个*结点*（node）中，结点恰有两个字段，
`value`（字符串）和 `next`（指向另一个结点的引用，或 `None`）。向量对象持有 `head`，它是链的两个*端点结点*
（end node）之一，从 `head` 沿 `next` 走下去恰好经过每个结点一次；哪一端作为头由实现决定。元素不得存放在 Python
的 `list` 或其他任何容器里，结点也不得有这两个字段之外的字段。操作如下：

- `add(index, value)`，`0 <= index <= n`：插入 `value`，使它成为 `a[index]`；原来的 `a[index], ..., a[n-1]`
  移到下标 `index+1, ..., n`。其他 `index` 抛出 `IndexError`。
- `get(index)`，`0 <= index < n`：返回 `a[index]`。其他 `index`（包括负数）抛出 `IndexError`。
- `len(v)` 返回 `n`。

### Part 1 —— 普通单向链表

`head` 是存放 `a[0]` 的结点。实现 `LinkedVector`；`add` 和 `get` 可以用 $`O(n)`$ 时间。

```py
class LinkedVector:
    def __init__(self) -> None: ...
    def __len__(self) -> int: ...
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

示例：

```text
v = LinkedVector()
add(0, "pear")    # [pear]
add(1, "fig")     # [pear, fig]
add(1, "plum")    # [pear, plum, fig]
get(1)            # "plum"
add(3, "kiwi")    # [pear, plum, fig, kiwi]
add(0, "lime")    # [lime, pear, plum, fig, kiwi]
get(4)            # "kiwi"
get(5)            # IndexError
add(7, "x")       # IndexError
```

### Part 2 —— 精确的检查点

固定一个正整数 `k`，由构造函数给出（若不是正的 `int`，抛出 `ValueError`）。向量还维护 `checkpoints`，一个由结点
组成的 Python `list`，其中对每个满足 `j*k < n` 的 `j`，`checkpoints[j]` 是存放 `a[j*k]` 的结点。所以
`checkpoints` 有 `ceil(n/k)` 项（`n = 0` 时为空），并且每次调用 `add` 之后都必须成立。实现 `CheckpointVector(k)`，
满足下面的代价界；*链接读取*（link read）指读取一次 `next` 字段。

- `get` 至多做 `k - 1` 次链接读取。
- `add` 至多做 `k + ceil(n/k)` 次链接读取，时间 $`O(n/k + k)`$，除 `checkpoints` 列表外额外空间 $`O(1)`$。
  特别地，不得通过遍历整条链来重建 `checkpoints`。

```py
class CheckpointVector:
    def __init__(self, k: int) -> None: ...
    k: int                  # the spacing
    head: Node              # an end node; None when n = 0
    checkpoints: list       # checkpoints[j] is the node holding a[j*k]
    def __len__(self) -> int: ...
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

`k = 3` 的示例，列出各检查点所存放的值：

```text
add "a", "b", ..., "g" at indices 0, 1, ..., 6    # [a b c d e f g]   checkpoints: a d g   (indices 0 3 6)
add(1, "X")                                       # [a X b c d e f g] checkpoints: a c f
add(8, "h")                                       # [a X b c d e f g h]   checkpoints: a c f
add(9, "i")                                       # [a X b c d e f g h i] checkpoints: a c f i   (index 9 is new)
```

### Part 3 —— 自己选间距

不给出 `k`。实现 `AutoVector()`，它自己选择间距，可通过属性 `k` 读取，并在每次调用之后对当前的 `k` 保持 Part 2
的不变式。每次调用之后，若 `n >= 1`，`k` 是满足 $`\sqrt{n} \le k \le 2\sqrt{n}`$ 的整数。`get` 至多做 `k - 1` 次链接读取，
即 $`O(\sqrt{n})`$；从空向量开始的任意 `m` 次调用，总共做 $`O(m\sqrt{m})`$ 次链接读取，总时间也是这个量级。

```py
class AutoVector:
    def __init__(self) -> None: ...
    k: int                  # the current spacing, chosen by the vector
    def add(self, index: int, value: str) -> None: ...
    def get(self, index: int) -> str: ...
```

示例：对 `i = 0, ..., 9` 依次执行 `add(i, "v" + str(i))`（`n = 10`）之后，`k` 取 `{4, 5, 6}` 中任一个都允许；
`k = 4` 时检查点存放 `v0, v4, v8`。

## 参考解答

<details>
<summary>展开参考解答</summary>

需要确认的点：`index == n` 是合法的 `add`（追加），负下标是错误；哪一端作为头由实现决定，而 Part 2 恰好依赖这个选择。

### Part 1

从头结点出发往后走。在位置 `index-1` 之后插入需要前驱结点，所以提前一个结点停下；只有 `index == 0` 没有前驱。

```python
class Node:
    __slots__ = ("value", "next")

    def __init__(self, value, next=None):
        self.value = value
        self.next = next


class LinkedVector:
    """Part 1: head holds element 0, every operation walks from the head."""

    def __init__(self):
        self._head = None
        self._n = 0

    def __len__(self):
        return self._n

    def _node_at(self, i):
        node = self._head
        for _ in range(i):
            node = node.next
        return node

    def add(self, index, value):
        if not 0 <= index <= self._n:          # NOTE: index == n is allowed (append), index == -1 is not
            raise IndexError(index)
        if index == 0:                         # NOTE: no predecessor: the new node becomes the head
            self._head = Node(value, self._head)
        else:
            prev = self._node_at(index - 1)    # insert AFTER the predecessor, so stop one node early
            prev.next = Node(value, prev.next)
        self._n += 1

    def get(self, index):
        if not 0 <= index < self._n:
            raise IndexError(index)
        return self._node_at(index).value
```

两个操作的代价都是 $`O(n)`$。

### Part 2

**为什么头必须是最后一个元素。** 在 `index = i` 处插入。下标不小于 `i` 的元素都加一，而结点不会移动，所以之后对
`j*k > i`，应当成为 `checkpoints[j]` 的结点，是插入前存放 `a[j*k - 1]` 的结点，也就是旧检查点在下标顺序中的*前驱*。
如果 `next` 通向更大的下标（头存放 `a[0]`），结点就没有办法走到它的前驱；找到前驱要对每个检查点走最多 `k` 条链接，
总共 $`O(n)`$；而把检查点前面的结点存下来，只是把问题往前推了一个结点。让头存放 `a[n-1]`，并让存放 `a[m]` 的结点的
`next` 指向存放 `a[m-1]` 的结点，那么下标顺序中的前驱就是 `next`，之后的每个检查点只需读取一次链接就能移动。

**不变式。** 链为 `head = node(a[n-1]) -> node(a[n-2]) -> ... -> node(a[0]) -> None`，且
`checkpoints[j] = node(a[j*k])`。

**`add(i, v)`，`i < n`。** 令 `anchor = node(a[i])`，`b` 为插入之后的序列：
`m < i` 时 `b[m] = a[m]`，`b[i] = v`，`m > i` 时 `b[m] = a[m-1]`。

1. 在 `anchor` 之后链入新结点：`new.next = anchor.next`，`anchor.next = new`。这时链为
   `node(a[n-1]) -> ... -> anchor -> new -> node(a[i-1]) -> ...`，正是 `b` 的链（`anchor` 存放 `b[i+1]`，`new` 存放
   `b[i]`），而存放 `b[n] = a[n-1]` 的 `head` 不变。
2. `j*k < i` 的检查点不变，因为 `b[j*k] = a[j*k]` 是同一个结点。
3. `j*k = i` 的检查点原来是 `anchor`；`b[i]` 是 `new = anchor.next`。
4. `i < j*k <= n-1` 的检查点原来是 `node(a[j*k])`，它不是 `anchor`；`b[j*k] = a[j*k-1]` 是它所链接的那个结点，
   而第 1 步没有改变这条链接。所以第 3、4 步是同一句话：**第 1 步之后，对每个 `j >= ceil(i/k)`，
   `checkpoints[j] = checkpoints[j].next`**。
5. 若 `n` 是 `k` 的倍数，则 `b` 多出下标 `n = (n/k)*k`，而 `b[n] = a[n-1]` 是旧的头；把它追加进去。

`add(n, v)` 是新建一个头，没有任何下标变化，再加上第 5 步（此时 `b[n] = v`）。

**`get(i)`。** 在 `i` 处或其上方最近的检查点是 `j = ceil(i/k)`，存放 `a[j*k]`，而链是从大下标通向小下标的，所以走
`j*k - i <= k-1` 条链接。若 `j*k > n-1`，就没有这样的检查点；头存放 `a[n-1]`，走 `n-1-i < j*k - i <= k-1` 条链接就够。

**`add` 的代价。** 到达 `anchor` 至多 `k-1` 条链接，读 `anchor.next` 一条，每个被移动的检查点一条，至多
`ceil(n/k)` 条：时间 $`O(n/k + k)`$。除 `checkpoints` 列表外，只保存常数个引用。

```python
class CheckpointVector:
    """Part 2: head holds the LAST element; node(a[m]).next is node(a[m-1]);
    checkpoints[j] is the node holding a[j*k]."""

    def __init__(self, k):
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k must be a positive int")
        self.k = k
        self.head = None
        self.checkpoints = []
        self._n = 0

    def __len__(self):
        return self._n

    def _walk(self, node, steps):
        for _ in range(steps):
            node = node.next
        return node

    def _node_at(self, i):
        j = -(-i // self.k)                    # ceil(i / k): the nearest checkpoint at or ABOVE i
        if j < len(self.checkpoints):
            return self._walk(self.checkpoints[j], j * self.k - i)
        # NOTE: past the last checkpoint: start from the head, which holds a[n-1]
        return self._walk(self.head, self._n - 1 - i)

    def get(self, index):
        if not 0 <= index < self._n:
            raise IndexError(index)
        return self._node_at(index).value

    def add(self, index, value):
        n, k = self._n, self.k
        if not 0 <= index <= n:
            raise IndexError(index)
        old_head = self.head
        if index == n:                         # append: a new head, no index changes
            new = self.head = Node(value, old_head)
        else:
            anchor = self._node_at(index)      # holds a[index]; it will sit just above the new node
            new = Node(value, anchor.next)
            anchor.next = new                  # NOTE: relink BEFORE shifting: for the checkpoint at
            #                                    index itself, anchor.next must already be `new`
            for j in range(-(-index // k), len(self.checkpoints)):
                self.checkpoints[j] = self.checkpoints[j].next    # one step toward smaller indices
        if n % k == 0:                         # index n is now occupied and is a multiple of k
            # NOTE: for index < n that node is the OLD head (a[n-1] moved up by one), not `new`
            self.checkpoints.append(new if index == n else old_head)
        self._n = n + 1
```

### Part 3

`k` 固定时，`n/k + k` 在 `k = sqrt(n)` 处最小，为 `2 sqrt(n)`，所以 `k` 要跟着 `n` 走。让 `k` 保持为 2 的幂，且
`n <= k*k`：在会破坏它的 `add`（`n == k*k`）之前，把 `k` 加倍，并从存放 `a[n-1]` 的头一路走到 `a[0]`，一次遍历重建
`checkpoints`。

- 每次调用之后 `n <= k*k` 都成立，所以 `k >= sqrt(n)`。刚加倍之后 `n = (k/2)^2`，且 `n` 只增不减，所以（`n >= 1`）
  `k/2 <= sqrt(n)` 一直成立：`k <= 2 sqrt(n)`。
- 不重建的调用至多做 `k - 1 + 1 + ceil(n/k) <= 3 sqrt(n) + 1` 次链接读取（Part 2），`get` 至多 `2 sqrt(n)` 次。
- 重建发生在 `n = 1, 4, 16, ..., 4^t`，每次做 `n` 次链接读取。`m` 次调用中，总和小于
  `1 + 4 + ... + 4^t < 4m/3`（因为 `4^t < m`）。合计：$`O(m\sqrt{m})`$。

```python
class AutoVector(CheckpointVector):
    """Part 3: the spacing k is a power of two with n <= k*k, doubled when n reaches k*k."""

    def __init__(self):
        super().__init__(1)

    def _rebuild(self):
        n, k = self._n, self.k
        checkpoints = [None] * -(-n // k)
        node, index = self.head, n - 1         # the head holds a[n-1]; walk down to a[0]
        while node is not None:
            if index % k == 0:
                checkpoints[index // k] = node
            node, index = node.next, index - 1
        self.checkpoints = checkpoints

    def add(self, index, value):
        if self._n == self.k * self.k:
            self.k *= 2                        # NOTE: double BEFORE the add so that n + 1 <= k*k afterwards
            self._rebuild()                    # O(n) once per doubling: amortised O(1) per add
        super().add(index, value)
```

### 追问

- 在同样的精确不变式下实现 `remove(index)`，要把之后的每个检查点移到存放下一个更大下标的结点；在这个朝向下，那是
  *指向*检查点的结点，单向链够不到它；而头存放 `a[0]` 时，`add` 面临镜像的问题。要两个操作同时做到，每个结点需要
  一条回链：双向链表让之后的每个检查点在两个方向上都只读一次链接就能移动，同样是 $`O(n/k + k)`$。
- 放宽的设计（展开链表，unrolled linked list）：一条由块组成的链，每块是至多 `k` 个字符串的数组，再加一棵记录各块大小的
  树状数组（Fenwick tree）。`get(i)` 用前缀和在 $`O(\log(n/k))`$ 内找到块并读取槽位；`add` 在一个块内移动，用
  $`O(k)`$，更新树用 $`O(\log(n/k))`$，块超过 `k` 时分裂成两半，重建树用 $`O(n/k)`$，但对同一个块至多每 `k/2`
  次插入才发生一次；`remove` 对称地合并块。
- 加倍重建是一次代价 $`O(n)`$ 的调用；若在旧的 `checkpoints` 继续使用的同时，每次调用构建新列表的几项，
  可以把每次调用的最坏情况降到 $`O(\sqrt{n})`$。
- `n` 个结点之外的空间是 `ceil(n/k)` 个引用，Part 3 中约为 $`\sqrt{n}`$；`k` 取得更大，就用 `get` 和 `add` 的时间换更少的内存，
  `k >= n` 时 `checkpoints` 只有一项。

<details>
<summary>验证代码（可运行）</summary>

```python
import math
import random


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


# Count every read of a `next` link, so that the link bounds in the statement can be asserted.
LINKS = [0]
_next_slot = Node.next


class CountingNode(Node):
    __slots__ = ()

    @property
    def next(self):
        LINKS[0] += 1
        return _next_slot.__get__(self)

    @next.setter
    def next(self, other):
        _next_slot.__set__(self, other)


RealNode, Node = Node, CountingNode


def chain(v):
    """All nodes from the head, followed through `next`."""
    out, node = [], v.head
    while node is not None:
        out.append(node)
        node = node.next
    return out


def check_state(v, model, k):
    """Independent check of the statement: size, contents, and checkpoints[j] holds index j*k."""
    n = len(model)
    nodes = chain(v)
    assert len(v) == n == len(nodes)
    assert len(v.checkpoints) == -(-n // k)
    values = [x.value for x in nodes]
    # the head is one of the two end nodes, so the chain reads the sequence in one of two directions
    if values == model and all(v.checkpoints[j] is nodes[j * k] for j in range(len(v.checkpoints))):
        return
    assert values == model[::-1], (values, model)
    assert all(v.checkpoints[j] is nodes[n - 1 - j * k] for j in range(len(v.checkpoints)))


def cp_values(v):
    return [x.value for x in v.checkpoints]


# --- Part 1: the example in the statement ---
v = LinkedVector()
v.add(0, "pear")
v.add(1, "fig")
v.add(1, "plum")
assert [v.get(i) for i in range(3)] == ["pear", "plum", "fig"]
v.add(3, "kiwi")
v.add(0, "lime")
assert [v.get(i) for i in range(5)] == ["lime", "pear", "plum", "fig", "kiwi"] and len(v) == 5
expect(IndexError, v.get, 5)
expect(IndexError, v.get, -1)
expect(IndexError, v.add, 6, "x")
expect(IndexError, v.add, -1, "x")

rng = random.Random(2024)
for _ in range(200):
    v, model = LinkedVector(), []
    for _ in range(rng.randint(0, 40)):
        index = rng.randint(0, len(model))
        word = rng.choice("abcdef")
        v.add(index, word)
        model.insert(index, word)
        assert [v.get(i) for i in range(len(model))] == model and len(v) == len(model)

# --- Part 2: the example in the statement ---
v = CheckpointVector(3)
for i, ch in enumerate("abcdefg"):
    v.add(i, ch)
assert cp_values(v) == ["a", "d", "g"]
v.add(1, "X")                                  # a X b c d e f g
assert cp_values(v) == ["a", "c", "f"]
v.add(8, "h")                                  # n = 9
assert cp_values(v) == ["a", "c", "f"]
v.add(9, "i")                                  # n = 10, index 9 is a multiple of 3
assert cp_values(v) == ["a", "c", "f", "i"]
assert "".join(v.get(i) for i in range(10)) == "aXbcdefghi"
expect(ValueError, CheckpointVector, 0)
expect(ValueError, CheckpointVector, -3)
expect(ValueError, CheckpointVector, 2.0)
expect(IndexError, v.add, 11, "x")
expect(IndexError, v.get, 10)
check_state(v, list("aXbcdefghi"), 3)


# --- Part 2: random operations against a Python list, with the link bounds ---
def exercise(make, steps, rng, bounds):
    v, model = make(), []
    for _ in range(steps):
        n = len(model)
        r = rng.random()
        if r < 0.65:
            index = rng.choice([0, n, rng.randint(0, n), rng.randint(0, n)])
            word = "w%d" % rng.randrange(8)          # repeated values on purpose
            k, before = v.k, LINKS[0]
            v.add(index, word)
            assert LINKS[0] - before <= bounds(n, k), (n, k, index)
            model.insert(index, word)
        elif r < 0.9 and n:
            index = rng.randrange(n)
            k, before = v.k, LINKS[0]
            assert v.get(index) == model[index]
            assert LINKS[0] - before <= k - 1
        else:
            expect(IndexError, v.add, rng.choice([-1, n + 1, n + 5]), "bad")
            expect(IndexError, v.get, rng.choice([-1, n, n + 3]))
        yield v, model


rng = random.Random(7)
ops = 0
for k in (1, 2, 3, 4, 5, 7, 8, 16):
    for _ in range(25):
        for v, model in exercise(lambda: CheckpointVector(k), rng.randint(1, 160), rng,
                                 lambda n, k: k + -(-n // k)):
            check_state(v, model, k)
            ops += 1
print("part 2 states checked:", ops)

# --- Part 3: the example in the statement ---
v = AutoVector()
for i in range(10):
    v.add(i, "v%d" % i)
assert 10 <= v.k * v.k <= 4 * 10 and v.k == 4
assert cp_values(v) == ["v0", "v4", "v8"]
check_state(v, ["v%d" % i for i in range(10)], v.k)


# --- Part 3: random operations; size bounds on k after every call, amortised link count ---
def part3_bounds(n, k):
    return 2 * k + -(-n // k) + n      # a call that doubles k also follows n links to rebuild


rng = random.Random(11)
for _ in range(60):
    for v, model in exercise(AutoVector, rng.randint(1, 300), rng, part3_bounds):
        n = len(model)
        if n:
            assert n <= v.k * v.k <= 4 * n and v.k & (v.k - 1) == 0, (n, v.k)
        check_state(v, model, v.k)

m = 3000
v, total = AutoVector(), 0
rebuilds = []
original_rebuild = v._rebuild
v._rebuild = lambda: (rebuilds.append(len(v)), original_rebuild())
for i in range(m):
    before = LINKS[0]
    v.add(rng.randint(0, i), "x")
    assert v.get(rng.randrange(i + 1)) == "x"
    total += LINKS[0] - before
assert rebuilds == [1, 4, 16, 64, 256, 1024], rebuilds
assert total <= 4 * m * math.isqrt(m), total
print("part 3 links for", m, "adds and gets:", total, "<=", 4 * m * math.isqrt(m))

Node = RealNode
print("all checks passed")
```

</details>

</details>
