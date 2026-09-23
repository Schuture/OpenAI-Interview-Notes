# 流式熵计算

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程（含数学推导）· NumPy | ★★★☆☆ | 中等 | RS · RE · MLE | numerical-stability, softmax, streaming | 4 个部分 / 60 分钟 |
<!-- meta:end -->

## 题目

`logits` 是形状为 `(N,)` 的一维浮点数组，每个元素都是有限值，$N \ge 1$。记 $x$ 为 `logits`，
$p = \mathrm{softmax}(x)$，

$$p_i = \frac{e^{x_i}}{\sum_{k=0}^{N-1} e^{x_k}}, \qquad i = 0, \dots, N-1,$$

它的*香农熵*（Shannon entropy）定义为 $H(p) = -\sum_i p_i \log p_i$，其中 $\log$ 全文都指自然对数。每个 $p_i \in (0, 1]$，
所以 $H(p) \ge 0$；下面每一问都返回这个非负值，而不是原始的和 $\sum_i p_i \log p_i$（它是 $\le 0$ 的）。
用 NumPy 完成下面四个部分。

### Part 1 —— 直接计算熵

按定义直接计算 $H(p)$：取指数、归一化、求和。

```py
def softmax_entropy(logits: np.ndarray) -> float:
    """logits: shape (N,) float array, N >= 1, every entry finite. Returns H(softmax(logits))."""
```

对 `logits = [0.5, 2.5, -1.0]`，函数返回约 `0.4761`。

### Part 2 —— 数值稳定的熵

在某些输入上 Part 1 无法使用：

```py
softmax_entropy(np.array([1000.0, 1002.0, 998.0]))
# nan
```

实现 `softmax_entropy_stable(logits)`：只要 Part 1 不失败，两者结果在浮点误差范围内应当相同；
对任意有限输入都要返回有限且正确的值，包括上面这个例子（结果约为 `0.4411`）。实现必须做到：
(a) 在调用 `np.exp` 之前先减去最大的 logit；(b) 把 $\log p_i$ 写成居中形式
$(x_i - m) - \log \sum_k e^{x_k - m}$（其中 $m = \max_k x_k$），而不是写成
$\log\bigl(e^{x_i} / \sum_k e^{x_k}\bigr)$。

```py
def softmax_entropy_stable(logits: np.ndarray) -> float:
    """Same contract as softmax_entropy, correct and finite for every finite input."""
```

### Part 3 —— 固定大小的分块计算熵，额外空间 O(1)

这里的“额外空间 O(1)”是指代码不能分配任何大小依赖于 $N$ 的数组——尤其不能有长度为 $N$ 的概率向量。
把 `logits` 切成连续的、大小固定为 `block_size` 的片段（例如 `2`，不要求整除 $N$，所以最后一段可能更短），
片段之间只保留固定数量的标量。整个数组是现成可用的，可以不止读一遍。

```py
def softmax_entropy_blockwise(logits: np.ndarray, block_size: int = 2) -> float:
    """Same contract as softmax_entropy_stable, using O(1) extra space for a fixed block_size."""
```

对 `logits = [1.5, -2.0, 4.0, -0.5, 3.0]`、`block_size = 2`，三个切片依次是 `[1.5, -2.0]`、
`[4.0, -0.5]`、`[3.0]`，函数返回约 `0.8168`。

### Part 4 —— 单遍在线计算熵

现在 `logits` 不再是一整个数组，而是一段一段到来的序列——例如来自一个生成器——每一段只能读一次：
后一段到来后，前一段就不能再看了。实现 `softmax_entropy_online(blocks)`，同样要求额外空间 O(1)，
只消费 `blocks` 一遍，返回全部片段拼接起来的熵。

```py
def softmax_entropy_online(blocks) -> float:
    """blocks: an iterable of 1-D float arrays, the logits split into chunks of any length, consumed
    once, in order. Returns the same value as softmax_entropy_stable on their concatenation."""
```

用与 Part 3 相同的三个切片、依次到来，函数同样返回约 `0.8168`。

## 参考解答

<details>
<summary>展开参考解答</summary>

值得跟面试官确认的一点：累加是否必须始终用 `float64`，不论输入本身的 dtype 是什么（下面按此假设——
`float32` 会改变重缩放的精度，见最后一条追问）；`block_size` 是整次调用固定不变，还是可以逐段变化
（Part 4 的写法两者都能处理）。

### Part 1

```python
import numpy as np


def softmax_entropy(logits):
    x = np.asarray(logits, dtype=np.float64)
    exp_x = np.exp(x)                       # NOTE: np.exp(1000.0) is inf, with a RuntimeWarning
                                             #       "overflow encountered in exp"
    p = exp_x / np.sum(exp_x)               # NOTE: once exp_x holds an inf, p is inf / inf = nan
                                             #       ("invalid value encountered in divide")
    return float(-np.sum(p * np.log(p)))    # NOTE: even without overflow, a p_i that underflows to
                                             #       exactly 0.0 makes log(p_i) = -inf ("divide by zero
                                             #       encountered in log"), and 0.0 * -inf is nan too
                                             #       ("invalid value encountered in multiply")
```

