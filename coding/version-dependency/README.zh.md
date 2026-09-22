# 版本依赖

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程 | ★★★☆☆ | 中等 | SWE · RE | binary-search, backtracking, topological-sort | 4 个部分 / 75 分钟 |
<!-- meta:end -->

## 题目

包管理器（package manager）需要回答关于所管理软件包的两类问题。Part 1-3 用一个很慢的探测函数，找出某个包最早支持某项特性的已发布版本；Part 4 则为一次安装解析出一整套相互兼容的依赖版本。每个版本号都是字符串 `"{major}.{minor}.{patch}"`，每一段都是可能带前导零的十进制整数（`"103.003.02"` 表示 major 103、minor 3、patch 2）；比较版本时要按 `(major, minor, patch)` 数值元组比较，绝不能按原始字符串比较。

```py
def parse_version(version: str) -> tuple[int, int, int]:
    """Parses "{major}.{minor}.{patch}" into (major, minor, patch)."""
```

### Part 1 —— 单调支持

`versions` 是同一个包的一组互不相同的版本字符串，顺序任意。`is_supported(version)` 会调用注册表（registry）的一个慢速接口，返回该版本是否支持给定特性。假设把 `versions` 按数值排序后，`is_supported` 在这个顺序上是单调的：一段（可能为空的）`False` 后面跟着一段（可能为空的）`True`。实现 `find_earliest_supported_monotone`，返回数值上最小的、`is_supported` 为 `True` 的版本；如果没有版本支持该特性，返回 `None`。

```py
def is_supported(version: str) -> bool:
    """Provided by the package registry: a real network call, slow and rate-limited."""

def find_earliest_supported_monotone(versions: list[str], is_supported) -> str | None:
    """versions: distinct "{major}.{minor}.{patch}" strings, in arbitrary order. Assumes is_supported is
    monotone once versions are ordered numerically. Returns the earliest supported version, or None."""
```

例如，输入 `["2.0.0", "1.10.0", "1.9.1", "1.9.0"]`（本身就不是数值序），支持从 `"1.9.1"` 开始，答案是 `"1.9.1"`：数值上 `(1, 9, 1) < (1, 10, 0) < (2, 0, 0)`，尽管作为普通字符串比较时 `"1.10.0"` 排在 `"1.9.1"` 前面。

### Part 2 —— 版本回退

支持情况可能会回退：版本号变大不代表仍然支持该特性，因此随着版本增大，`is_supported` 可能先返回 `True`，再变成 `False`，然后又变回 `True`。实现 `find_earliest_supported`，去掉 Part 1 的假设，依然返回数值上最早的、`is_supported` 为 `True` 的版本；如果都不支持，返回 `None`。

```py
def find_earliest_supported(versions: list[str], is_supported) -> str | None:
    """Same contract as find_earliest_supported_monotone, but is_supported need not be monotone."""
```

例如，输入 `["3.1.4", "3.1.0", "3.1.2", "3.1.1", "3.1.3"]`，`is_supported` 对 patch 0 到 4 依次返回 `False, True, False, True, False`，答案是 `"3.1.1"`——尽管 `"3.1.3"` 也支持该特性。

### Part 3 —— 分层结构上的限速探测

现在每次调用 `is_supported` 都要计入配额（quota），因此调用次数要尽量少。支持情况在整个列表上不单调，但具有下面的结构（“排序”均指按数值排序）：

- **(A1)** 在同一个 `(major, minor)` 分组内，把 patch 排序后，支持情况是单调的（就是 Part 1 的模式，只不过只在组内成立）。
- **(A2)** 在同一个 major 内，取每个 minor 分组的*代表元*（representative）——该组中数值最大的版本。把这些代表元按 minor 排序后，支持情况是单调的。
- **(A3)** 取每个 major 的*代表元*——该 major 中数值最大的版本。把这些代表元按 major 排序后，支持情况是单调的。

这三条性质只约束了代表元以及每个分组内部，并不能保证把全部版本按数值展平排序后整体单调。例如 major 0 和 1 如下：

```text
0.9.0 -> False
1.0.0 -> False   1.1.0 -> False
1.2.0 -> False   1.2.1 -> True
1.3.0 -> False   1.3.1 -> False   1.3.2 -> False   1.3.3 -> True
```

