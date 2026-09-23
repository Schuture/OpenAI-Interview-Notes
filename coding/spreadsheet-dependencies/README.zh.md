# 带单元格依赖的电子表格（OpenSheet）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★☆☆☆☆ | 中等 | SWE | graph, dfs, topological-sort, recursion | 3 个部分 |
<!-- meta:end -->

## 题目

*单元格名*（cell name）由一个或多个大写字母 `A`–`Z`（列）加一个或多个数字 `0`–`9`（行）组成，不含其他字符，例如 `A1`、`AB12`；
`a1`、`A`、`A1B` 都不是单元格名。一个单元格保存的要么是一个 Python `int`，要么是一条*公式*（formula）：`=` 后面跟一个或多个*项*（term），
相邻两项之间恰好有一个 `+` 或 `-`，例如 `=R1 + 20 - S3` 或 `=5`。项是一个单元格名，或者一个不超过 18 位的非负整数字面量。
项和运算符的前后可以有空格，项的内部不能有。除此之外什么都不允许：没有 `*`、`/` 和括号，第一项之前、最后一项之后也不能有运算符，
所以 `=-R1`、`=R1 - -S3`、`=R1 2` 都不合法。读取一个从未被 `set` 过的单元格名——无论是直接读取，还是通过某条公式引用到它——都得到 `0`。
`set` 和 `get` 收到的名字不是单元格名时都抛出 `FormulaError`；`set` 收到的值既不是 `int` 也不是合法公式时，同样抛出 `FormulaError`。

### Part 1 —— 按需求值

实现 `LazySpreadsheet`。`set(name, value)` 把 `value`——一个 `int`，或者一条公式字符串——存入 `name`，替换它原来的内容。
`get(name)` 返回 `name` 当前的整数值：如果是字面量就是它本身，如果是公式就把它引用的每个单元格替换成那个单元格当前的值，递归求值。
如果某个单元格的公式直接或经由其他单元格的公式读到了它自己，这些单元格就构成*循环依赖*（circular dependency）。
即使一条公式会造成循环依赖，`set` 也照样存入；`get(name)` 在求 `name` 的值需要用到循环依赖上某个单元格时，必须抛出 `CycleError`，
否则正常返回。可以假设从任一单元格出发沿引用往下走、不重复经过同一个单元格，最多经过 200 个单元格。

```py
class LazySpreadsheet:
    def set(self, name: str, value: int | str) -> None:
        """Stores value for name. Raises FormulaError if name or value is not of the shape above."""

    def get(self, name: str) -> int:
        """Evaluates name, recursively reading the cells its formula references.
        Raises CycleError if that needs a cell on a circular dependency."""
```

例如依次设置 `P4 = 6`、`Q2 = 17`、`M3 = "=Q2 - P4"`、`M8 = "=M3 - P4 + 30"`，`get("M8")` 是 `35`。
之后设置 `P4 = 14`，再读 `M8` 得到 `19`，因为此时 `M3` 是 `3`。设置 `U1 = "=U2"`、再设置 `U2 = "=U1"` 都能成功；
随后 `get("U1")` 会抛出 `CycleError`，对任何公式读到 `U1` 的单元格调用 `get` 也是如此。

### Part 2 —— 写入时立即更新

实现 `Spreadsheet`，`set`/`get` 的约定与上面相同，只是 `set` 会立即让每个单元格的值保持最新，使得 `get` 永远只读取一个
已经算好的值，运行时间是 $O(1)$。与 `LazySpreadsheet.set` 不同，如果新的 `value` 会造成循环依赖，`set` 必须拒绝它并抛出 `CycleError`，
不存入任何东西，让该单元格原来的内容、依赖图以及所有已缓存的值都保持原样。

```py
class Spreadsheet:
    def set(self, name: str, value: int | str) -> None:
        """Same contract as LazySpreadsheet.set, but recomputes every affected cell immediately, and
        raises CycleError (without changing anything) if value would create a circular dependency."""

    def get(self, name: str) -> int:
        """O(1): returns the already-computed value of name."""
```

