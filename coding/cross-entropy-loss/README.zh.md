# 从零实现交叉熵损失

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程（含 ML 概念问答）· NumPy | ★☆☆☆☆ | 中等 | MLE · RE | numpy, numerical-stability, loss-functions, kl-divergence | 4 个部分 |
<!-- meta:end -->

## 题目

`logits` 是形状为 `(B, T, V)` 的浮点数组：对 `B` 个序列中的每一个、序列里 `T` 个位置中的每一个，
它给出语言模型在 `V` 个词表类别上的未归一化得分。`targets` 是形状为 `(B, T)` 的整数数组，
`targets[b, t]` 是该位置正确类别的下标，是 $[0, V)$ 内的整数。
记 $z = \text{logits}[b, t] \in \mathbb{R}^V$，$\operatorname{softmax}(z)_i = e^{z_i} / \sum_k e^{z_k}$。
一个位置上的*交叉熵损失*（cross-entropy loss）是模型分配给正确类别的负对数概率：

$$\ell(b, t) = -\log \operatorname{softmax}(z)_{y}, \qquad y = \text{targets}[b, t].$$

用 NumPy 完成下面四个部分。

### Part 1 —— 数值稳定的交叉熵

实现 `cross_entropy(logits, targets)`，返回 $\ell(b, t)$ 在全部 $B \times T$ 个位置上的均值。
对大小达到 `1000.0` 的 logits，函数也必须返回有限且正确的值。从下面的骨架开始写：

```python
import numpy as np


def cross_entropy(logits: np.ndarray, targets: np.ndarray) -> float:
    """logits: shape (B, T, V) float array of per-position class scores. targets: shape (B, T) int
    array, each entry a class id in [0, V). Returns the mean of -log softmax(logits)[b, t, targets[b, t]]
    over all B * T positions. Must stay finite and correct for logits as large as 1000."""
    raise NotImplementedError
```

例子，取 $B = 1$、$T = 2$、$V = 3$：

```text
logits  = [[[2.0, 1.0, 0.1],
            [0.0, 0.0, 5.0]]]
targets = [[0, 2]]
```

`cross_entropy(logits, targets)` 返回约 `0.2152`。

### Part 2 —— 用 mask 排除部分位置

`mask` 是形状为 `(B, T)` 的数组，元素是 `0`/`1` 整数或布尔值；`mask[b, t] == 0` 标记一个不参与损失计算的位置——
例如批次里较短序列末尾的 padding。在这样的位置上，`targets[b, t]` 可以是任意整数，包括 $[0, V)$ 之外的值，
且不能被读取。实现 `cross_entropy_masked(logits, targets, mask)`：$\ell(b, t)$ 的均值现在只除以 `mask == 1`
的位置个数，而不是 $B \times T$。如果全部位置都被 mask，返回 `0.0`。

```py
def cross_entropy_masked(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray) -> float:
    """Same contract as cross_entropy, except positions with mask == 0 (shape (B, T), 0/1 or bool) are
    excluded from both the sum and the count in the mean. targets at a masked position may be any
    integer, including a value outside [0, V). Returns 0.0 when every position is masked."""
```

例子，在 Part 1 的例子上扩展出第三个位置，把它 mask 掉，并故意让它的 target 越界：

```text
logits  = [[[2.0, 1.0, 0.1],
            [0.0, 0.0, 5.0],
            [1.0, 1.0, 1.0]]]
targets = [[0, 2, 7]]
mask    = [[1, 1, 0]]
```

`cross_entropy_masked(logits, targets, mask)` 返回与 Part 1 相同的 `0.2152`，因为第三个位置不计入。

### Part 3 —— 标签平滑

有了*标签平滑*（label smoothing）之后，未被 mask 的位置上使用的目标分布不再是集中在 `targets[b, t]` 上的
one-hot 分布（把全部概率质量放在类别 $y$ 上的分布），而是

$$p = (1 - \varepsilon) \cdot \text{one-hot}(y) + \frac{\varepsilon}{V} \mathbf{1}, \qquad y = \text{targets}[b, t],$$