满足 A1-A3：每个 `(major, minor)` 分组内部都单调；major 1 内部的 minor 代表元 `1.0.0, 1.1.0, 1.2.1, 1.3.3` 依次是 `False, False, True, True`；major 代表元 `0.9.0, 1.3.3` 依次是 `False, True`。但把全部九个版本展平排序后读出来是 `False, False, False, False, True, False, False, False, True`——支持在 `1.2.1` 处出现，在整个 `1.3.0`-`1.3.2` 区间又消失，到 `1.3.3` 才再次出现。因此直接对这个展平列表做二分是不成立的。实现 `find_earliest_supported_hierarchical`，必须改为先对 major 分组做二分，再在选中的 major 内对 minor 分组做二分，最后在选中的 minor 内对 patch 做二分。

```python
class CountingProbe:
    """Wraps is_supported and counts how many times it is actually called."""
    def __init__(self, is_supported):
        self._is_supported = is_supported
        self.calls = 0

    def __call__(self, version: str) -> bool:
        self.calls += 1
        return self._is_supported(version)
```

```py
def find_earliest_supported_hierarchical(versions: list[str], is_supported) -> str | None:
    """Same contract as find_earliest_supported, but assumes A1-A3 above and must call is_supported
    (which may be a CountingProbe) O(log M + log N_minor + log P) times, where M is the number of
    majors, N_minor the largest number of minors within one major, and P the largest number of patches
    within one (major, minor) group -- never probing the same version string twice."""
```

### Part 4 —— 依赖解析

要安装一个包，包管理器必须为它、以及它直接或间接需要的每一个包各选定一个版本，使所有声明的约束都成立。每个 `(package, version)` 用 `requires` 映射声明自己的直接依赖：从依赖的包名映射到一个*约束*（constraint），即一个比较运算符（`==`、`>=`、`<=`、`>`、`<`）加一个版本号，例如 `">=2.0.0"`。多个包可以对同一个依赖各自提出约束，为这个依赖选定的那一个版本必须同时满足全部约束。可用的包保存在一个 `Registry` 里：

```python
class Registry:
    """The available packages: name -> version -> requires."""
    def __init__(self):
        self._versions = {}

    def add_version(self, name: str, version: str, requires: dict[str, str] | None = None) -> None:
        """Registers one available (name, version) and its direct dependencies."""
        self._versions.setdefault(name, {})[version] = dict(requires or {})

    def versions(self, name: str) -> list[str]:
        """All versions registered for name (empty if the name is unknown)."""
        return list(self._versions.get(name, {}))

    def requires(self, name: str, version: str) -> dict[str, str]:
        """The constraints declared by exactly this (name, version)."""
        return self._versions[name][version]
```

```py
def resolve(registry: Registry, root: str) -> list[str] | None:
    """Chooses one version for root and for every package the chosen versions require, so that every
    declared constraint holds, and returns them as "name@version" strings in an install order: every
    package appears after all of its dependencies. Packages the chosen versions do not need are not
    listed. A choice whose dependencies form a cycle has no install order and is therefore not valid.
    Returns None if no valid choice exists."""
```

例如，注册表的内容如下：

```text
toolkit  1.0.0             requires netlib>=2.0.0, parser>=1.0.0
netlib   1.0.0
netlib   2.0.0             requires coreutil==1.0.0
netlib   2.1.0             requires coreutil>=1.2.0
parser   1.0.0             requires coreutil<1.2.0
parser   1.5.0             requires coreutil<1.0.0
coreutil 1.0.0, 1.2.0, 1.3.0   (no dependencies)
```

以 `root = "toolkit"` 解析，得到 `["coreutil@1.0.0", "netlib@2.0.0", "parser@1.0.0", "toolkit@1.0.0"]`（`netlib` 与 `parser` 可以互换位置）。`netlib@2.1.0` 不能用：它要求 `coreutil >= 1.2.0`，而 `parser@1.0.0` 要求 `coreutil < 1.2.0`，`parser@1.5.0` 要求 `coreutil < 1.0.0`。

## 参考解答

<details>
<summary>展开参考解答</summary>

开始写代码前值得跟面试官确认：`is_supported` 是确定性的，Part 4 里的约束始终是一个运算符加一个版本号。