用与 Part 1 例子相同的一串 `set` 调用，`get("M8")` 依然先是 `35`，`P4` 更新后变成 `19`——但现在每次 `get`
都只是一次缓存查询，因为 `P4` 改变的那一刻 `set` 就已经把 `M8`（以及它和 `P4` 之间的一切）重新算好了。
依次调用 `set("U1", "=U2")`、`set("U2", "=U1")`，第二次调用会抛出 `CycleError`，`U1`、`U2` 以及表里其余单元格都不受这次被拒绝的调用影响。

### Part 3 —— 边界情形

为 `Spreadsheet`（以及标注出的部分，`LazySpreadsheet`）的下列行为实现并跑通测试：

- 覆盖一个原本是公式的单元格——不管新值是公式还是字面量——都要删除它的旧依赖边：它原来读取的某个单元格再变化，
  不应该再触发它重算。
- 直接自引用（`set("H2", "=H2")`）和经过若干个单元格才形成的环，都要被 `Spreadsheet.set` 拒绝；同样这两种情形，
  `LazySpreadsheet` 只能在 `get` 时才能发现。
- 一条公式可以引用一个还没有被 `set` 过的单元格（读作 `0`）；之后再 `set` 这个单元格时，所有传递依赖它的单元格都要更新。
- 在一个“菱形”结构里——两个单元格都读同一个单元格，第四个单元格又同时读这两者——对公共单元格的一次 `set`
  只应把第四个单元格重算一次，而不是按到它的路径数重算多次。
- 覆盖一个原本是字面量的单元格、改成公式时，新的依赖边要立即生效：这次 `set` 调用之后，该单元格自己缓存的值、
  以及所有传递依赖它的单元格，都要反映这条新公式，而不是那个已经过期的字面量。

## 参考解答

<details>
<summary>展开参考解答</summary>

值得先确认：公式要不要支持乘除法或区域引用（假设不用）；单元格名不合法是否立即报错（假设是）。

### Part 1

`_FORMULA_RE` 用一个正则写出完整语法（一项，后跟任意多个 `[+-]` 加一项），`fullmatch` 一次就完成校验，
开头的运算符、连续两项、结尾的运算符都会被挡掉；`_SIGNED_TERM_RE` 再把合法公式拆成带符号的项。`get`
递归地展开公式，用 `visiting` 集合捕捉回到正在求值的单元格的路径，
与有向图里用 DFS 找环是同一个思路。结果如果跨调用缓存，它读过的单元格一旦被重新 `set` 就会过期，因为 Part 1
不记录谁依赖谁；只在单次调用内有效的 `memo` 不需要失效逻辑，$N$ 个单元格仍是 $O(N)$（共享的单元格每次调用只求值一次）。
代价是递归深度：最长链上每个单元格占三层 Python 栈帧，约 330 个单元格的链就会用完默认的 1000 层上限。

