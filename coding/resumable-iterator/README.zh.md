# 可恢复迭代器（一维、二维到任意深度）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | iterator, oop-design, state | 4 个部分 |
<!-- meta:end -->

## 题目

一个*可恢复迭代器*（resumable iterator）像普通的 Python 迭代器一样逐个产出元素，但还能用 `get_state()` 导出当前的
位置，之后用 `set_state(state)` 从那个位置继续产出，就像从未停止过一样。实现下面四个 Part。

下面每个迭代器遍历的都是嵌套 $d$ 层的数据（普通列表 $d = 1$）：连续取 $d$ 次下标得到的
$\text{items}[i_1][i_2] \cdots [i_d]$ 是一个元素，元素按*下标元组*（index tuple）$(i_1, \ldots, i_d)$ 的字典序产出，
对矩阵来说就是逐行产出。状态就是这样的元组：

- `get_state()` 返回一个由 $d$ 个非负 `int` 组成的 `tuple`，即下一次调用 `__next__` 将要产出的那个元素的下标元组。
  没有剩余元素之后（迭代器已*耗尽*，exhausted），它改为返回 $(\text{len}(\text{items}), 0, \ldots, 0)$。
- 对给定的数据，一个元组称为*规范*（canonical）的，当且仅当它就是上面这个耗尽元组，或者在每一层 $k$ 都满足
  $0 \le i_k < \text{len}(L_k)$，其中 $L_k$ 是用 $i_1, \ldots, i_{k-1}$ 逐层取下标得到的列表（$L_1$ 就是 `items`）。
  规范元组恰好就是 `get_state()` 可能返回的元组。第二个条件排除了指向空列表内部和指向非空列表末尾这两种情况：
  这时位置都应当已经移到了下一个元素上。例如，各行为 `[[5, 7], [2]]` 时，产出 7 之后的位置是 `(1, 0)`，所以
  `(0, 2)` 不是规范的；各行为 `[[], [4]]` 时，`(0, 0)` 不是规范的，因为第 0 行是空的。

`set_state(state)` 按以下顺序检查：如果 `state` 不是元组或列表、长度不是 $d$，或者有元素不是 `int`（`bool` 不算
`int`），抛出 `TypeError`；否则，如果 `state` 对这个迭代器自己的数据不是规范的，抛出 `ValueError`。被拒绝的状态
不改变迭代器的位置。否则，下一次 `__next__` 产出这个元组指向的元素；如果是耗尽元组，则抛出 `StopIteration`。
列表和元组一样被接受，因为状态经过一次 `json.dumps` / `json.loads` 往返之后会变成列表。`set_state` 可以向前跳，
也可以向后跳，在已经抛出过 `StopIteration` 之后也可以。

`set_state` 只拿状态和接收它的迭代器自己的数据比对，所以一个实例导出的状态可以交给另一个实例。如果两份数据的
*形状*（shape）相同，即每一层对应的每个列表长度都相同（元素的值可以不同），迭代会像在原来的实例上一样继续下去。
如果形状不同，只有当这个状态对新数据是规范的时才被接受，之后从它在新数据里指向的元素继续。构造迭代器之后再修改
它底下的列表，不在这份约定之内。

### Part 1 —— 抽象接口

定义 `ResumableIterator`，一个抽象基类，下面每个迭代器都继承自它，把 `__iter__`、`__next__`、`get_state`、
`set_state` 声明为抽象方法，遵循上面的约定。

```py
class ResumableIterator(ABC):
    @abstractmethod
    def __iter__(self) -> "ResumableIterator": ...

    @abstractmethod
    def __next__(self):
        """Returns the next item. Raises StopIteration once none remain."""

    @abstractmethod
    def get_state(self) -> tuple:
        """Returns a copyable, JSON-serializable tuple describing the current position."""

    @abstractmethod
    def set_state(self, state) -> None:
        """Moves to the position state describes. Raises TypeError or ValueError as specified above."""
```

### Part 2 —— 一维列表

`items` 是一个任意长度的普通 Python 列表，可以为空。实现 `ResumableListIterator(items)`；它按顺序产出
`items[0], items[1], ...`。

```py
class ResumableListIterator(ResumableIterator):
    def __init__(self, items: list) -> None:
        """items may be empty."""
```