### Part 1

排序之后，`is_supported` 就变成了下标上的单调谓词，于是可以用二分查找而不是线性扫描来找到最左边的 `True`——Part 3 会在每一层都复用这个例程。

```python
def parse_version(version):
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)   # NOTE: int() drops leading zeros; never compare the raw strings


def first_true_index(n, predicate):
    """Leftmost index in range(n) with predicate(i) True, assuming predicate is monotone; else None."""
    left, right, result = 0, n - 1, None
    while left <= right:
        mid = (left + right) // 2
        if predicate(mid):
            result = mid
            right = mid - 1          # an earlier True may still exist -- keep searching left
        else:
            left = mid + 1
    return result


def find_earliest_supported_monotone(versions, is_supported):
    ordered = sorted(versions, key=parse_version)   # NOTE: numeric order; "1.10.0" < "1.9.0" as plain strings
    idx = first_true_index(len(ordered), lambda i: is_supported(ordered[i]))
    return ordered[idx] if idx is not None else None
```

### Part 2

一旦允许回退，`is_supported(ordered[i])` 就不再是关于 `i` 单调的了：在 Part 2 的模式（`False, True, False, True, False`）上，`first_true_index` 会落在下标 3 的那个 `True` 上，返回 `"3.1.3"` 而不是 `"3.1.1"`（下面的验证代码里有这一条）。排序仍然值得保留：它让查找变成一次从左到右的扫描，遇到第一个命中就可以返回，因为后面不会再有更小的版本。

```python
def find_earliest_supported(versions, is_supported):
    for v in sorted(versions, key=parse_version):
        if is_supported(v):        # sorted, so this first True is already the earliest
            return v
    return None
```

### Part 3

关键在于：一个分组的代表元决定了该组里有没有被支持的版本。对 `(major, minor)` 组，这就是 A1：只要有一个 patch 被支持，最新的 patch 也被支持。对 major：元组比较时 minor 先于 patch，所以 major 的代表元同时也是它最新的 minor 组的代表元；如果该 major 里有某个版本被支持，由 A1 它所在 minor 组的代表元为 `True`，再由 A2 此后每个 minor 组的代表元都为 `True`，其中包括 major 自己的代表元。因此代表元为 `False` 的分组整组都不被支持。由 A3，代表元为 `True` 的 major 构成一个后缀，用二分找到其中第一个，记为 $M$；更早的 major 整个不被支持，所以答案在 $M$ 里。同样的论证配合 A2，找到 $M$ 中第一个代表元为 `True` 的 minor 组，最后由 A1 在该组的 patch 上再做一次二分。

在小规模的版本集合（最多 12 个版本）上枚举全部满足 A1-A3 的支持模式，结果都与全量扫描一致。一旦违反 A1（同一组内出现 `True, False, True`），patch 层的二分会返回较晚的那个 `True`。

```python
def find_earliest_supported_hierarchical(versions, is_supported):
    cache = {}
    def probe(v):
        if v not in cache:                     # NOTE: never call is_supported twice for one version
            cache[v] = is_supported(v)
        return cache[v]

    tree = {}                                   # major -> minor -> patch-sorted versions
    for v in versions:
        major, minor, _ = parse_version(v)
        tree.setdefault(major, {}).setdefault(minor, []).append(v)
    for minors in tree.values():
        for patches in minors.values():
            patches.sort(key=parse_version)

    majors = sorted(tree)
    rep = lambda i: max((p[-1] for p in tree[majors[i]].values()), key=parse_version)   # NOTE: latest = rep
    mi = first_true_index(len(majors), lambda i: probe(rep(i)))
    if mi is None:
        return None

    minors = sorted(tree[majors[mi]])
    ni = first_true_index(len(minors), lambda i: probe(tree[majors[mi]][minors[i]][-1]))
    patches = tree[majors[mi]][minors[ni]]
    pi = first_true_index(len(patches), lambda i: probe(patches[i]))
    return patches[pi]
```

在上面的例子上，这个过程依次探测 `"0.9.0", "1.3.3"`，然后 `"1.1.0", "1.2.1"`，然后 `"1.2.0"`（`"1.2.1"` 已被缓存）：9 个版本只用了 5 次调用，符合 $O(\log M + \log N_{\text{minor}} + \log P)$。