```python
import re


class FormulaError(ValueError):
    """Bad cell name, or bad formula syntax."""


class CycleError(ValueError):
    """A formula depends on itself, directly or indirectly."""


CELL_RE = re.compile(r'[A-Z]+[0-9]+')


def _check_name(name):
    if not CELL_RE.fullmatch(name):  # NOTE: not match() with '$', which also accepts 'A1\n'
        raise FormulaError(f"not a valid cell name: {name!r}")


_TERM = r'(?:[A-Z]+[0-9]+|[0-9]{1,18})'
_FORMULA_RE = re.compile(rf' *{_TERM}(?: *[+-] *{_TERM})* *')  # spaces only around terms
_SIGNED_TERM_RE = re.compile(rf'[+-]?{_TERM}')


def parse_formula(formula):
    """Returns the formula's (sign, kind, value) terms, kind in {'NUM', 'CELL'}."""
    if not isinstance(formula, str) or not formula.startswith('='):
        raise FormulaError(f"formula must start with '=': {formula!r}")
    body = formula[1:]
    if not _FORMULA_RE.fullmatch(body):  # NOTE: a bare term comes first, so no unary minus ("=-A1")
        raise FormulaError(f"not a valid formula: {formula!r}")
    terms = []
    for tok in _SIGNED_TERM_RE.findall(body.replace(' ', '')):
        sign, tok = (-1, tok[1:]) if tok[0] == '-' else (1, tok.lstrip('+'))
        terms.append((sign, 'CELL', tok) if CELL_RE.fullmatch(tok) else (sign, 'NUM', int(tok)))
    return terms


def _referenced_cells(value):
    """Validates value; returns the cells its formula references (empty for a literal)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return set()
    if isinstance(value, str) and value.startswith('='):
        return {item for _, kind, item in parse_formula(value) if kind == 'CELL'}
    raise FormulaError(f"neither an int nor a formula: {value!r}")


def _eval_terms(value, lookup):
    """lookup(cell) returns the value of a cell the formula reads."""
    if isinstance(value, int):
        return value
    total = 0
    for sign, kind, item in parse_formula(value):
        total += sign * (item if kind == 'NUM' else lookup(item))
    return total


class LazySpreadsheet:
    def __init__(self):
        self.contents = {}

    def set(self, name, value):
        _check_name(name)
        _referenced_cells(value)  # validate now; get() parses the formula again
        self.contents[name] = value  # NOTE: no cycle check here; get() finds cycles

    def get(self, name):
        _check_name(name)
        return self._eval(name, set(), {})

    def _eval(self, name, visiting, memo):
        if name in memo:
            return memo[name]
        if name in visiting:
            raise CycleError(f"circular reference through {name!r}")
        value = self.contents.get(name)
        if value is None:
            result = 0
        else:
            visiting.add(name)  # NOTE: mark before recursing, so a path back to `name` is caught
            result = _eval_terms(value, lambda c: self._eval(c, visiting, memo))
            visiting.discard(name)  # NOTE: visiting is the current path; finished cells answer from memo
        memo[name] = result
        return result
```

### Part 2

两张表取代了递归：`dependencies[name]` 是 `name` 读了哪些单元格，`dependents[name]` 是谁读了 `name`。引用
`refs` 的公式造成环，当且仅当 `refs` 里某个单元格就是 `name`，或者已经传递地依赖 `name`，也就是沿 `dependents`
从 `name` 出发能到达它。在改动任何东西之前，从 `name` 沿 `dependents` 遍历一次，既能判断是否成环，又给出
`affected`，它恰好是需要重算的单元格：这个集合只取决于谁读 `name`，本次调用不会改变它。检查先于修改，
所以拒绝时无需回滚；先提交、成环后再回滚的写法还得恢复*修改前*的公式，容易写错。通过检查后，`affected`
按拓扑序重算，菱形依赖只被访问一次。

```python
from collections import deque


class Spreadsheet:
    def __init__(self):
        self.contents = {}
        self.cache = {}
        self.dependencies = {}   # cell -> set of cells it reads
        self.dependents = {}     # cell -> set of cells that read it

    def set(self, name, value):
        _check_name(name)
        new_refs = _referenced_cells(value)  # raises FormulaError; touches nothing yet
        affected = self._affected(name)      # everyone that (transitively) reads `name`, incl. itself
        if new_refs & affected:
            raise CycleError(f"{name} = {value!r} would close a cycle")
        # NOTE: nothing above was mutated, so a rejected set needs no rollback.

        for old in self.dependencies.get(name, ()):  # NOTE: drop old edges first -- otherwise a formula
            self.dependents[old].discard(name)         #       that no longer reads X would still recompute on X
        self.dependencies[name] = new_refs
        for r in new_refs:
            self.dependents.setdefault(r, set()).add(name)
        self.contents[name] = value
        for cell in self._topological_order(affected):
            self._recompute_one(cell)

    def get(self, name):
        _check_name(name)
        return self.cache.get(name, 0)

    def _affected(self, name):
        """name plus everything reachable from it by following `dependents` (who reads whom)."""
        affected, stack = {name}, [name]
        while stack:
            cell = stack.pop()
            for dep in self.dependents.get(cell, ()):
                if dep not in affected:
                    affected.add(dep)
                    stack.append(dep)
        return affected

    def _topological_order(self, affected):
        indegree = {c: sum(d in affected for d in self.dependencies.get(c, ())) for c in affected}
        queue = deque(c for c in affected if not indegree[c])
        order = []
        while queue:
            c = queue.popleft()
            order.append(c)
            for dep in self.dependents.get(c, ()):
                if dep in affected:
                    indegree[dep] -= 1
                    if not indegree[dep]:
                        queue.append(dep)
        return order

    def _recompute_one(self, cell):
        value = self.contents.get(cell)
        self.cache[cell] = 0 if value is None else _eval_terms(
            value, lambda c: self.cache.get(c, 0))
```