其中 $\varepsilon \in [0, 1)$ 就是 `label_smoothing`，$\mathbf{1} \in \mathbb{R}^V$ 是全 1 向量。
该位置上的损失从 $-\log \operatorname{softmax}(z)_y$ 变为 $-\sum_v p_v \log \operatorname{softmax}(z)_v$。
实现 `cross_entropy_smoothed(logits, targets, mask, label_smoothing)`，mask 的约定与 Part 2 相同；
`label_smoothing = 0.0` 时必须与 `cross_entropy_masked` 的结果完全一致。

```py
def cross_entropy_smoothed(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray,
                            label_smoothing: float) -> float:
    """Same contract as cross_entropy_masked, plus label smoothing with parameter label_smoothing = eps:
    the target distribution at an unmasked position is (1 - eps) * one_hot(targets[b, t]) + eps / V."""
```

对 Part 2 的例子取 `label_smoothing = 0.2`，`cross_entropy_smoothed` 返回约 `0.6452`。

### Part 4 —— 交叉熵、KL 散度与梯度

固定一个位置 $(b, t)$，记 $p$ 为该处使用的目标分布（Part 1–2 里是 one-hot，Part 3 里是平滑后的分布），
$q = \operatorname{softmax}(z)$ 为模型的预测分布，于是 $\ell(b, t) = H(p, q) = -\sum_v p_v \log q_v$。

**(a)** 推导 $H(p, q) = H(p) + \mathrm{KL}(p \Vert q)$，其中 $H(p) = -\sum_v p_v \log p_v$ 是 $p$ 的熵，
$\mathrm{KL}(p \Vert q) = \sum_v p_v \log(p_v / q_v)$ 是 KL 散度。用这个恒等式说明：当目标是 one-hot 时，
对 `logits` 最小化损失，等价于恰好在最小化 $\mathrm{KL}(p \Vert q)$。

**(b)** 加入标签平滑（$\varepsilon > 0$）之后，给出 $H(p)$ 的闭式表达式，并说明该位置上 Part 3 的
损失无论 `logits` 怎么取都不可能低于哪个值。用数值核对这个下界。

**(c)** 对 Part 3 的损失推导 $\partial \ell(b, t) / \partial z$（当 `label_smoothing = 0` 且没有位置被 mask 时，
它就退化为 Part 1 的梯度），并实现 `cross_entropy_grad`，返回均值损失对 `logits` 每个元素的梯度，
包括 mask 和除以未屏蔽位置数带来的影响。

```py
def cross_entropy_grad(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray,
                        label_smoothing: float) -> np.ndarray:
    """Gradient of cross_entropy_smoothed(logits, targets, mask, label_smoothing) with respect to
    logits, shape (B, T, V). The gradient row at a masked position is all zero."""
```

用中心有限差分和自动微分两种方式核对结果。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前有两点值得确认：全部位置都被 mask 时返回 `0.0` 是一个选择——
`torch.nn.functional.cross_entropy(..., reduction='mean')` 在同样的情况下返回 `nan`（`0 / 0`）；
标签平滑把 $\varepsilon$ 均匀分给全部 $V$ 个类别（含目标类自己），
而非只分给其余 $V - 1$ 个类别——PyTorch 的 `label_smoothing` 参数用的是前一种约定。

### Part 1

记 $z = \text{logits}[b, t]$、$y = \text{targets}[b, t]$、$m = \max_v z_v$。由 $e^{z_v} = e^m e^{z_v - m}$，

$$\log \sum_v e^{z_v} = m + \log \sum_v e^{z_v - m}.$$

每个指数 $z_v - m$ 都 $\le 0$，取最大值的那一项恰好为 $0$，右边的和因此总落在 $[1, V]$ 内，
不论 $z$ 的量级：既不会溢出，也不会下溢为零。$\ell = -(z_y - m) + \log \sum_v e^{z_v - m}$，
从头到尾没有对一个概率调用 `log`，只对这个有界的和取了一次对数。

