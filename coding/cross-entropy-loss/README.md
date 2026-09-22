# Cross-Entropy Loss from Scratch

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding with ML concepts · NumPy | ★☆☆☆☆ | Medium | MLE · RE | numpy, numerical-stability, loss-functions, kl-divergence | 4 parts |
<!-- meta:end -->

## Problem

`logits` is a float array of shape `(B, T, V)`: the unnormalized scores a language model assigns to
`V` vocabulary classes, for each of `T` positions in each of `B` sequences. `targets` is an integer
array of shape `(B, T)`; `targets[b, t]` is the id of the correct class at that position, an integer in
`[0, V)`. Write $z = \text{logits}[b, t] \in \mathbb{R}^V$
and $\operatorname{softmax}(z)_i = e^{z_i} / \sum_k e^{z_k}$. The *cross-entropy loss* at one position
is the negative log-probability the model assigns to the correct class:

$$\ell(b, t) = -\log \operatorname{softmax}(z)_{y}, \qquad y = \text{targets}[b, t].$$

Complete the following four parts in NumPy.

### Part 1 — Numerically stable cross-entropy

Implement `cross_entropy(logits, targets)`, returning the mean of $\ell(b, t)$ over all $B \times T$
positions. The function must stay finite and correct for logits as large as `1000.0`. Start from this
skeleton:

```python
import numpy as np


def cross_entropy(logits: np.ndarray, targets: np.ndarray) -> float:
    """logits: shape (B, T, V) float array of per-position class scores. targets: shape (B, T) int
    array, each entry a class id in [0, V). Returns the mean of -log softmax(logits)[b, t, targets[b, t]]
    over all B * T positions. Must stay finite and correct for logits as large as 1000."""
    raise NotImplementedError
```

Example, with $B = 1$, $T = 2$, $V = 3$:

```text
logits  = [[[2.0, 1.0, 0.1],
            [0.0, 0.0, 5.0]]]
targets = [[0, 2]]
```

`cross_entropy(logits, targets)` returns approximately `0.2152`.

### Part 2 — Excluding positions with a mask

`mask` is an array of shape `(B, T)`, holding either `0`/`1` integers or booleans; `mask[b, t] == 0`
marks a position — for example padding at the end of a shorter sequence in the batch — that must not
contribute to the loss. At such a position `targets[b, t]` may hold any integer, including a value
outside `[0, V)`, and it must not be read. Implement `cross_entropy_masked(logits, targets, mask)`: the
mean of $\ell(b, t)$ now divides only by the number of positions with `mask == 1`, not by $B \times T$.
If every position is masked, return `0.0`.

```py
def cross_entropy_masked(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray) -> float:
    """Same contract as cross_entropy, except positions with mask == 0 (shape (B, T), 0/1 or bool) are
    excluded from both the sum and the count in the mean. targets at a masked position may be any
    integer, including a value outside [0, V). Returns 0.0 when every position is masked."""
```

Example, extending Part 1's example with a third, masked position whose target is deliberately out of
range:

```text
logits  = [[[2.0, 1.0, 0.1],
            [0.0, 0.0, 5.0],
            [1.0, 1.0, 1.0]]]
targets = [[0, 2, 7]]
mask    = [[1, 1, 0]]
```

`cross_entropy_masked(logits, targets, mask)` returns the same `0.2152` as Part 1, since the third
position does not count.

### Part 3 — Label smoothing

With *label smoothing*, the target distribution used at an unmasked position is no longer the one-hot
distribution on `targets[b, t]` (the distribution with all its mass on class $y$), but

$$p = (1 - \varepsilon) \cdot \text{one-hot}(y) + \frac{\varepsilon}{V} \mathbf{1}, \qquad y = \text{targets}[b, t],$$

where $\varepsilon \in [0, 1)$ is `label_smoothing` and $\mathbf{1} \in \mathbb{R}^V$ is the all-ones
vector. The loss at that position becomes $-\sum_v p_v \log \operatorname{softmax}(z)_v$ instead of
$-\log \operatorname{softmax}(z)_y$. Implement `cross_entropy_smoothed(logits, targets, mask,
label_smoothing)` with the same masking contract as Part 2; `label_smoothing = 0.0` must reproduce
`cross_entropy_masked` exactly.