`get` 是一次名字检查加一次字典查找，耗时几百纳秒，表里有两个单元格还是 20000 个都一样。`set` 的耗时
与受影响单元格的个数加上它们公式的长度（以及 `name` 旧公式的长度）成正比，因为它经过的每条依赖边都是这些公式里的一项：
一条长链上每格几微秒，与链外有多少单元格无关。

### Part 3

前三条由上面的代码直接保证：旧依赖边由 `set` 里判环之后的那个循环删除；从未 `set` 的单元格经 `.get(name, 0)`
读作 `0`，之后 `set` 它时照常从 `dependents` 找到读它的单元格；`LazySpreadsheet` 不保存依赖图，只能靠递归走进环才发现它。
菱形依赖靠拓扑序：每个单元格只被 `_affected` 收集一次、被 `_topological_order` 发出一次，一次 `set` 里不会重算两次。
最后一条是同一段代码反过来看：`set` 在写入之前先读 `self.dependencies.get(name, ())`——`name` 第一次变成公式时这
自然就是空的——所以字面量变公式时加边、公式变别的东西时删边，走的是同样这四行代码，不是两套要分别维护的逻辑。

### 追问

- `SUM(A1:A100)` 这样的区域引用会给它覆盖的每个单元格加一条依赖边；难点在于插入或删除行时更新这组边，而不是求和本身。
- 批量写入的 `set_many` 必须在所有新边都加上之后再判环，因为两次写入可能合起来成环（`X1 = "=Y1"`、`Y1 = "=X1"`）；
  对受影响单元格的并集做一次 Kahn 拓扑排序，既能发现环，又给出重算顺序，$B$ 次写入涉及 $K$ 个单元格，代价 $O(K)$ 而非 $O(B \cdot K)$。
- 急切重算每次 `set` 都要付代价，即使结果之后不再被读；写多读少的表更适合标记依赖者为“脏”，留到下次 `get` 才重算。

<details>
<summary>验证代码（可运行）</summary>