### Part 2

记 $Z = \sum_k e^{x_k}$，则 $p_i = e^{x_i}/Z$，$\log p_i = x_i - \log Z$。提出最大的指数
$m = \max_k x_k$：由 $e^{x_i} = e^m e^{x_i - m}$，

$$Z = e^m s, \qquad \log Z = m + \log s, \qquad s = \sum_k e^{x_k - m}.$$

每个指数 $x_k - m$ 都 $\le 0$，取到最大值的那一项恰好是 $0$，所以 $s$ 的每一项都落在 $(0, 1]$ 内，
且 $s \ge 1$：无论 $x$ 有多大或跨度多宽，这个和都不会溢出，也不会消失为零。这就是先减去 $m$
再取指数的原因。

把 $\log p_i$ 写成 $(x_i - m) - \log s$，从头到尾都没有对一个概率调用 `log`——它只对 $s$ 取对数，
而 $s$ 恒为有限值且 $\ge 1$（代码里把它存成 `total`）。先算出 $p_i$ 再调用 `np.log` 是不同的做法：
当 $x_i - m$ 很负时，
$p_i = e^{x_i - m}/s$ 可能恰好下溢为 `0.0`，而 `np.log(0.0)` 是 `-inf`，与 Part 1 里的失败方式一样。
居中形式绕开了这个问题，因为 $p_i$ 本身要到之后才由 `np.exp(log_p_i)` 算出；即便这一步下溢为 `0.0`，
它与 `log_p_i` 相乘也只是 `0.0` 乘一个有限数，不是 `0.0` 乘 `-inf`。

```python
def log_softmax_stable(logits):
    x = np.asarray(logits, dtype=np.float64)
    m = np.max(x)
    shifted = x - m                          # NOTE: shifted <= 0 everywhere, so np.exp below never overflows
    total = np.exp(shifted).sum()
    return shifted - np.log(total)           # NOTE: never calls log on a value that could be 0


def softmax_entropy_stable(logits):
    log_p = log_softmax_stable(logits)
    p = np.exp(log_p)                        # NOTE: p can still underflow to exactly 0.0 here, but log_p
                                              #       stays finite, so p * log_p below is 0.0 * finite, not nan
    return float(-np.sum(p * log_p))
```

### Part 3

分块的两问共用一个恒等式。把 $\log p_i = x_i - \log Z$ 代入 $H$ 的定义，并用 $\sum_i p_i = 1$：

$$H(p) = -\sum_i p_i(x_i - \log Z) = \log Z - \sum_i p_i x_i.$$

所以 $H$ 只需要 $\log Z$ 和 logits 按概率加权的和，两者都不需要先算出 $p$。用 Part 2 里的 $m$、$s$，
有 $\log Z = m + \log s$。第二项代入 $x_i = m + (x_i - m)$，再除以 $Z = e^m s$：

$$\sum_i p_i x_i = \frac{1}{Z}\sum_i e^{x_i} x_i = \frac{1}{s}\sum_i e^{x_i - m}\bigl(m + (x_i - m)\bigr)
= m + \frac{u}{s}, \qquad u = \sum_i e^{x_i - m}(x_i - m).$$

两项一起代入 $H$，$m$ 正好抵消：

$$H(p) = \log s - \frac{u}{s}.$$

$s$ 和 $u$ 都是对 $i$ 的求和，一旦 $m$ 已知，就可以逐块累加。第一遍扫描各块得到 $m$；第二遍把 $s$、$u$
一起累加——不需要第三遍，因为 $u/s$ 已经是 logits 按概率加权的均值，从头到尾都没有单独算出某个 $p_i$。

```python
def _chunks(x, block_size):
    for start in range(0, x.shape[0], block_size):
        yield x[start:start + block_size]                      # NOTE: at most block_size elements live at
                                                                 #       once; no array of size N is ever built


def softmax_entropy_blockwise(logits, block_size=2):
    x = np.asarray(logits, dtype=np.float64)

    m = -np.inf
    for chunk in _chunks(x, block_size):          # pass 1: the global maximum
        m = max(m, float(np.max(chunk)))

    s = u = 0.0
    for chunk in _chunks(x, block_size):           # pass 2: s and u together, given m
        shifted = chunk - m
        w = np.exp(shifted)
        s += float(np.sum(w))
        u += float(np.sum(w * shifted))

    return float(np.log(s) - u / s)
```

### Part 4

每一段都能算出自己局部的 $(m, s, u)$，算法与 Part 3 相同，只是相对于它自己的最大值。要把已经处理过的
三元组 $(m_0, s_0, u_0)$ 与新一段的三元组 $(m_1, s_1, u_1)$ 合并成相对于 $m = \max(m_0, m_1)$ 的一个三元组，
需要把每个和都重新居中到 $m$ 上。对 $s$：对已经居中在 $m_0$ 上的那些项，
$\sum e^{x_k - m} = \sum e^{x_k - m_0} e^{m_0 - m} = s_0 e^{m_0 - m}$，居中在 $m_1$ 上的那些项同理，
于是 $s = s_0 e^{m_0 - m} + s_1 e^{m_1 - m}$。