```python
import numpy as np


def cross_entropy(logits, targets):
    x = np.asarray(logits, dtype=np.float64)
    y = np.asarray(targets)
    m = x.max(axis=-1, keepdims=True)                        # NOTE: keepdims=True, else `x - m` below
    shifted = x - m                                           #       broadcasts along the wrong axis when T == V
    log_z = np.log(np.exp(shifted).sum(axis=-1)) + m[..., 0]  # (B, T), always finite: shifted <= 0 everywhere
    picked = np.take_along_axis(x, y[..., None], axis=-1)[..., 0]   # (B, T), logits at the target class
    nll = log_z - picked   # NOTE: this is (z_y - m) - log sum_v exp(z_v - m); never softmax(x) followed by log(.)
    return float(nll.mean())
```

### Part 2

在 Part 1 的基础上有两处变化。第一，`mask == 0` 的位置要从求和与均值的分母里一起去掉，分母是
`mask == 1` 的位置个数，没有这样的位置时结果取 `0.0`。第二，被 mask 位置的 target 不会用于索引：gather 前先换成
一个无害的占位类别，之后统一把这些位置的损失乘以 `0`。

```python
def cross_entropy_masked(logits, targets, mask):
    x = np.asarray(logits, dtype=np.float64)
    keep = np.asarray(mask).astype(bool)          # NOTE: mask may arrive as 0/1 ints; x[mask] would then do
                                                    #       FANCY indexing, not boolean masking
    safe_targets = np.where(keep, targets, 0)      # NOTE: dummy class 0 at masked slots, so the gather below
                                                     #       never reads an out-of-range target
    m = x.max(axis=-1, keepdims=True)
    shifted = x - m
    log_z = np.log(np.exp(shifted).sum(axis=-1)) + m[..., 0]
    picked = np.take_along_axis(x, safe_targets[..., None], axis=-1)[..., 0]
    nll = (log_z - picked) * keep                   # zero out masked positions before summing
    count = keep.sum()
    if count == 0:
        return 0.0
    return float(nll.sum() / count)                 # NOTE: "/" not "//" -- floor division would silently
                                                       #       truncate the loss to an integer
```

### Part 3

记 $q_v = \operatorname{softmax}(z)_v$，把 $p = (1 - \varepsilon)\,\text{one-hot}(y) + (\varepsilon / V)\mathbf{1}$
代入 $-\sum_v p_v \log q_v$，得到

$$-\sum_v p_v \log q_v = -(1 - \varepsilon) \log q_y - \frac{\varepsilon}{V} \sum_v \log q_v
= -(1 - \varepsilon) \log q_y - \varepsilon \cdot \overline{\log q},$$

其中 $\overline{\log q} = \frac{1}{V}\sum_v \log q_v$ 是 $\log q_v$ 在整个词表上的均值。
两项都能从 Part 1 已经算出的量得到（$\log q_y$ 就是 `nll` 取负），再加一次对
`shifted - log_sum_exp` 沿最后一个轴求均值；全程没有构造任何 $(B, T, V)$ 的目标张量。

```python
def cross_entropy_smoothed(logits, targets, mask, label_smoothing):
    x = np.asarray(logits, dtype=np.float64)
    V = x.shape[-1]
    keep = np.asarray(mask).astype(bool)
    safe_targets = np.where(keep, targets, 0)

    m = x.max(axis=-1, keepdims=True)
    shifted = x - m
    log_sum_exp = np.log(np.exp(shifted).sum(axis=-1))         # (B, T)
    log_z = log_sum_exp + m[..., 0]
    log_q_y = np.take_along_axis(x, safe_targets[..., None], axis=-1)[..., 0] - log_z   # log q at the target
    mean_log_q = shifted.mean(axis=-1) - log_sum_exp           # mean over v of log q_v; no (B, T, V) target tensor built
    eps = label_smoothing
    nll = -(1.0 - eps) * log_q_y - eps * mean_log_q
    nll = nll * keep
    count = keep.sum()
    if count == 0:
        return 0.0
    return float(nll.sum() / count)
```

在随机批次上，结果与 `torch.nn.functional.cross_entropy(..., ignore_index=-100, label_smoothing=eps, reduction='mean')`
一致（被 mask 的位置用 `ignore_index` 标记）。可见 PyTorch 的分母同样是未被忽略的位置个数，而不是 $B \times T$。