### Part 4

选版本是一个约束满足（constraint satisfaction）搜索。`pending` 保存已选版本声明过、但还没有处理的 `(包名, 约束)`。取出第一项：如果这个包已经选定了版本，新约束只能用来检验；否则按从新到旧依次尝试满足该约束的每个版本，并带着列表的其余部分和刚选版本的依赖继续搜索。每次尝试都带着全部剩余的待办项，所以之后任何地方失败，都会回到最近的一次选择去试下一个版本。搜索因此是穷尽的，只有不存在合法选择时才返回 `None`。`pending` 为空时所有约束都已成立，再用 Kahn 算法生成安装顺序：反复输出一个依赖已全部输出的包。始终输出不了的包位于环上，这组选择作废，搜索继续。在 2000 个随机注册表上，结果与枚举所有版本组合的暴力解一致。

```python
import operator
from collections import deque

_OPS = {"==": operator.eq, ">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}


def satisfies(version, constraint):
    for op in ("==", ">=", "<=", ">", "<"):        # NOTE: two-character operators first, or ">=" is read as ">"
        if constraint.startswith(op):
            return _OPS[op](parse_version(version), parse_version(constraint[len(op):]))
    raise ValueError(f"bad constraint: {constraint!r}")


def install_order(registry, chosen):
    """Kahn's algorithm over the chosen versions; None if their dependencies form a cycle."""
    indegree = {name: 0 for name in chosen}
    dependents = {name: [] for name in chosen}
    for name, version in chosen.items():
        for dep in registry.requires(name, version):
            dependents[dep].append(name)
            indegree[name] += 1
    queue = deque(sorted(name for name in chosen if indegree[name] == 0))
    order = []
    while queue:
        name = queue.popleft()
        order.append(f"{name}@{chosen[name]}")
        for other in sorted(dependents[name]):
            indegree[other] -= 1
            if indegree[other] == 0:
                queue.append(other)
    return order if len(order) == len(chosen) else None      # NOTE: a shorter order means a cycle


def resolve(registry, root):
    def search(chosen, pending):
        """chosen: name -> version so far; pending: declared (name, constraint) pairs not yet enforced."""
        if not pending:
            return install_order(registry, chosen)            # a cyclic choice fails here and the search goes on
        (name, constraint), rest = pending[0], pending[1:]
        if name in chosen:                                     # version already fixed: the constraint is only checked
            return search(chosen, rest) if satisfies(chosen[name], constraint) else None
        for version in sorted(registry.versions(name), key=parse_version, reverse=True):   # newest first
            if satisfies(version, constraint):
                found = search({**chosen, name: version}, rest + list(registry.requires(name, version).items()))
                if found is not None:
                    return found
        return None                                            # NOTE: the caller then tries its own next version

    return search({}, [(root, ">=0.0.0")])
```

### 追问

- 每个包只能选一个版本的依赖解析是 NP 完全问题（3-SAT 可以归约到它），所以最坏情况是指数时间。实用的解析器为每个包维护候选版本集合，每来一条约束就收缩它（集合变空立即失败），并记录每次冲突的原因，避免再次走进同一条死路。
- 某些版本之间成环并不意味着无解：如果 `x@2.0.0` 与 `y@1.0.0` 互相依赖，而 `x@1.0.0` 没有依赖，搜索会否决成环的选择并返回 `x@1.0.0`。
- 如果注册表允许并发调用，可以把同一层的全部代表元一次发出：总共只有三轮延迟，代价是调用次数从对数级变成 $O(M + N_{\text{minor}} + P)$。
- 预发布后缀（如 `2.1.0-beta`）排在对应正式版之前，解析时多加一个元组字段即可：预发布版是 `(2, 1, 0, 0, "beta")`，`2.1.0` 是 `(2, 1, 0, 1, "")`。
- 如果 `is_supported` 可能超时，就带退避地重试，并且不要把失败当作 `False` 缓存：代表元上一个错误的 `False` 会把二分引向错误的分组。

<details>
<summary>验证代码（可运行）</summary>