例子：

```text
items = [68, 71, 74, 70, 73, 69]

next -> 68
next -> 71
next -> 74
state = get_state()      # (3,)
next -> 70
set_state(state)
next -> 70                # 再次产出
next -> 73
next -> 69
next -> StopIteration
```

### Part 3 —— 二维列表（矩阵）

`items` 是一个列表的列表（*行*，row）；任何一行都可以为空，包括第一行、最后一行，或者全部行。实现
`Resumable2DIterator(items)`；它依次产出 `items[0]` 的元素，然后是 `items[1]` 的元素，以此类推，跳过每一个空行。

```py
class Resumable2DIterator(ResumableIterator):
    def __init__(self, items: list) -> None:
        """items is a list of lists; a row may be empty."""
```

例子：

```text
items = [[7, 2], [], [9], [], [3, 5, 1]]

next -> 7
next -> 2
state = get_state()      # (2, 0)：已经越过空的第 1 行，指向第 2 行的 9
next -> 9
set_state(state)
next -> 9                 # 再次产出
next -> 3
next -> 5
next -> 1
next -> StopIteration
get_state()               # (5, 0)：已耗尽
```

`Resumable2DIterator([[], []])` 什么也不产出；它的 `get_state()` 从一开始就是 `(2, 0)`。

### Part 4 —— 任意深度的嵌套列表

`items` 嵌套了 `depth` 层（$\text{depth} = d \ge 1$）：连续取 `depth` 次下标得到的就是元素，即使它本身也是一个
列表。任何一层的列表都可以为空。实现 `ResumableNestedIterator(items, depth)`；`depth=1` 或 `depth=2` 时，它的行为
与 Part 2 或 Part 3 的迭代器完全相同。

```py
class ResumableNestedIterator(ResumableIterator):
    def __init__(self, items: list, depth: int) -> None:
        """items is nested depth levels deep, depth >= 1; a list at any level may be empty."""
```

`depth=3` 的例子：

```text
items = [
    [[5, 3], []],
    [],
    [[], [9, 1]],
    [[6]],
]

next -> 5
next -> 3
state = get_state()      # (2, 1, 0)：跳过了 items[0][1]、items[1] 和 items[2][0]，它们都是空的
next -> 9
set_state(state)
next -> 9                 # 再次产出
next -> 1
next -> 6
next -> StopIteration
```

## 参考解答

<details>
<summary>展开参考解答</summary>

动手写代码之前，先为容易出错的位置写测试：紧挨在一串空列表之前保存、耗尽之后保存、经过一次 JSON 往返的状态，
以及 `get_state` 永远不会返回的元组。

### Part 1

基类本身不含逻辑，只承载约定；类型检查由三个迭代器共用。

```python
from abc import ABC, abstractmethod


class ResumableIterator(ABC):
    @abstractmethod
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self):
        ...

    @abstractmethod
    def get_state(self):
        ...

    @abstractmethod
    def set_state(self, state) -> None:
        ...


def _check_index_tuple(state, length):
    # NOTE: bool is a subclass of int, so isinstance(True, int) is True
    if (not isinstance(state, (tuple, list)) or len(state) != length
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in state)):
        raise TypeError(f"expected a {length}-tuple of ints, got {state!r}")
    return tuple(state)          # NOTE: a state that went through JSON arrives as a list
```

### Part 2

一个下标，每次调用后加一；`len(items)` 就是耗尽状态。

```python
class ResumableListIterator(ResumableIterator):
    def __init__(self, items):
        self.items = items
        self._pos = 0                                 # index of the next element to produce

    def __iter__(self):
        return self

    def __next__(self):
        pos = self._pos
        if pos == len(self.items):                    # the exhausted state; set_state never goes past it
            raise StopIteration
        self._pos = pos + 1
        return self.items[pos]

    def get_state(self):
        return (self._pos,)

    def set_state(self, state):
        (pos,) = _check_index_tuple(state, 1)
        if not 0 <= pos <= len(self.items):          # NOTE: '<=': pos == len(items) is exhausted
            raise ValueError(f"{state!r} is not a canonical position")
        self._pos = pos
```

### Part 3