### Part 4

**(a)** 由 $-\log q_v = -\log p_v + \log(p_v / q_v)$，两边乘以 $p_v$ 再对 $v$ 求和，得到

$$H(p, q) = -\sum_v p_v \log q_v = -\sum_v p_v \log p_v + \sum_v p_v \log \frac{p_v}{q_v}
= H(p) + \mathrm{KL}(p \Vert q).$$

对 one-hot 的 $p$，$H(p)$ 恒为 $0$：$v = y$ 那一项是 $-1 \cdot \log 1 = 0$，其余每一项 $p_v = 0$。
$H(p)$ 不依赖 `logits`——只有 $q$ 依赖——所以 $\ell(b, t)$ 与 $\mathrm{KL}(p \Vert q)$ 其实是 `logits`
的同一个函数，只差常数 $0$。对 `logits` 最小化损失，就是在最小化 $\mathrm{KL}(p \Vert q)$。

**(b)** 加入标签平滑后，Part 3 的目标分布 $p$ 同样不依赖 `logits`，所以 $H(p)$ 仍是一个
不随 `logits` 变化的常数，只是这次是正的：

$$H(p) = -\Bigl[(1 - \varepsilon) + \tfrac{\varepsilon}{V}\Bigr] \log\Bigl[(1 - \varepsilon) + \tfrac{\varepsilon}{V}\Bigr]
- (V - 1) \cdot \frac{\varepsilon}{V} \log \frac{\varepsilon}{V}.$$

$\mathrm{KL}(p \Vert q) \ge 0$，等号当且仅当 $q = p$，而这是可以达到的：softmax 能取到任何全部为正的分布
（取 `logits = log(p)`，加任意常数不影响 softmax）。所以 $H(p)$ 恰好是该位置损失的下确界：one-hot 目标下
损失可以趋近但不会低于 `0`；加了平滑后不会低于 $H(p) > 0$。以 Part 3 的例子为例（$V = 3$、$\varepsilon = 0.2$、
目标类别 $0$），$H(p) \approx 0.4851$，低于 Part 3 例子里那组 `logits` 算出的 `0.6452`。

**(c)** 由 $\log q_j = z_j - \log \sum_k e^{z_k}$ 得 $\partial \log q_j / \partial z_i = \delta_{ij} - q_i$，于是

$$\frac{\partial H(p, q)}{\partial z_i} = -\sum_j p_j \frac{\partial \log q_j}{\partial z_i}
= -\sum_j p_j(\delta_{ij} - q_i) = -p_i + q_i \sum_j p_j = q_i - p_i,$$

这里用到 $\sum_j p_j = 1$。对 $N$ 个未被 mask 的位置取平均，会把每个位置的梯度都缩放 $1/N$；
被 mask 的位置贡献的是零向量。

```python
def cross_entropy_grad(logits, targets, mask, label_smoothing):
    x = np.asarray(logits, dtype=np.float64)
    V = x.shape[-1]
    keep = np.asarray(mask).astype(bool)
    safe_targets = np.where(keep, targets, 0)
    count = keep.sum()
    if count == 0:
        return np.zeros_like(x)

    m = x.max(axis=-1, keepdims=True)
    q = np.exp(x - m)
    q /= q.sum(axis=-1, keepdims=True)                          # q = softmax(x), shape (B, T, V)

    eps = label_smoothing
    p = np.full_like(x, eps / V)                                # p = target distribution
    np.put_along_axis(p, safe_targets[..., None], (1.0 - eps) + eps / V, axis=-1)
    grad = (q - p) / count                                      # NOTE: divide by count, matching the mean reduction
    grad *= keep[..., None]                                     # zero the gradient row of every masked position
    return grad
```

### 追问

- **为什么不是“乘 0 后除以 `B * T`”。** 两种做法只在没有位置被 mask 时相同；批次间 padding 比例不同时，
  除以 `B * T` 会让 padding 更多的批次有效梯度更小，而除以未屏蔽位置数能让每个真实 token 的贡献与旁边
  padding 多少无关。