```python
# --- Parts 1-3 ---
versions1 = ["2.0.0", "1.10.0", "1.9.1", "1.9.0"]
support1 = {"1.9.0": False, "1.9.1": True, "1.10.0": True, "2.0.0": True}
assert find_earliest_supported_monotone(versions1, lambda v: support1[v]) == "1.9.1"

versions2 = ["3.1.4", "3.1.0", "3.1.2", "3.1.1", "3.1.3"]
support2 = dict(zip(sorted(versions2, key=parse_version), [False, True, False, True, False]))
assert find_earliest_supported(versions2, lambda v: support2[v]) == "3.1.1"
# the naive bisection of Part 1 is unsound on this same regression pattern:
assert find_earliest_supported_monotone(versions2, lambda v: support2[v]) == "3.1.3"

support3 = {
    "0.9.0": False,
    "1.0.0": False, "1.1.0": False,
    "1.2.0": False, "1.2.1": True,
    "1.3.0": False, "1.3.1": False, "1.3.2": False, "1.3.3": True,
}
probe3 = CountingProbe(lambda v: support3[v])
result3 = find_earliest_supported_hierarchical(list(support3), probe3)
assert result3 == "1.2.1" and find_earliest_supported(list(support3), lambda v: support3[v]) == result3
assert probe3.calls == 5   # against 9 versions total

# violating A1 (True, False, True within one (major, minor) group) breaks the hierarchical search
support_bad = {"1.0.0": True, "1.0.1": False, "1.0.2": True}
assert find_earliest_supported(list(support_bad), lambda v: support_bad[v]) == "1.0.0"
assert find_earliest_supported_hierarchical(list(support_bad), lambda v: support_bad[v]) == "1.0.2"

# exhaustive enumeration: every A1-A3-respecting pattern on small version sets agrees with a full scan
import itertools


def enumerate_a1_a3(majors, minors, patches):
    versions = sorted((f"{M}.{m}.{p}" for M in range(majors) for m in range(minors) for p in range(patches)),
                       key=parse_version)
    checked = 0
    for bits in itertools.product([False, True], repeat=len(versions)):
        support = dict(zip(versions, bits))
        ok = True
        for M in range(majors):
            for m in range(minors):
                seq = [support[f"{M}.{m}.{p}"] for p in range(patches)]
                ok &= not any(seq[i] and not seq[i + 1] for i in range(len(seq) - 1))
            reps = [support[f"{M}.{m}.{patches - 1}"] for m in range(minors)]
            ok &= not any(reps[i] and not reps[i + 1] for i in range(len(reps) - 1))
        major_reps = [support[f"{M}.{minors - 1}.{patches - 1}"] for M in range(majors)]
        ok &= not any(major_reps[i] and not major_reps[i + 1] for i in range(len(major_reps) - 1))
        if not ok:
            continue
        checked += 1
        expected = find_earliest_supported(versions, lambda v: support[v])
        got = find_earliest_supported_hierarchical(versions, lambda v: support[v])
        assert got == expected, (support, expected, got)
    return checked


for shape in [(2, 2, 2), (3, 2, 2), (2, 3, 2), (2, 2, 3)]:
    assert enumerate_a1_a3(*shape) > 0

# --- Part 4 ---
def build_example():
    reg = Registry()
    reg.add_version("toolkit", "1.0.0", {"netlib": ">=2.0.0", "parser": ">=1.0.0"})
    reg.add_version("netlib", "1.0.0", {})
    reg.add_version("netlib", "2.0.0", {"coreutil": "==1.0.0"})
    reg.add_version("netlib", "2.1.0", {"coreutil": ">=1.2.0"})
    reg.add_version("parser", "1.0.0", {"coreutil": "<1.2.0"})
    reg.add_version("parser", "1.5.0", {"coreutil": "<1.0.0"})
    reg.add_version("coreutil", "1.0.0", {})
    reg.add_version("coreutil", "1.2.0", {})
    reg.add_version("coreutil", "1.3.0", {})
    return reg


order = resolve(build_example(), "toolkit")
assert order == ["coreutil@1.0.0", "netlib@2.0.0", "parser@1.0.0", "toolkit@1.0.0"]

reg_cycle = Registry()
reg_cycle.add_version("app", "1.0.0", {"x": ">=1.0.0"})
reg_cycle.add_version("x", "1.0.0", {"y": ">=1.0.0"})
reg_cycle.add_version("y", "1.0.0", {"x": ">=1.0.0"})     # x <-> y: no version of either escapes it
assert resolve(reg_cycle, "app") is None

reg_avoid = Registry()
reg_avoid.add_version("app", "1.0.0", {"x": ">=1.0.0"})
reg_avoid.add_version("x", "1.0.0", {})                   # no dependency at all: breaks the potential cycle
reg_avoid.add_version("x", "2.0.0", {"y": ">=1.0.0"})
reg_avoid.add_version("y", "1.0.0", {"x": ">=1.0.0"})     # only cycles back if x picks 2.0.0
order_avoid = resolve(reg_avoid, "app")
assert order_avoid is not None and dict(e.split("@") for e in order_avoid)["x"] == "1.0.0"


def is_valid_order(registry, root, order):
    """Independently re-derives validity: every listed package's constraints hold, dependencies precede
    dependents, and the closure from root is exactly the set listed."""
    chosen = {}
    for entry in order:
        name, version = entry.rsplit("@", 1)
        if name in chosen:
            return False
        chosen[name] = version
    if root not in chosen:
        return False
    position = {e.rsplit("@", 1)[0]: i for i, e in enumerate(order)}
    reachable, stack = set(), [root]
    while stack:
        name = stack.pop()
        if name in reachable:
            continue
        reachable.add(name)
        for dep_name, constraint in registry.requires(name, chosen[name]).items():
            if dep_name not in chosen or not satisfies(chosen[dep_name], constraint):
                return False
            if position[dep_name] >= position[name]:
                return False
            stack.append(dep_name)
    return reachable == set(chosen)


assert is_valid_order(build_example(), "toolkit", order) is True


def brute_force_satisfiable(registry, root):
    names = list(registry._versions)
    for combo in itertools.product(*[registry.versions(n) for n in names]):
        assignment = dict(zip(names, combo))
        reachable, stack, ok = set(), [root], True
        while stack and ok:
            name = stack.pop()
            if name in reachable:
                continue
            reachable.add(name)
            for dep_name, constraint in registry.requires(name, assignment[name]).items():
                if dep_name not in assignment or not satisfies(assignment[dep_name], constraint):
                    ok = False
                    break
                stack.append(dep_name)
        if not ok:
            continue
        indegree = {n: 0 for n in reachable}
        adj = {n: [] for n in reachable}
        for n in reachable:
            for dep_name in registry.requires(n, assignment[n]):
                adj[dep_name].append(n)
                indegree[n] += 1
        q = deque(n for n in reachable if indegree[n] == 0)
        seen = 0
        while q:
            n = q.popleft()
            seen += 1
            for nxt in adj[n]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    q.append(nxt)
        if seen == len(reachable):
            return True
    return False


assert brute_force_satisfiable(build_example(), "toolkit") is True
assert brute_force_satisfiable(reg_cycle, "app") is False


def random_registry(rng, names, max_versions=3, max_deps=2):
    reg = Registry()
    for name in names:
        vers = sorted({f"{rng.randint(1, 2)}.{rng.randint(0, 2)}.{rng.randint(0, 2)}"
                       for _ in range(rng.randint(1, max_versions))}) or ["1.0.0"]
        others = [n for n in names if n != name]
        for v in vers:
            requires = {}
            for dep in rng.sample(others, k=min(max_deps, len(others))) if others else []:
                if rng.random() < 0.6:
                    op = rng.choice([">=", "<=", ">", "<", "=="])
                    bound = f"{rng.randint(1, 2)}.{rng.randint(0, 2)}.{rng.randint(0, 2)}"
                    requires[dep] = f"{op}{bound}"
            reg.add_version(name, v, requires)
    return reg


import random

rng = random.Random(0)
mismatches = 0
for _ in range(2000):
    names = list("ABCDE")[:rng.randint(2, 5)]
    registry = random_registry(rng, names)
    root = names[0]
    got = resolve(registry, root)
    expected_sat = brute_force_satisfiable(registry, root)
    if expected_sat:
        mismatches += got is None or is_valid_order(registry, root, got) is not True
    else:
        mismatches += got is not None
assert mismatches == 0
```

</details>

</details>
