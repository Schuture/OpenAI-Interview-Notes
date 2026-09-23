# Sharded Matmul: Forward, Backward, Bug Hunt

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Derivation, coding and debugging · NumPy / PyTorch | ★☆☆☆☆ | Hard | MLE · RE | linear-algebra, parallelism, autograd, numpy, pytorch, debugging | 3 parts |
<!-- meta:end -->

## Problem

Let $X$ have shape `(B, d_in)`, $W$ have shape `(d_in, d_out)`, and $Y = XW$ have shape `(B, d_out)`. A
*device* is one entry of a Python list holding a NumPy array; the whole computation still runs on a
single machine, and every exchange of data between devices goes through one of two explicit functions:

- `all_gather(shards, axis)`: `shards[k]` is device $k$'s piece of a logically single array, split
  along `axis`. Returns a list of length $n$ in which every entry is the same array, the concatenation
  of all the shards along `axis`.
- `all_reduce(shards)`: `shards[k]` is device $k$'s own array, all of the same shape, each holding a
  partial contribution to a sum. Returns a list of length $n$ in which every entry is the same array,
  the elementwise sum of all the shards.

A *shard* of a matrix is a contiguous slice along one of its axes, assigned to one device. In
*column-parallel* sharding, $W$ is split along its output axis (`axis=1`, size `d_out`) into shards
$W_0, \dots, W_{n-1}$, and every device holds a full copy of $X$. In *row-parallel* sharding, $W$ is
split along its input axis (`axis=0`, size `d_in`) into shards $W_0, \dots, W_{n-1}$, and $X$ is split
along its own feature axis (also size `d_in`) to match, so device $k$ holds only $X_k$, the columns of
$X$ that line up with the rows of $W_k$. When the length of the axis being split is not divisible by
$n$, the remainder is spread one entry at a time over the first shards: with `d_out = 7` and $n = 3$
devices the column widths are $3, 2, 2$, so device 0's shard of $W$ has shape `(d_in, 3)` and devices 1
and 2 have shape `(d_in, 2)`. The sizes here are small — `B`, `d_in` and `d_out` at most 50, entries
within $\pm 100$ — and $n$ never exceeds the length of the axis being split, so no device ends up with
an empty shard.

### Part 1 — Forward and backward by hand

For **column-parallel** sharding, state what device $k$ computes in the forward pass and how the full
$Y$ is assembled. Then, given the upstream gradient $\bar Y = \partial L / \partial Y$ (the full array,
identical on every device), derive $\bar W_k = \partial L / \partial W_k$ and $\bar X = \partial L /
\partial X$ for each device, and say at which step, if any, communication is needed and of which kind.
Do the same for **row-parallel** sharding.

### Part 2 — Implement the sharded layer

Implement `all_gather`, `all_reduce`, and the forward and backward pass of both sharding schemes:

```py
def all_gather(shards: list, axis: int) -> list: ...
def all_reduce(shards: list) -> list: ...

def column_parallel_forward(X, W_shards: list) -> list:
    """X: (B, d_in), a full copy on every device. W_shards[k]: (d_in, d_out_k).
    Returns Y_shards[k]: (B, d_out_k), device k's own shard of Y (not gathered)."""

def column_parallel_backward(X, W_shards: list, dY_shards: list) -> tuple:
    """dY_shards[k]: (B, d_out_k), dL/dY restricted to device k's columns.
    Returns (dW_shards, dX_shards)."""

def row_parallel_forward(X_shards: list, W_shards: list) -> list:
    """X_shards[k]: (B, d_in_k). W_shards[k]: (d_in_k, d_out).
    Returns Y_shards[k]: (B, d_out), the full Y, identical on every device."""

def row_parallel_backward(X_shards: list, W_shards: list, dY) -> tuple:
    """dY: (B, d_out), identical on every device. Returns (dW_shards, dX_shards)."""
```

Shard $W$, and for row-parallel also $X$, with `np.array_split` so that `d_out` or `d_in` need not be
divisible by $n$. Verify both schemes, forward and backward, against an unsharded NumPy reference and
against PyTorch autograd, in `float64`, with `np.allclose`; include at least one case where the split is
uneven.

### Part 3 — Debug a sharded MLP