- **按 token 平均与按序列平均。** 对全部未屏蔽 token 取平均，会让更长的序列占更大权重；先对每个序列分别
  求平均、再对这 $B$ 个数取平均，则每个序列权重相同，与长度无关。
- **`float16` 下的 log-sum-exp。** 减去最大值之后不再溢出（不减时 `float16` 的 `exp` 在 $z \approx 11.09$ 以上就溢出），
  但 $e^{z_v - m} < 6 \times 10^{-8}$ 的项会直接变成 `0`，12 附近相邻两个可表示的数相差约 `0.008`。
  所以混合精度训练里这一步通常转成 `float32` 计算。
- **标签平滑对校准的影响。** 损失下界从 `0` 变成 $H(p) > 0$ 后，训练不再需要把 `logits` 推向
  $\pm\infty$ 来让目标类别概率逼近 `1`，模型的置信度往往因此更贴近实际准确率。
- **与 `log_softmax` + `nll_loss` 的关系。** PyTorch 把 `nn.CrossEntropyLoss` 描述成 `LogSoftmax` 接
  `NLLLoss`；数值上 `cross_entropy(logits, y)` 与 `nll_loss(log_softmax(logits, dim=-1), y)` 在浮点
  精度内完全一致。

<details>
<summary>验证代码（可运行）</summary>