```python
import random
import re
import time


def expect(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} from {fn.__name__}{args!r}")


# ---- the worked example from the statement, both spreadsheets ----
for Sheet in (LazySpreadsheet, Spreadsheet):
    sh = Sheet()
    sh.set('P4', 6)
    sh.set('Q2', 17)
    sh.set('M3', '=Q2 - P4')
    sh.set('M8', '=M3 - P4 + 30')
    assert sh.get('M8') == 35
    sh.set('P4', 14)
    assert sh.get('M8') == 19 and sh.get('M3') == 3

# ---- LazySpreadsheet: set() stores cycles; get() raises on every cell that needs one ----
lz = LazySpreadsheet()
lz.set('U1', '=U2')
lz.set('U2', '=U1')
lz.set('V1', '=U1 + 1')  # not on the cycle, but reads it
lz.set('H2', '=H2 + 1')  # self-reference
lz.set('W1', 5)
for cell in ('U1', 'U2', 'V1', 'H2'):
    expect(CycleError, lz.get, cell)
assert lz.get('W1') == 5
lz.set('U2', 8)  # overwriting breaks both cycles
lz.set('H2', 3)
assert (lz.get('U1'), lz.get('V1'), lz.get('H2')) == (8, 9, 3)
deep = LazySpreadsheet()  # the longest chain Part 1 allows
deep.set('K1', 1)
for i in range(2, 201):
    deep.set(f'K{i}', f'=K{i - 1} + 1')
assert deep.get('K200') == 200
for i in range(201, 400):
    deep.set(f'K{i}', f'=K{i - 1} + 1')
expect(RecursionError, deep.get, 'K399')  # ~3 frames per cell: 399 cells pass the limit of 1000


# ---- Spreadsheet: set() rejects a cycle and changes nothing ----
def state(sh):
    return (dict(sh.contents), dict(sh.cache),
            {k: set(v) for k, v in sh.dependencies.items()}, {k: set(v) for k, v in sh.dependents.items()})


sh = Spreadsheet()
sh.set('U1', '=U2 + 1')  # U2 is not set yet; reads as 0 for now
sh.set('H2', 7)
sh.set('V1', '=H2 + U1')
before = state(sh)
for name, value in (('U2', '=U1'), ('H2', '=H2 + 1'), ('H2', '=V1 - 2'), ('U2', '=V1')):
    expect(CycleError, sh.set, name, value)
    assert state(sh) == before
assert (sh.get('U1'), sh.get('H2'), sh.get('V1')) == (1, 7, 8)
sh.set('U1', 4)  # U1 stops reading U2 ...
sh.set('U2', '=U1')  # ... so this no longer closes a cycle
assert (sh.get('U2'), sh.get('V1')) == (4, 11)

# ---- Part 3 and the statement's syntax rules ----
for bad_name in ('a1', '1A', 'A', 'A1B', 'A 1', 'A1\n'):
    for sheet in (LazySpreadsheet(), Spreadsheet()):
        expect(FormulaError, sheet.set, bad_name, 1)
        expect(FormulaError, sheet.get, bad_name)
for bad in ('=', '=D4*2', '=(D4+2)', '=D4++E4', '=D4--E4', '=D4 - -E4', '=D4+', '=-D4', '=+D4', '=D4 E4',
            '=D 4', '=D4 2', '=d4+2', '=D4\t+ 2', '=' + '9' * 19, '=' + '9' * 5000, '42', ' =D4', 4.0, True):
    for sheet in (LazySpreadsheet(), Spreadsheet()):
        expect(FormulaError, sheet.set, 'D5', bad)
sh = Spreadsheet()
for good, value in (('=5', 5), ('=007', 7), ('=' + '9' * 18, 10 ** 18 - 1), ('=  D4 +E4 -  3 ', -3)):
    sh.set('D5', good)
    assert sh.get('D5') == value

sh = Spreadsheet()  # overwriting drops the old dependency
sh.set('J1', 4)
sh.set('K1', '=J1 + 6')
sh.set('K1', 70)
assert 'K1' not in sh.dependents['J1']
sh.set('J1', 500)
assert sh.get('K1') == 70

sh = Spreadsheet()  # ... and the reverse: a literal overwritten with a formula picks up edges at once
sh.set('J1', 4)
sh.set('K1', 70)
sh.set('K1', '=J1 + 6')
assert 'K1' in sh.dependents['J1'] and sh.get('K1') == 10
sh.set('J1', 500)
assert sh.get('K1') == 506

sh = Spreadsheet()  # a formula may reference a cell that is set only later
sh.set('M1', '=N1 + 5')
sh.set('M2', '=M1 - 1')
assert (sh.get('N1'), sh.get('M2')) == (0, 4)
sh.set('N1', 3)
assert sh.get('M2') == 7

sh = Spreadsheet()  # diamond: recomputed exactly once per set()
calls, recompute = [], sh._recompute_one
sh._recompute_one = lambda cell: (calls.append(cell), recompute(cell))
sh.set('E5', 2)
sh.set('F5', '=E5 + 3')
sh.set('G5', '=E5 - 1')
sh.set('H5', '=F5 + G5')
calls.clear()
sh.set('E5', 40)
assert sorted(calls) == ['E5', 'F5', 'G5', 'H5'] and sh.get('H5') == 43 + 39

# ---- cross-validation against a naive evaluator written from the statement alone ----
# It shares no code with the solution: its own reference regex, its own cycle rule, eval for arithmetic.
CELL_PATTERN = re.compile(r'[A-Z]+[0-9]+')


def naive_values(raw):
    """raw: cell -> int or formula. Values of the cells that need no cycle; the rest of raw is missing."""
    values, progress = {}, True
    while progress:  # keep evaluating cells whose references are all known or never set
        progress = False
        for cell, v in raw.items():
            refs = [] if isinstance(v, int) else CELL_PATTERN.findall(v)
            if cell not in values and all(r in values or r not in raw for r in refs):
                expr = str(v) if isinstance(v, int) else CELL_PATTERN.sub(
                    lambda m: str(values.get(m.group(), 0)), v[1:])
                assert re.fullmatch(r'[0-9+\- ]+', expr)  # eval only ever sees digits, '+', '-', spaces
                values[cell] = eval(expr, {'__builtins__': {}}, {})
                progress = True
    return values


def random_value(rng, pool, readers):
    r = rng.random()
    if readers and r < 0.25:
        return f"={rng.choice(readers)} + 1"  # closes a cycle
    if r < 0.4:
        return rng.randint(-20, 20)
    text = rng.choice(pool)
    for _ in range(rng.randint(0, 2)):
        text += rng.choice([' + ', '-']) + rng.choice(pool + ['0', '7', '42'])
    return '=' + text


def cross_validate(seed, steps=300):
    rng = random.Random(seed)
    pool = [f"{c}{r}" for c in "ABC" for r in range(1, 5)]
    eager, lazy, eager_raw, lazy_raw = Spreadsheet(), LazySpreadsheet(), {}, {}
    rejected = lazy_cycles = 0
    for _ in range(steps):
        name = rng.choice(pool)
        readers = [c for c, v in eager_raw.items() if isinstance(v, str) and name in CELL_PATTERN.findall(v)]
        value = random_value(rng, pool, readers)
        lazy.set(name, value)  # Part 1 stores cycles too
        lazy_raw[name] = value
        trial = {**eager_raw, name: value}
        expected = naive_values(trial)
        if len(expected) < len(trial):  # the new value would close a cycle
            before = [eager.get(c) for c in pool]
            expect(CycleError, eager.set, name, value)
            assert [eager.get(c) for c in pool] == before
            rejected += 1
        else:
            eager.set(name, value)
            eager_raw = trial
            assert all(eager.get(c) == expected.get(c, 0) for c in pool)
        lazy_expected = naive_values(lazy_raw)
        for c in pool:
            if c in lazy_raw and c not in lazy_expected:
                expect(CycleError, lazy.get, c)
                lazy_cycles += 1
            else:
                assert lazy.get(c) == lazy_expected.get(c, 0)
    return rejected, lazy_cycles


results = [cross_validate(seed) for seed in range(20)]
assert all(r >= 20 and c >= 100 for r, c in results)  # both cycle paths exercised in every run


# ---- timing: ratios only, since absolute times depend on the machine ----
def best_per_call(fn, n, repeats=5):
    best = float('inf')
    for _ in range(repeats):  # the minimum over repeats shrugs off background load
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        best = min(best, (time.perf_counter() - t0) / n)
    return best


def chain_sheet(length, unrelated):
    sh = Spreadsheet()
    sh.set('C0', 0)
    for i in range(1, length):
        sh.set(f'C{i}', f'=C{i - 1} + 1')
    for i in range(unrelated):
        sh.set(f'Y{i}', i)
    return sh


small, big = chain_sheet(2, 0), chain_sheet(2, 20000)
get_small = best_per_call(lambda: small.get('C1'), 20000)
get_big = best_per_call(lambda: big.get('C1'), 20000)
assert get_big < 5 * get_small  # get() does not grow with the sheet

bare, crowded = chain_sheet(2000, 0), chain_sheet(2000, 20000)
set_bare = best_per_call(lambda: bare.set('C0', 1), 3)
set_crowded = best_per_call(lambda: crowded.set('C0', 1), 3)
assert set_crowded < 5 * set_bare  # set() does not grow with cells outside the affected set
assert crowded.get('C1999') == 1 + 1999

print(f"get: {get_small * 1e9:.0f} ns on 2 cells, {get_big * 1e9:.0f} ns on 20002; set through a 2000-cell "
      f"chain: {set_bare / 2000 * 1e6:.1f} us/cell, {set_crowded / 2000 * 1e6:.1f} us/cell with 20000 more")
print("all checks OK; (rejected sets, lazy CycleErrors) for the first seeds:", results[:3])
```

</details>

</details>