两个下标，`_outer` 和 `_inner`。`_skip_empty` 在构造时和每次 `__next__` 之后都会运行，所以这对下标始终是
规范的，`get_state` 直接读出来即可。如果改成在 `__next__` 开头才跳过空行，Part 3 的例子里产出 2 之后
留下的就是 `(0, 2)`，而这正是 `set_state` 必须拒绝的状态。

```python
class Resumable2DIterator(ResumableIterator):
    def __init__(self, items):
        self.items = items
        self._outer = 0
        self._inner = 0
        self._skip_empty()

    def _skip_empty(self):
        while self._outer < len(self.items) and self._inner >= len(self.items[self._outer]):
            self._outer += 1
            self._inner = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._outer >= len(self.items):
            raise StopIteration
        item = self.items[self._outer][self._inner]
        self._inner += 1
        self._skip_empty()              # NOTE: right away, not before producing the next item
        return item

    def get_state(self):
        return (self._outer, self._inner)

    def set_state(self, state):
        outer, inner = _check_index_tuple(state, 2)
        exhausted = (outer, inner) == (len(self.items), 0)
        inside = 0 <= outer < len(self.items) and 0 <= inner < len(self.items[outer])
        if not (exhausted or inside):   # NOTE: strict '<': inner == len(row) is not canonical
            raise ValueError(f"{state!r} is not a canonical position")
        self._outer, self._inner = outer, inner
```

### Part 4

Part 3 的做法可以推广成一叠 `(container, index)` 帧（frame），每层一帧；栈空表示已耗尽。`_advance` 靠*数层数*
（`len(self._stack) < self.depth`）决定是否继续往下探，而不是用 `isinstance(x, list)` 判断：`depth=1` 时，
`[[], [], []]` 是三个恰好为空列表的元素，`isinstance` 判断会把它们都当成空分支跳过。

```python
class ResumableNestedIterator(ResumableIterator):
    def __init__(self, items, depth):
        self.items = items
        self.depth = depth
        self._stack = [(items, 0)]
        self._advance()

    def _advance(self):
        while self._stack:
            container, idx = self._stack[-1]
            if idx >= len(container):
                self._stack.pop()
                if self._stack:
                    parent, pidx = self._stack[-1]
                    self._stack[-1] = (parent, pidx + 1)
                continue
            if len(self._stack) < self.depth:
                self._stack.append((container[idx], 0))
            else:
                return                   # top of stack points at the next item

    def __iter__(self):
        return self

    def __next__(self):
        if not self._stack:
            raise StopIteration
        container, idx = self._stack[-1]
        item = container[idx]
        self._stack[-1] = (container, idx + 1)
        self._advance()
        return item

    def _exhausted_state(self):
        return (len(self.items),) + (0,) * (self.depth - 1)

    def get_state(self):
        if not self._stack:              # NOTE: the empty stack alone would give (), not a d-tuple
            return self._exhausted_state()
        return tuple(idx for _, idx in self._stack)

    def set_state(self, state):
        indices = _check_index_tuple(state, self.depth)
        if indices == self._exhausted_state():
            self._stack = []
            return
        stack, container = [], self.items
        for idx in indices:
            if not 0 <= idx < len(container):    # NOTE: the same strict '<' at every level
                raise ValueError(f"{state!r} is not a canonical position")
            stack.append((container, idx))
            container = container[idx]
        self._stack = stack
```

完整走一遍的总工作量是 $O(N + M)$，其中 $N$ 是元素个数，$M$ 是各层列表的总数，因为 `_advance` 对每个列表只压栈、
出栈各一次；但需要跳过一长串空列表时，单次 `__next__` 仍可能花 $O(M)$。`get_state` 和 `set_state` 的代价是
$O(\text{depth})$，迭代器额外保存的状态也只有 $O(\text{depth})$，与元素多少无关。先展平成一个列表再复用 Part 2
更简单，但要多占 $O(N)$ 内存，而且它的状态是展平后的单个位置，不是约定要求的下标元组。

### 追问

- 改成逐行遍历一个文件：状态是 `f.tell()` 给出的字节偏移，`set_state` 重新打开文件并 seek 到那里，文件句柄本身
  不进入状态。文件要用二进制模式打开：文本模式下，`next(f)` 之后调用 `f.tell()` 会抛出
  `OSError: telling position disabled by next() call`。