```py
def cross_entropy_smoothed(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray,
                            label_smoothing: float) -> float:
    """Same contract as cross_entropy_masked, plus label smoothing with parameter label_smoothing = eps:
    the target distribution at an unmasked position is (1 - eps) * one_hot(targets[b, t]) + eps / V."""
```

On the example of Part 2 with `label_smoothing = 0.2`, `cross_entropy_smoothed` returns approximately
`0.6452`.

### Part 4 — Cross-entropy, KL divergence, and the gradient

Fix a position $(b, t)$ and write $p$ for the target distribution used there (one-hot in Parts 1–2, the
smoothed distribution of Part 3) and $q = \operatorname{softmax}(z)$ for the model's predicted
distribution, so that $\ell(b, t) = H(p, q) = -\sum_v p_v \log q_v$.

**(a)** Derive $H(p, q) = H(p) + \mathrm{KL}(p \Vert q)$, where $H(p) = -\sum_v p_v \log p_v$ is the
entropy of $p$ and $\mathrm{KL}(p \Vert q) = \sum_v p_v \log(p_v / q_v)$ is the KL divergence. Use the
identity to explain why, with one-hot targets, minimizing the loss over `logits` is exactly minimizing
$\mathrm{KL}(p \Vert q)$.

**(b)** With label smoothing ($\varepsilon > 0$), give a closed-form expression for $H(p)$ and state the
value the loss of Part 3 can no longer go below at that position, no matter how `logits` is chosen.
Check the bound numerically.

**(c)** Derive $\partial \ell(b, t) / \partial z$ for the loss of Part 3 (which reduces to Part 1's when
`label_smoothing = 0` and every position is unmasked), and implement `cross_entropy_grad`, returning the
gradient of the mean loss with respect to every entry of `logits`, including the effect of masking and
of dividing by the count of unmasked positions.

```py
def cross_entropy_grad(logits: np.ndarray, targets: np.ndarray, mask: np.ndarray,
                        label_smoothing: float) -> np.ndarray:
    """Gradient of cross_entropy_smoothed(logits, targets, mask, label_smoothing) with respect to
    logits, shape (B, T, V). The gradient row at a masked position is all zero."""
```

Verify the result against central finite differences and against automatic differentiation.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming before coding: returning `0.0` when every position is masked is a choice —
`torch.nn.functional.cross_entropy(..., reduction='mean')` returns `nan` (`0 / 0`) in that same situation;
and label smoothing here
spreads $\varepsilon$ over all $V$ classes, including the target class itself, rather than only over the
other $V - 1$ classes — both are choices, and PyTorch's `label_smoothing` argument follows the first one.

### Part 1

Write $z = \text{logits}[b, t]$, $y = \text{targets}[b, t]$, and $m = \max_v z_v$. Since
$e^{z_v} = e^m e^{z_v - m}$,

$$\log \sum_v e^{z_v} = m + \log \sum_v e^{z_v - m}.$$

Every exponent $z_v - m$ is $\le 0$ and the one at $v = \arg\max$ is exactly $0$, so the sum on the right
always lies in $[1, V]$, whatever the scale of $z$: it can neither overflow nor underflow to zero. The
loss is $\ell = -(z_y - m) + \log \sum_v e^{z_v - m}$, which never calls `log` on a probability — only on
this bounded sum.

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

Two changes on top of Part 1. First, positions with `mask == 0` are dropped from both the sum and the
count that forms the mean: the divisor is the number of positions with `mask == 1`, and the result is
`0.0` when there are none. Second, the target at a masked position is never used for indexing;
it is replaced with a harmless placeholder before the gather, and the corresponding loss value is
multiplied by `0` afterwards regardless of what it turned out to be.

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

Write $q_v = \operatorname{softmax}(z)_v$ and substitute
$p = (1 - \varepsilon)\,\text{one-hot}(y) + (\varepsilon / V)\mathbf{1}$ into $-\sum_v p_v \log q_v$:

$$-\sum_v p_v \log q_v = -(1 - \varepsilon) \log q_y - \frac{\varepsilon}{V} \sum_v \log q_v
= -(1 - \varepsilon) \log q_y - \varepsilon \cdot \overline{\log q},$$

where $\overline{\log q} = \frac{1}{V}\sum_v \log q_v$ is the plain mean of $\log q_v$ over the
vocabulary. Both terms come from quantities Part 1 already computes ($\log q_y$ is `nll` negated) plus
one extra mean over the last axis of `shifted - log_sum_exp`; no $(B, T, V)$ target tensor is ever built.

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