对 $u$，记 $\delta = m_0 - m \le 0$，代入 $x_k - m = (x_k - m_0) + \delta$：

$$\sum_k e^{x_k - m}(x_k - m) = e^{\delta}\sum_k e^{x_k - m_0}\bigl((x_k - m_0) + \delta\bigr)
= e^{\delta}\bigl(u_0 + \delta s_0\bigr),$$

居中在 $m_1$ 上的那些项同理。把新一段折叠进当前累加值，做的正是这个合并；最后的三元组按 Part 3
的公式给出 $H$。

```python
def _centered_stats(x):
    m = float(np.max(x))
    shifted = x - m
    w = np.exp(shifted)
    return m, float(np.sum(w)), float(np.sum(w * shifted))


def _fold(acc, chunk):
    m0, s0, u0 = acc
    m1, s1, u1 = chunk
    if s0 == 0.0:                 # NOTE: acc is still the empty accumulator (m0 = -inf). Without this guard,
        return chunk               #       exp(m0 - m) is 0.0 and s0 * (m0 - m) is 0.0 * -inf = nan below
    m = max(m0, m1)
    a, b = np.exp(m0 - m), np.exp(m1 - m)
    s = s0 * a + s1 * b
    u = (u0 + s0 * (m0 - m)) * a + (u1 + s1 * (m1 - m)) * b
    return m, s, u


def softmax_entropy_online(blocks):
    acc = (-np.inf, 0.0, 0.0)
    for block in blocks:
        acc = _fold(acc, _centered_stats(np.asarray(block, dtype=np.float64)))
    m, s, u = acc
    return float(np.log(s) - u / s)
```

### 追问

- 整个数组都在内存里时（Part 3），两遍扫描比单遍在线（Part 4）更简单，额外空间同样是 O(1)；
  只有数据确实无法回头重读时，才需要 Part 4 的重缩放。
- `_fold` 里的重缩放，正是 online softmax / FlashAttention 背后的同一个递推：那里逐块折叠的是一个输出向量、
  配一个 running max，而不是这里的两个标量 `s` 和 `u`。
- 对形状为 `(B, N)` 的一批序列，把标量 `m, s, u` 换成形状 `(B,)` 的数组，每次归约都加上
  `axis=-1, keepdims=True`，每一块的形状相应变成 `(B, block_size)`。
- 用 `float32` 时，折叠进许多量级相差很大的块之后，`s` 和 `u` 会损失精度；即使 `logits` 本身是
  `float32`，累加器也要保留 `float64`。

<details>
<summary>验证代码（可运行）</summary>

```python
from scipy.special import softmax as reference_softmax
from scipy.stats import entropy as reference_entropy


def iter_blocks(x, block_size):
    for start in range(0, len(x), block_size):
        yield x[start:start + block_size]


assert round(softmax_entropy(np.array([0.5, 2.5, -1.0])), 4) == 0.4761
assert round(softmax_entropy_stable(np.array([1000.0, 1002.0, 998.0])), 4) == 0.4411
example = np.array([1.5, -2.0, 4.0, -0.5, 3.0])
assert round(softmax_entropy_blockwise(example, block_size=2), 4) == 0.8168
assert round(softmax_entropy_online(iter_blocks(example, block_size=2)), 4) == 0.8168

rng = np.random.default_rng(0)
cases = [
    np.array([0.5, 2.5, -1.0]),
    np.array([1000.0, 1002.0, 998.0]),
    np.array([0.0, -800.0, -900.0]),
    np.array([3.0]),
    example,
    np.array([1e6, 1e6, 1e6]),
    rng.normal(size=7),
    rng.normal(scale=500.0, size=9),
    rng.normal(scale=1e4, size=11),
]
for x in cases:
    reference = reference_entropy(reference_softmax(x))
    assert np.allclose(softmax_entropy_stable(x), reference, atol=1e-9)
    for block_size in (1, 2, 3, 4, len(x) + 5):               # block_size need not divide len(x)
        assert np.allclose(softmax_entropy_blockwise(x, block_size), reference, atol=1e-9)
        assert np.allclose(softmax_entropy_online(iter_blocks(x, block_size)), reference, atol=1e-9)
    assert np.allclose(softmax_entropy_online([x]), softmax_entropy_stable(x), atol=1e-12)  # one big chunk
    mid = len(x) // 2                                          # chunks of different lengths in one stream
    chunks = [c for c in (x[:mid], x[mid:mid + 1], x[mid + 1:]) if len(c)]
    assert np.allclose(softmax_entropy_online(chunks), reference, atol=1e-9)

mild = np.array([0.5, 2.5, -1.0, 1.5])                          # Part 1 only agrees away from over/underflow
assert np.allclose(softmax_entropy(mild), softmax_entropy_stable(mild))
with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
    assert np.isnan(softmax_entropy(np.array([1000.0, 1002.0, 998.0])))    # overflow -> inf / inf
    assert np.isnan(softmax_entropy(np.array([0.0, -800.0, -900.0])))      # underflow -> 0.0 * log(0.0)
```

</details>

</details>