- 如果要拒绝在形状不同的数据上保存的状态，可以在构造时算出形状的指纹（例如对每个列表的长度求哈希），放进
  状态里，在 `set_state` 里比对。
- 生成器对象既不能复制，也不能 pickle（`TypeError: cannot pickle 'generator' object`），所以用普通生成器写的遍历
  只能重新运行、丢掉此前已经产出的所有元素来恢复。
- 这几个类只用到 `len()` 和下标访问，所以元组和 NumPy 数组原样可用：产出的元素是 NumPy 标量，状态仍然是普通的
  `int`。

<details>
<summary>验证代码（可运行）</summary>

```python
import copy
import io
import json
import random

import numpy as np


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


# --- the examples in the statement ---
it = ResumableListIterator([68, 71, 74, 70, 73, 69])
assert [next(it), next(it), next(it)] == [68, 71, 74]
s = it.get_state()
assert s == (3,) and next(it) == 70
it.set_state(s)
assert list(it) == [70, 73, 69] and it.get_state() == (6,)

it2 = Resumable2DIterator([[7, 2], [], [9], [], [3, 5, 1]])
assert [next(it2), next(it2)] == [7, 2]
s2 = it2.get_state()
assert s2 == (2, 0) and next(it2) == 9
it2.set_state(s2)
assert list(it2) == [9, 3, 5, 1] and it2.get_state() == (5, 0)
empty_rows = Resumable2DIterator([[], []])
assert empty_rows.get_state() == (2, 0) and list(empty_rows) == []
rows = Resumable2DIterator([[5, 7], [2]])
assert [next(rows), next(rows)] == [5, 7] and rows.get_state() == (1, 0)
expect(ValueError, rows.set_state, (0, 2))
expect(TypeError, rows.set_state, (0, True))
expect(ValueError, Resumable2DIterator([[], [4]]).set_state, (0, 0))

data3 = [[[5, 3], []], [], [[], [9, 1]], [[6]]]
it3 = ResumableNestedIterator(data3, depth=3)
assert [next(it3), next(it3)] == [5, 3]
s3 = it3.get_state()
assert s3 == (2, 1, 0) and next(it3) == 9
it3.set_state(json.loads(json.dumps(s3)))          # a list after the JSON round trip
assert list(it3) == [9, 1, 6] and it3.get_state() == (4, 0, 0)
it3.set_state((4, 0, 0))
expect(StopIteration, next, it3)
# depth counts levels; what an item is does not matter
assert list(ResumableNestedIterator([[], [8], []], depth=1)) == [[], [8], []]


# --- independent oracle, written from the statement: enumerate every index tuple ---
class NaiveIterator:
    def __init__(self, items, d):
        self.items, self.d, self.pos = items, d, 0
        self.paths, self.empty_lists = [], []

        def walk(x, prefix):
            if len(prefix) == d:
                self.paths.append(prefix)
                return
            if len(x) == 0:
                self.empty_lists.append(prefix)
            for i in range(len(x)):
                walk(x[i], prefix + (i,))

        walk(items, ())
        self.end = (len(items),) + (0,) * (d - 1)

    def state(self):
        return self.paths[self.pos] if self.pos < len(self.paths) else self.end

    def next(self):
        if self.pos == len(self.paths):
            raise StopIteration
        x = self.items
        for i in self.paths[self.pos]:
            x = x[i]
        self.pos += 1
        return x

    def seek(self, s):
        if not isinstance(s, (tuple, list)) or len(s) != self.d or any(type(v) is not int for v in s):
            raise TypeError
        if tuple(s) == self.end:
            self.pos = len(self.paths)
        elif tuple(s) in self.paths:
            self.pos = self.paths.index(tuple(s))
        else:
            raise ValueError

    def rest(self):
        return [self.next() for _ in range(len(self.paths) - self.pos)]

    def skipped_empty(self):
        """Whether an empty list lies between the last produced item and the next one."""
        lo = self.paths[self.pos - 1] if self.pos else ()
        return any(lo < e < self.state() for e in self.empty_lists)   # tuples compare in walk order


def gen(rng, d, max_len=3):
    if d == 1:
        return [rng.randint(0, 9) for _ in range(rng.randint(0, max_len))]
    return [[] if rng.random() < 0.35 else gen(rng, d - 1) for _ in range(rng.randint(0, max_len))]


def relabel(x, d):
    return [v + 100 for v in x] if d == 1 else [relabel(sub, d - 1) for sub in x]


def random_state(rng, naive):
    """Mostly near misses: a real position nudged by one, or small ints with the odd bool or float."""
    if rng.random() < 0.3 and naive.paths:
        s = list(rng.choice(naive.paths))
        s[rng.randrange(naive.d)] += rng.choice([-1, 1])
    else:
        s = [rng.choice([-1, True, False, 1.0]) if rng.random() < 0.1 else rng.randint(0, 3)
             for _ in range(naive.d + rng.choice([0, 0, 0, 0, -1, 1]))]
    return tuple(s) if rng.random() < 0.5 else s


def outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except (StopIteration, TypeError, ValueError) as e:
        return (type(e).__name__,)


def makers(d):
    out = [lambda data: ResumableNestedIterator(data, d)]
    if d == 1:
        out.append(ResumableListIterator)
    if d == 2:
        out.append(Resumable2DIterator)
    return out


rng = random.Random(0)
cov = dict(skip_saves=0, end_saves=0, TypeError=0, ValueError=0, ok=0, other_shape_ok=0, other_shape_bad=0)
for d in (1, 2, 3, 4):
    for _ in range(500):
        data = gen(rng, d)
        for make in makers(d):
            it, naive, pool = make(data), NaiveIterator(data, d), []
            for _ in range(25):
                r = rng.random()
                if r < 0.45:
                    assert outcome(next, it) == outcome(naive.next), data
                elif r < 0.6:
                    s = it.get_state()
                    assert type(s) is tuple and s == naive.state(), (data, s, naive.state())
                    pool.append(s)
                    cov["skip_saves"] += naive.skipped_empty()
                    cov["end_saves"] += s == naive.end
                elif r < 0.75 and pool:
                    s = json.loads(json.dumps(rng.choice(pool)))
                    it.set_state(s)
                    naive.seek(s)
                else:
                    s = random_state(rng, naive)
                    got = outcome(it.set_state, s)
                    assert got == outcome(naive.seek, s), (data, s, got)
                    cov[got[0]] += 1
                assert it.get_state() == naive.state(), data      # also after a rejected state
            # hand the state to an iterator over other data: same shape, then a random shape
            s = it.get_state()
            for other, same_shape in ((relabel(data, d), True), (gen(rng, d), False)):
                it_o, naive_o = make(other), NaiveIterator(other, d)
                got = outcome(it_o.set_state, s)
                assert got == outcome(naive_o.seek, s), (data, other, s)
                if got[0] == "ok":
                    assert list(it_o) == naive_o.rest()
                if not same_shape:
                    cov["other_shape_ok" if got[0] == "ok" else "other_shape_bad"] += 1
print(cov)
assert min(cov.values()) > 300, cov

# --- follow-ups ---
buf = io.TextIOWrapper(io.BytesIO(b"alpha\nbeta\n"))
next(buf)
expect(OSError, buf.tell)                       # text mode: telling position disabled by next() call
raw = io.BufferedReader(io.BytesIO(b"alpha\nbeta\n"))
next(raw)
assert raw.tell() == 6

gen_it = (x for row in [[7, 2], [9]] for x in row)
next(gen_it)
try:
    copy.deepcopy(gen_it)
    raise AssertionError
except TypeError as e:
    assert "cannot pickle 'generator' object" in str(e)

cube = ResumableNestedIterator(np.arange(24).reshape(2, 3, 4), depth=3)
assert [int(next(cube)) for _ in range(9)] == list(range(9))
s_np = cube.get_state()
assert s_np == (0, 2, 1) and all(type(v) is int for v in s_np)
cube.set_state(json.loads(json.dumps(s_np)))
assert [int(v) for v in cube] == list(range(9, 24))
assert list(Resumable2DIterator(np.zeros((3, 0)))) == []
assert list(Resumable2DIterator(((4, 1), (), (8,)))) == [4, 1, 8]
print("all checks passed")
```

</details>

</details>