The file below implements a two-layer MLP split across $n$ devices: layer 1 is a column-parallel Linear
from `d_in` to `d_hidden` followed by `tanh`, layer 2 is a row-parallel Linear from `d_hidden` to
`d_out`, and the loss is the mean squared error against a target. `check_gradients` compares the sharded
forward and backward pass against an unsharded NumPy reference built from the same weights, and returns
the maximum absolute error of $Y$ and of each of the three gradients.

The file contains 5 bugs, each independent of the others: fixing one does not require touching the
others, and each has its own effect on `check_gradients`. Find and fix all 5; for each, say where it is
and why it produces the effect you observe. Once all 5 are fixed, `check_gradients()` returns errors
below `1e-8` for every one of $Y$, `dW1`, `dW2`, `dX`, for any random seed.

```python
import numpy as np

B, D_IN, D_HIDDEN, D_OUT, N = 5, 4, 7, 3, 3   # NOTE: D_HIDDEN is not divisible by N


def all_gather(shards, axis):
    full = np.concatenate(shards, axis=axis)
    return [full for _ in shards]


def all_reduce(shards):
    total = sum(shards)
    return [total for _ in shards]


def shard_columns(A, n):
    return np.array_split(A, n, axis=1)


def shard_rows(A, n):
    chunk = A.shape[0] // n
    return [A[i * chunk:(i + 1) * chunk] for i in range(n)]


def layer1_forward(X, W1_shards):
    Z1_shards = [X @ W1k for W1k in W1_shards]
    H_shards = [np.tanh(Z1k) for Z1k in Z1_shards]
    return Z1_shards, H_shards


def layer1_backward(X, W1_shards, Z1_shards, H_shards, dH_shards):
    dZ1_shards = [dHk * (1 - Z1k ** 2) for dHk, Z1k in zip(dH_shards, Z1_shards)]
    dW1_shards = [dZ1k.T @ X for dZ1k in dZ1_shards]
    dX_shards = [dZ1k @ W1k.T for dZ1k, W1k in zip(dZ1_shards, W1_shards)]
    return dW1_shards, dX_shards


def layer2_forward(H_shards, W2_shards):
    Y_partial = [Hk @ W2k for Hk, W2k in zip(H_shards, W2_shards)]
    return Y_partial


def layer2_backward(H_shards, W2_shards, dY):
    dW2_shards = [Hk.T @ dY for Hk in H_shards]
    dH_shards = [dY @ W2k.T for W2k in W2_shards]
    return dW2_shards, dH_shards


def mse_loss_and_grad(Y, target):
    diff = Y - target
    loss = np.mean(diff ** 2)
    dY = 2 * diff / diff.size
    return loss, dY


def check_gradients(seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((B, D_IN))
    W1 = rng.standard_normal((D_IN, D_HIDDEN)) * 0.5
    W2 = rng.standard_normal((D_HIDDEN, D_OUT)) * 0.5
    target = rng.standard_normal((B, D_OUT))
    W1_shards = shard_columns(W1, N)
    W2_shards = shard_rows(W2, N)

    Z1_shards, H_shards = layer1_forward(X, W1_shards)
    Y_shards = layer2_forward(H_shards, W2_shards)
    Y = Y_shards[0]
    loss, dY = mse_loss_and_grad(Y, target)
    dW2_shards, dH_shards = layer2_backward(H_shards, W2_shards, dY)
    dW1_shards, dX_shards = layer1_backward(X, W1_shards, Z1_shards, H_shards, dH_shards)

    W1_full = all_gather(W1_shards, axis=1)[0]
    W2_full = all_gather(W2_shards, axis=0)[0]
    Z1 = X @ W1_full
    H = np.tanh(Z1)
    Y_ref = H @ W2_full
    loss_ref, dY_ref = mse_loss_and_grad(Y_ref, target)
    dW2_ref = H.T @ dY_ref
    dH_ref = dY_ref @ W2_full.T
    dZ1_ref = dH_ref * (1 - H ** 2)
    dW1_ref = X.T @ dZ1_ref
    dX_ref = dZ1_ref @ W1_full.T

    return {
        "Y": np.abs(Y - Y_ref).max(),
        "dW1": np.abs(np.concatenate(dW1_shards, axis=1) - dW1_ref).max(),
        "dW2": np.abs(np.concatenate(dW2_shards, axis=0) - dW2_ref).max(),
        "dX": np.abs(dX_shards[0] - dX_ref).max(),
    }


if __name__ == "__main__":
    print(check_gradients())
```

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two things worth confirming with the interviewer: which axis of $W$ is split first, and whether $X$
starts out replicated or already sharded (the derivation below is symmetric either way, only the
transposes move to the other side). Writing `all_gather` and `all_reduce` as two separate functions, so
that every exchange of data goes through one of them and nowhere else, is what makes shape-tracing in
Part 3 possible.