```python
import torch
import torch.nn.functional as F

logits_ex = np.array([[[2.0, 1.0, 0.1], [0.0, 0.0, 5.0], [1.0, 1.0, 1.0]]])
targets_ex = np.array([[0, 2, 7]])            # position 2's target is deliberately out of range
mask_ex = np.array([[1, 1, 0]])
assert round(cross_entropy(logits_ex[:, :2], np.array([[0, 2]])), 4) == 0.2152
assert round(cross_entropy_masked(logits_ex, targets_ex, mask_ex), 4) == 0.2152
assert round(cross_entropy_smoothed(logits_ex, targets_ex, mask_ex, 0.2), 4) == 0.6452
assert cross_entropy_smoothed(logits_ex, targets_ex, mask_ex, 0.0) == \
       cross_entropy_masked(logits_ex, targets_ex, mask_ex)


def torch_cross_entropy(logits, targets, mask=None, label_smoothing=0.0):
    B, T, V = logits.shape
    x = torch.tensor(logits.reshape(-1, V), dtype=torch.float64)
    y = targets.reshape(-1).copy()
    if mask is not None:
        y[mask.reshape(-1) == 0] = -100                 # PyTorch's convention for "skip this position"
    y = torch.tensor(y, dtype=torch.long)
    return F.cross_entropy(x, y, ignore_index=-100, label_smoothing=label_smoothing, reduction='mean').item()


rng = np.random.default_rng(0)
for _ in range(200):
    B, T, V = rng.integers(1, 4), rng.integers(1, 5), rng.integers(2, 6)
    logits = rng.normal(scale=4.0, size=(B, T, V))
    targets = rng.integers(0, V, size=(B, T))
    mask = rng.integers(0, 2, size=(B, T))
    eps = rng.uniform(0.0, 0.4)
    dirty_targets = np.where(mask == 0, -999, targets)   # exercise the "never read a masked target" contract
    assert np.allclose(cross_entropy(logits, targets), torch_cross_entropy(logits, targets), atol=1e-8)
    if mask.sum() > 0:
        assert np.allclose(cross_entropy_masked(logits, dirty_targets, mask),
                            torch_cross_entropy(logits, targets, mask), atol=1e-8)
        assert np.allclose(cross_entropy_smoothed(logits, dirty_targets, mask, eps),
                            torch_cross_entropy(logits, targets, mask, eps), atol=1e-7)

# overflow: a naive softmax-then-log implementation is nan here; cross_entropy stays finite and correct
big = np.array([[[1000.0, 0.0, -1000.0]]])
assert cross_entropy(big, np.array([[0]])) == 0.0
with np.errstate(over="ignore", invalid="ignore"):
    bad = np.exp(big[0, 0]) / np.exp(big[0, 0]).sum()
    assert np.isnan(-np.log(bad[0]))

# all-masked returns 0.0; torch returns nan for the same situation
zeros_mask = np.zeros((2, 3), dtype=int)
assert cross_entropy_masked(rng.normal(size=(2, 3, 4)), rng.integers(-9, 9, (2, 3)), zeros_mask) == 0.0
assert torch.isnan(F.cross_entropy(torch.randn(6, 4, dtype=torch.float64),
                                    torch.full((6,), -100, dtype=torch.long),
                                    ignore_index=-100, reduction='mean'))

# an int mask of 0/1 and a bool mask must agree: 0/1 ints must not be read as fancy indices
li = np.array([[[1.0, 2.0, 0.5]], [[0.2, -1.0, 3.0]]])
ti = np.array([[0], [2]])
assert cross_entropy_masked(li, ti, np.array([[1], [0]])) == \
       cross_entropy_masked(li, ti, np.array([[True], [False]]))

# Part 4(b): the label-smoothing lower bound, reached exactly at logits = log(target distribution)
V4, eps4, y4 = 3, 0.2, 0
q = np.full(V4, eps4 / V4)
q[y4] = (1 - eps4) + eps4 / V4
H_p = float(-(q * np.log(q)).sum())
assert round(H_p, 4) == 0.4851
achieved = cross_entropy_smoothed(np.log(q)[None, None, :], np.array([[y4]]), np.array([[1]]), eps4)
assert np.allclose(achieved, H_p, atol=1e-10)
assert cross_entropy_smoothed(logits_ex, targets_ex, mask_ex, eps4) > H_p     # a generic prediction sits above it


def numerical_grad(f, x, eps_fd=1e-6):
    # NOTE: eps_fd is tuned for float64; the same eps_fd in float32 loses ~4 orders of magnitude to
    # cancellation (checked below), so finite differences must run in float64 even if logits are float32
    g = np.zeros_like(x)
    it = np.nditer(x, flags=['multi_index'])
    for _ in it:
        idx = it.multi_index
        old = x[idx]
        x[idx] = old + eps_fd
        f_plus = f(x)
        x[idx] = old - eps_fd
        f_minus = f(x)
        x[idx] = old
        g[idx] = (f_plus - f_minus) / (2 * eps_fd)
    return g


for _ in range(5):
    B, T, V = 2, 2, 3
    logits = rng.normal(scale=1.5, size=(B, T, V))
    targets = rng.integers(0, V, size=(B, T))
    mask = rng.integers(0, 2, size=(B, T))
    if mask.sum() == 0:
        mask[0, 0] = 1
    eps = 0.15
    dirty_targets = np.where(mask == 0, -777, targets)

    grad_analytic = cross_entropy_grad(logits, dirty_targets, mask, eps)
    grad_fd = numerical_grad(lambda x: cross_entropy_smoothed(x, dirty_targets, mask, eps),
                              logits.astype(np.float64).copy())
    assert np.allclose(grad_analytic, grad_fd, atol=1e-6)

    xt = torch.tensor(logits.reshape(-1, V), dtype=torch.float64, requires_grad=True)
    yt = targets.reshape(-1).copy()
    yt[mask.reshape(-1) == 0] = -100
    loss = F.cross_entropy(xt, torch.tensor(yt, dtype=torch.long), ignore_index=-100,
                            label_smoothing=eps, reduction='mean')
    loss.backward()
    grad_torch = xt.grad.numpy().reshape(B, T, V)
    assert np.allclose(grad_analytic, grad_torch, atol=1e-8)

# float32 finite differences at the same eps_fd really do become unreliable
logits32 = rng.normal(scale=3.0, size=(1, 1, 6)).astype(np.float32)
g64 = numerical_grad(lambda x: cross_entropy_smoothed(x, np.array([[2]]), np.array([[1]]), 0.1),
                      logits32.astype(np.float64).copy(), eps_fd=1e-6)
g32 = numerical_grad(lambda x: cross_entropy_smoothed(x.astype(np.float64), np.array([[2]]), np.array([[1]]), 0.1),
                      logits32.astype(np.float32).copy(), eps_fd=1e-6)
assert np.abs(g32 - g64).max() > 1e-3          # float32 cancellation, not a tight match like the float64 check above
```

</details>

</details>