On random batches this matches `torch.nn.functional.cross_entropy(..., ignore_index=-100,
label_smoothing=eps, reduction='mean')` with the masked positions marked by `ignore_index`. PyTorch's
divisor is therefore also the count of non-ignored positions, not $B \times T$.

### Part 4

**(a)** Since $-\log q_v = -\log p_v + \log(p_v / q_v)$, multiplying by $p_v$ and summing over $v$ gives

$$H(p, q) = -\sum_v p_v \log q_v = -\sum_v p_v \log p_v + \sum_v p_v \log \frac{p_v}{q_v}
= H(p) + \mathrm{KL}(p \Vert q).$$

For a one-hot $p$, $H(p) = 0$ identically: the term at $v = y$ is $-1 \cdot \log 1 = 0$, and every other
term has $p_v = 0$. $H(p)$ does not depend on `logits` at all — only $q$ does — so $\ell(b, t) = H(p, q)$
and $\mathrm{KL}(p \Vert q)$ are literally the same function of `logits`, off by the constant $0$.
Minimizing the loss over `logits` is minimizing $\mathrm{KL}(p \Vert q)$.

**(b)** With label smoothing, the target $p$ of Part 3 still does not depend on `logits`, so
$H(p)$ is again a `logits`-independent constant, but now a positive one:

$$H(p) = -\Bigl[(1 - \varepsilon) + \tfrac{\varepsilon}{V}\Bigr] \log\Bigl[(1 - \varepsilon) + \tfrac{\varepsilon}{V}\Bigr]
- (V - 1) \cdot \frac{\varepsilon}{V} \log \frac{\varepsilon}{V}.$$

$\mathrm{KL}(p \Vert q) \ge 0$, with equality iff $q = p$, which is reachable because softmax can equal
any distribution with strictly positive entries (take `logits = log(p)`, up to an additive constant that
softmax cancels). So $H(p)$ is exactly the infimum of the loss at that position: with a one-hot target it
can approach but never go below `0`, and with smoothing it can never go below $H(p) > 0$. For the example
of Part 3 ($V = 3$, $\varepsilon = 0.2$, target class $0$), $H(p) \approx 0.4851$, below the `0.6452` that
Part 3's example computed for one particular choice of `logits`.

**(c)** Since $\log q_j = z_j - \log \sum_k e^{z_k}$, $\partial \log q_j / \partial z_i = \delta_{ij} -
q_i$. Then

$$\frac{\partial H(p, q)}{\partial z_i} = -\sum_j p_j \frac{\partial \log q_j}{\partial z_i}
= -\sum_j p_j(\delta_{ij} - q_i) = -p_i + q_i \sum_j p_j = q_i - p_i,$$

using $\sum_j p_j = 1$. Averaging over $N$ unmasked positions scales every one of their gradients by
$1/N$, and a masked position contributes the zero vector.

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

### Follow-ups

- **Why not scale by `0` and divide by `B * T` instead.** The two only agree when nothing is masked; once
  the fraction of masked positions varies across batches (different amounts of padding), dividing by
  `B * T` shrinks the effective gradient for batches with more padding, while dividing by the unmasked
  count keeps every real token's contribution the same size regardless of how much padding sits next to it.
- **Per-token vs. per-sequence averaging.** Averaging over every unmasked token, as above, gives longer
  sequences more total weight in the loss; averaging each sequence first and then averaging those $B$
  numbers gives every sequence equal weight regardless of its length.
- **`float16` and log-sum-exp.** Subtracting the maximum removes the overflow (`exp` in `float16` overflows
  above $z \approx 11.09$), but terms with $e^{z_v - m} < 6 \times 10^{-8}$ become `0` and values near 12 are
  spaced about `0.008` apart. Mixed-precision training therefore usually computes this step in `float32`.
- **Label smoothing and calibration.** Because the loss floor is $H(p) > 0$ rather than $0$, training no
  longer pushes `logits` towards $\pm\infty$ to drive the predicted probability of the target to `1`,
  which tends to make the model's confidence track its accuracy more closely.
- **Relation to `log_softmax` + `nll_loss`.** PyTorch documents `nn.CrossEntropyLoss` as `LogSoftmax`
  followed by `NLLLoss` in one step, and `cross_entropy(logits, y)` agrees with
  `nll_loss(log_softmax(logits, dim=-1), y)` to floating-point precision.

<details>
<summary>Checks (runnable)</summary>

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