### Part 1

Write $\bar A = \partial L / \partial A$ for any array $A$.

**Column-parallel.** Device $k$ holds $W_k$, the $k$-th block of columns of $W$, shape
`(d_in, d_out_k)`, and a full copy of $X$.

$$Y_k = X W_k \quad (B \times d_{out,k}), \qquad Y = \operatorname{all\_gather}_{\mathrm{axis}=1}(Y_0, \dots, Y_{n-1}).$$

No communication is needed to produce $Y_k$ itself; the gather is only needed where the full $Y$ must
live on every device. Slice the given $\bar Y$ locally into $\bar Y_k$ (device $k$'s columns) and apply
the product rule to $Y_k = X W_k$:

$$\bar W_k = X^\top \bar Y_k \quad \text{(local)}, \qquad \bar X = \sum_k \bar Y_k W_k^\top = \operatorname{all\_reduce}\bigl(\bar Y_k W_k^\top\bigr).$$

$X$ feeds every device's local product, so its gradient is a sum over devices — an all-reduce.

**Row-parallel.** Device $k$ holds $W_k$, the $k$-th block of rows of $W$, shape `(d_in_k, d_out)`, and
$X_k$, the matching block of columns of $X$, shape `(B, d_in_k)`.

$$Y_k = X_k W_k \quad \text{(a partial sum, shape } B \times d_{out}\text{)}, \qquad Y = \sum_k Y_k = \operatorname{all\_reduce}(Y_0, \dots, Y_{n-1}).$$

Here $Y_k$ already has the right shape but is only part of the answer, so the forward pass itself needs
an all-reduce. Given the full $\bar Y$, identical on every device once that reduction has run:

$$\bar W_k = X_k^\top \bar Y \quad \text{(local)}, \qquad \bar X_k = \bar Y W_k^\top \quad \text{(local; device } k\text{'s own shard of } \bar X\text{)}.$$

Both gradients are local: $X_k$ and $W_k$ are each used by exactly one device, so nothing needs
combining.

### Part 2

```python
import numpy as np


def all_gather(shards, axis):
    """shards[k]: device k's piece of the full array along `axis`. Returns, for every device, the
    same fully assembled array."""
    full = np.concatenate(shards, axis=axis)
    return [full for _ in shards]


def all_reduce(shards):
    """shards[k]: device k's partial sum, all the same shape. Returns, for every device, the same
    elementwise sum across all the shards."""
    total = sum(shards)        # NOTE: given only a gather, this is a gather on a fresh axis plus a local sum
    return [total for _ in shards]


def column_parallel_forward(X, W_shards):
    return [X @ Wk for Wk in W_shards]              # NOTE: X is replicated; no communication here


def column_parallel_backward(X, W_shards, dY_shards):
    dW_shards = [X.T @ dYk for dYk in dY_shards]                       # local
    dX_partial = [dYk @ Wk.T for dYk, Wk in zip(dY_shards, W_shards)]
    return dW_shards, all_reduce(dX_partial)                           # NOTE: sum over devices


def row_parallel_forward(X_shards, W_shards):
    Y_partial = [Xk @ Wk for Xk, Wk in zip(X_shards, W_shards)]
    return all_reduce(Y_partial)                     # NOTE: forward itself needs a reduction


def row_parallel_backward(X_shards, W_shards, dY):
    dW_shards = [Xk.T @ dY for Xk in X_shards]        # local
    dX_shards = [dY @ Wk.T for Wk in W_shards]        # local
    return dW_shards, dX_shards
```

Sharding uses `np.array_split(A, n, axis=...)`, which spreads a non-divisible size as evenly as
possible (widths $3, 2, 2$ for `d_out = 7`, $n = 3$); calling it on $X$'s feature axis with the same $n$
for row-parallel guarantees $X_k$ and $W_k$ agree on `d_in_k`. The checks at the end confirm both
schemes against an unsharded reference and against `torch.autograd`, in `float64`, for even and uneven
splits alike.

### Part 3

The rows follow the order in which the bugs surface: each output is what `check_gradients()` prints once the
bugs of the rows above it are fixed.

| Already fixed | Output of `check_gradients()` | Points to |
| --- | --- | --- |
| nothing | `ValueError: matmul: ... (size 2 is different from 3)`, raised in `layer2_forward` | `shard_rows` cuts at other boundaries than `shard_columns` |
| row 1 | `ValueError: ... along dimension 0, the array at index 0 has size 3 and the array at index 1 has size 2`, raised where `dW1_shards` are concatenated | the transpose in `dW1` is swapped |
| rows 1–2 | errors `Y` 1.01, `dW1` 0.50, `dW2` 0.20, `dX` 0.28 | the forward result is already wrong: `layer2_forward` lacks its all-reduce |
| rows 1–3 | `Y` and `dW2` exact to `1e-16`; `dW1` 0.77, `dX` 0.31 | only what passes through `layer1_backward` is wrong: the activation derivative |
| rows 1–4 | `Y`, `dW1`, `dW2` exact; `dX` 0.29 | $\bar X$ alone is wrong: nothing sums it across devices |
| all five | all four errors at most `1e-16` | — |

**Shard boundaries disagree.** `shard_columns` uses `np.array_split`, giving hidden-dimension widths
$3, 2, 2$ for `D_HIDDEN = 7`, $n = 3$. `shard_rows`, used for $W_2$, instead floor-divides
($7 \mathbin{//} 3 = 2$) into fixed chunks of 2, covering only 6 of the 7 rows and never matching
$W_1$'s column boundaries. Device 0's $H_0$ has 3 columns from $W_1$'s split, but $W_{2,0}$ has only 2
rows from the mismatched split, so $H_0 @ W_{2,0}$ fails on its first call, inside the row-parallel
forward pass.

```py
def shard_rows(A, n):
    return np.array_split(A, n, axis=0)      # same split function as shard_columns, only the axis differs
```

**Transpose swapped.** For $Y = AB$, $\bar B = A^\top \bar Y$; here $Y_k = X W_{1,k}$, so
$\bar W_{1,k} = X^\top \bar Z_{1,k}$, shape `(d_in, hidden_k)`. The buggy $\bar Z_{1,k}^\top X$ computes
the transpose of that, shape `(hidden_k, d_in)`. The three `hidden_k` widths are unequal (3, 2, 2), so
concatenating the three wrongly-shaped pieces along `axis=1` fails outright, catching the bug with a
shape error instead of silently producing a wrong-shaped `dW1`.

```py
dW1_shards = [X.T @ dZ1k for dZ1k in dZ1_shards]     # (d_in, hidden_k), matches W1_shards[k]
```

**Missing all-reduce.** Row-parallel forward computes only a partial sum $Y_k = H_k W_{2,k}$ per device;
$Y = \sum_k Y_k$ needs summing across devices, exactly what `all_reduce` does. Skipping it leaves each
device with just its own term, roughly $1/n$ of $Y$ in magnitude, and every downstream quantity — $\bar
Y$, both weight gradients, $\bar X$ — inherits the same error, since all are computed from this wrong
$Y$. Shapes match, so nothing raises.

```py
def layer2_forward(H_shards, W2_shards):
    Y_partial = [Hk @ W2k for Hk, W2k in zip(H_shards, W2_shards)]
    return all_reduce(Y_partial)      # row-parallel forward: sum the partial products across devices
```

**Activation gradient uses the wrong tensor.** `layer1_backward` computes
$\bar Z_1 = \bar H \odot \tanh'(Z_1)$. The correct derivative $\tanh'(z) = 1 - \tanh(z)^2 = 1 - h^2$ is a
function of the *output* $h$, not of the pre-activation $z$; the buggy line uses $z$ in place of $h$,
giving $1 - z^2$ wherever $z \ne h$, i.e. everywhere `tanh` actually bends the input. Both arrays have
shape `(B, hidden_k)`, so nothing raises: `dZ1` is silently wrong, corrupting `dW1` and `dX`, while $Y$
and $\bar W_2$ stay exact since neither depends on this line. With `relu` in place of `tanh` this
particular slip would be invisible — `z > 0` and `h > 0` are the same mask — and the error that bites
there instead is writing the derivative as the activation itself, `np.where(z > 0, z, 0)`, which scales
the gradient by $z$ rather than masking it.

```py
dZ1_shards = [dHk * (1 - Hk ** 2) for dHk, Hk in zip(dH_shards, H_shards)]   # tanh'(z) = 1 - h^2, h = tanh(z)
```

**The input gradient is never summed.** Every device multiplies the same $X$, so $X$ reaches the loss
through all $n$ local products and its gradient is a sum over them,
$\bar X = \sum_k \bar Z_{1,k} W_{1,k}^\top$: whatever the forward pass replicates or gathers, the
backward pass has to sum back up. Returning the list of local products leaves device $k$ with a single
one of those $n$ terms; every array keeps its shape `(B, d_in)`, so nothing raises, and $Y$, $\bar W_1$
and $\bar W_2$, none of which read $\bar X$, stay exact.

```py
dX_partial = [dZ1k @ W1k.T for dZ1k, W1k in zip(dZ1_shards, W1_shards)]
dX_shards = all_reduce(dX_partial)      # X is replicated, so its gradient is summed across devices
```

### Follow-ups

- With layer 1 column-parallel and layer 2 row-parallel, layer 1's output is already sharded along
  `d_hidden`, and an elementwise activation preserves that sharding exactly as layer 2 expects it — no
  communication happens between the two layers.
- One `all_reduce` in the forward pass (layer 2's sum) and one in the backward pass (layer 1's `dX`
  sum); everything else in this MLP is local.
- A bias is sharded like the weight it follows: column-parallel splits $b$ the same way as $W$'s columns
  and adds it locally; row-parallel adds the (unsplit) bias once after the forward `all_reduce`, or adds
  $b / n$ on every device before it, to avoid counting it $n$ times.
- In a ring implementation every device sends about $2(n-1)/n$ times the array size for an all-reduce and
  $(n-1)/n$ times for an all-gather: more devices shrink each device's computation, but hardly its traffic.
- A non-elementwise activation (softmax over `d_hidden`, say) would need the full pre-activation row on
  every device, turning the free lunch between the two layers into an extra `all_gather`.

<details>
<summary>Checks (runnable)</summary>

```python
def check(B, d_in, d_out, n, seed):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((B, d_in))
    W = rng.standard_normal((d_in, d_out))
    G = rng.standard_normal((B, d_out))                          # upstream gradient dL/dY

    Y_ref = X @ W
    dW_ref = X.T @ G
    dX_ref = G @ W.T

    W_shards = np.array_split(W, n, axis=1)
    Y_full = all_gather(column_parallel_forward(X, W_shards), axis=1)[0]
    dW_shards, dX_shards = column_parallel_backward(X, W_shards, np.array_split(G, n, axis=1))
    assert np.allclose(Y_full, Y_ref)
    assert np.allclose(np.concatenate(dW_shards, axis=1), dW_ref)
    assert np.allclose(dX_shards[0], dX_ref)

    X_shards, W_shards = np.array_split(X, n, axis=1), np.array_split(W, n, axis=0)
    Y_full = row_parallel_forward(X_shards, W_shards)[0]
    dW_shards, dX_shards = row_parallel_backward(X_shards, W_shards, G)
    assert np.allclose(Y_full, Y_ref)
    assert np.allclose(np.concatenate(dW_shards, axis=0), dW_ref)
    for dXk, dXk_ref in zip(dX_shards, np.array_split(dX_ref, n, axis=1)):
        assert np.allclose(dXk, dXk_ref)

    import torch
    Xt, Wt = torch.tensor(X, requires_grad=True), torch.tensor(W, requires_grad=True)
    (Xt @ Wt).backward(torch.tensor(G))
    assert np.allclose(Wt.grad.numpy(), dW_ref) and np.allclose(Xt.grad.numpy(), dX_ref)


for (B, d_in, d_out, n) in [(5, 4, 6, 3), (5, 4, 7, 3), (8, 9, 5, 4)]:   # last two are not divisible by n
    check(B, d_in, d_out, n, seed=0)
print("Part 2: column- and row-parallel forward/backward match the reference and torch autograd")
```

```python
import numpy as np

B, D_IN, D_HIDDEN, D_OUT, N = 5, 4, 7, 3, 3   # hidden width not divisible by the shard count


def all_gather(shards, axis):
    full = np.concatenate(shards, axis=axis)
    return [full for _ in shards]


def all_reduce(shards):
    total = sum(shards)
    return [total for _ in shards]


def shard_columns(A, n):
    return np.array_split(A, n, axis=1)


def shard_rows(A, n):
    return np.array_split(A, n, axis=0)          # bug 4 fix: same split function as shard_columns


def layer1_forward(X, W1_shards):
    Z1_shards = [X @ W1k for W1k in W1_shards]
    H_shards = [np.tanh(Z1k) for Z1k in Z1_shards]
    return Z1_shards, H_shards


def layer1_backward(X, W1_shards, Z1_shards, H_shards, dH_shards):
    dZ1_shards = [dHk * (1 - Hk ** 2) for dHk, Hk in zip(dH_shards, H_shards)]   # bug 1 fix: use H, not Z1
    dW1_shards = [X.T @ dZ1k for dZ1k in dZ1_shards]                            # bug 2 fix: X.T @ dZ1k
    dX_partial = [dZ1k @ W1k.T for dZ1k, W1k in zip(dZ1_shards, W1_shards)]
    dX_shards = all_reduce(dX_partial)      # bug 5 fix: X is replicated, so its gradient is summed
    return dW1_shards, dX_shards


def layer2_forward(H_shards, W2_shards):
    Y_partial = [Hk @ W2k for Hk, W2k in zip(H_shards, W2_shards)]
    return all_reduce(Y_partial)                 # bug 3 fix: sum the partial products


def layer2_backward(H_shards, W2_shards, dY):
    dW2_shards = [Hk.T @ dY for Hk in H_shards]
    dH_shards = [dY @ W2k.T for W2k in W2_shards]
    return dW2_shards, dH_shards


def mse_loss_and_grad(Y, target):
    diff = Y - target
    loss = np.mean(diff ** 2)
    dY = 2 * diff / diff.size
    return loss, dY


def check_gradients(seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((B, D_IN))
    W1 = rng.standard_normal((D_IN, D_HIDDEN)) * 0.5
    W2 = rng.standard_normal((D_HIDDEN, D_OUT)) * 0.5
    target = rng.standard_normal((B, D_OUT))
    W1_shards = shard_columns(W1, N)
    W2_shards = shard_rows(W2, N)

    Z1_shards, H_shards = layer1_forward(X, W1_shards)
    Y_shards = layer2_forward(H_shards, W2_shards)
    Y = Y_shards[0]
    loss, dY = mse_loss_and_grad(Y, target)
    dW2_shards, dH_shards = layer2_backward(H_shards, W2_shards, dY)
    dW1_shards, dX_shards = layer1_backward(X, W1_shards, Z1_shards, H_shards, dH_shards)

    W1_full = all_gather(W1_shards, axis=1)[0]   # W1 was split by columns, so it is gathered along axis=1
    W2_full = all_gather(W2_shards, axis=0)[0]
    Z1 = X @ W1_full
    H = np.tanh(Z1)
    Y_ref = H @ W2_full
    loss_ref, dY_ref = mse_loss_and_grad(Y_ref, target)
    dW2_ref = H.T @ dY_ref
    dH_ref = dY_ref @ W2_full.T
    dZ1_ref = dH_ref * (1 - H ** 2)
    dW1_ref = X.T @ dZ1_ref
    dX_ref = dZ1_ref @ W1_full.T

    return {
        "Y": np.abs(Y - Y_ref).max(),
        "dW1": np.abs(np.concatenate(dW1_shards, axis=1) - dW1_ref).max(),
        "dW2": np.abs(np.concatenate(dW2_shards, axis=0) - dW2_ref).max(),
        "dX": np.abs(dX_shards[0] - dX_ref).max(),
    }


if __name__ == "__main__":
    print(check_gradients())
```

```python
errs = check_gradients()
assert all(v < 1e-8 for v in errs.values()), errs
print("clean check_gradients():", {k: float(v) for k, v in errs.items()})


def reference(X, W1, W2, target):
    Z1 = X @ W1
    H = np.tanh(Z1)
    Y = H @ W2
    loss, dY = mse_loss_and_grad(Y, target)
    dW2 = H.T @ dY
    dH = dY @ W2.T
    dZ1 = dH * (1 - H ** 2)
    dW1 = X.T @ dZ1
    dX = dZ1 @ W1.T
    return Y, dW1, dW2, dX


def run_with_one_bug(bug, seed=0):
    """The fixed pipeline with exactly one step swapped back to its buggy form."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((B, D_IN))
    W1 = rng.standard_normal((D_IN, D_HIDDEN)) * 0.5
    W2 = rng.standard_normal((D_HIDDEN, D_OUT)) * 0.5
    target = rng.standard_normal((B, D_OUT))
    Y_ref, dW1_ref, dW2_ref, dX_ref = reference(X, W1, W2, target)

    W1_shards = shard_columns(W1, N)
    if bug == "boundary":
        chunk = D_HIDDEN // N
        W2_shards = [W2[i * chunk:(i + 1) * chunk] for i in range(N)]
    else:
        W2_shards = shard_rows(W2, N)

    Z1_shards, H_shards = layer1_forward(X, W1_shards)
    Y_partial = [Hk @ W2k for Hk, W2k in zip(H_shards, W2_shards)]
    Y_shards = Y_partial if bug == "aggregation" else all_reduce(Y_partial)
    Y = Y_shards[0]
    _, dY = mse_loss_and_grad(Y, target)
    dW2_shards, dH_shards = layer2_backward(H_shards, W2_shards, dY)

    if bug == "activation":
        dZ1_shards = [dHk * (1 - Z1k ** 2) for dHk, Z1k in zip(dH_shards, Z1_shards)]
    else:
        dZ1_shards = [dHk * (1 - Hk ** 2) for dHk, Hk in zip(dH_shards, H_shards)]
    if bug == "transpose":
        dW1_shards = [dZ1k.T @ X for dZ1k in dZ1_shards]
    else:
        dW1_shards = [X.T @ dZ1k for dZ1k in dZ1_shards]
    dX_partial = [dZ1k @ W1k.T for dZ1k, W1k in zip(dZ1_shards, W1_shards)]
    dX_shards = dX_partial if bug == "input-grad" else all_reduce(dX_partial)

    dW1 = np.concatenate(dW1_shards, axis=1)
    dW2 = np.concatenate(dW2_shards, axis=0)
    return {
        "Y": float(np.abs(Y - Y_ref).max()),
        "dW1": float(np.abs(dW1 - dW1_ref).max()),
        "dW2": float(np.abs(dW2 - dW2_ref).max()),
        "dX": float(np.abs(dX_shards[0] - dX_ref).max()),
    }


e = run_with_one_bug("aggregation")                              # NOTE: shapes match, so nothing raises
assert e["Y"] > 0.5 and e["dW1"] > 0.1 and e["dX"] > 0.1, e
print("aggregation bug alone:", e)

e = run_with_one_bug("activation")                                # NOTE: Y and dW2 stay exact
assert e["Y"] < 1e-8 and e["dW2"] < 1e-8 and e["dW1"] > 0.5 and e["dX"] > 0.1, e
print("activation bug alone:", e)

e = run_with_one_bug("input-grad")                                # NOTE: only dX is wrong, and only by a sum
assert e["Y"] < 1e-8 and e["dW1"] < 1e-8 and e["dW2"] < 1e-8 and e["dX"] > 0.1, e
print("missing backward reduction alone:", e)

try:
    run_with_one_bug("transpose")
    raise AssertionError("expected a ValueError")
except ValueError as err:
    print("transpose bug alone:", err)
    assert "dimension 0" in str(err) and "size 3" in str(err) and "size 2" in str(err)

try:
    run_with_one_bug("boundary")
    raise AssertionError("expected a ValueError")
except ValueError as err:
    print("boundary bug alone:", err)
    assert "matmul" in str(err) and "size 2 is different from 3" in str(err)

z = np.linspace(-2.0, 2.0, 9)                                     # the relu remark of the activation bug
assert np.array_equal(z > 0, np.maximum(z, 0) > 0)                # the mask is the same from z or from h
assert not np.array_equal(np.where(z > 0, z, 0), (z > 0).astype(float))     # relu itself is not its derivative
print("relu: mask(z) == mask(h), and relu(z) != relu'(z)")
```

</details>

</details>
