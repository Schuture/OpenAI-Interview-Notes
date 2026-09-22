# Prefix Matmul: Autograd, Manual Backward, Hillis–Steele Scan

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding with derivation · PyTorch | ★★★★☆ | Hard | RS · RE · MLE | autograd, linear-algebra, parallel-scan, pytorch | 4 parts / 75 min |
<!-- meta:end -->

## Problem

`W` is a floating-point tensor of shape `(N, D, D)` with $N \ge 1$. It holds $N$ square matrices
$W_0, W_1, \dots, W_{N-1}$ of size $D \times D$, where `W[i]` is $W_i$. The $i$-th *prefix product* is
the product of the first $i + 1$ matrices, taken from left to right:

$$P_i = W_0 W_1 \cdots W_i, \qquad i = 0, 1, \dots, N-1,$$

so $P_0 = W_0$ and $P_i = P_{i-1} W_i$ for $i \ge 1$. The output is a tensor `P` of shape `(N, D, D)`
with `P[i]` equal to $P_i$. All $N$ prefix products are returned. For example, with $N = 3$ and $D = 2$:

```math
W_0 = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix},\qquad
W_1 = \begin{pmatrix} 2 & 0 \\ 0 & 1 \end{pmatrix},\qquad
W_2 = \begin{pmatrix} 1 & 0 \\ 3 & 1 \end{pmatrix}
```

```math
P_0 = W_0 = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix},\qquad
P_1 = P_0 W_1 = \begin{pmatrix} 2 & 1 \\ 0 & 1 \end{pmatrix},\qquad
P_2 = P_1 W_2 = \begin{pmatrix} 5 & 1 \\ 3 & 1 \end{pmatrix}
```

Implement the following four parts in PyTorch.

### Part 1 — Forward pass with indexed assignment

**(a)** Implement `prefix_products_inplace(W)`. Allocate the output with `P = torch.empty_like(W)` and
fill it in a `for` loop with `P[i] = P[i - 1] @ W[i]`. Indexed assignment overwrites the memory of the
existing tensor `P`. Operations of this kind are called *in-place* operations.

```py
def prefix_products_inplace(W: torch.Tensor) -> torch.Tensor:
    """W: float tensor of shape (N, D, D). Returns P of shape (N, D, D) with P[i] = W[0] @ ... @ W[i]."""
```

**(b)** PyTorch's automatic differentiation engine, *autograd*, records the operations applied to a
tensor created with `requires_grad=True`. When `loss.backward()` is called on a scalar `loss`, it
applies the chain rule backwards through the recorded operations and stores the gradient of `loss`
with respect to `W` in `W.grad`. Under autograd, the function from (a) fails:

```py
W = torch.randn(4, 3, 3, requires_grad=True)
P = prefix_products_inplace(W)      # the values in P are correct
loss = P.sum()
loss.backward()
# RuntimeError: one of the variables needed for gradient computation has been modified by an inplace operation
```

Explain why PyTorch raises this error.

### Part 2 — Forward pass that autograd can differentiate

Rewrite the function as `prefix_products(W)` without any in-place operation, so that the code of
Part 1(b) runs and `W.grad` holds the correct gradient.

### Part 3 — Backward pass by hand

Let $L$ be a scalar loss that depends on all the $P_i$. The *upstream gradient* $G_i = \partial L / \partial P_i$
is given. It has the same shape as $P_i$, and its entry $(a, b)$ is $\partial L / \partial (P_i)_{ab}$.
Without using autograd, derive a formula for $\partial L / \partial W_i$ and implement it:

```py
def prefix_products_backward(W: torch.Tensor, P: torch.Tensor, G: torch.Tensor) -> torch.Tensor:
    """W, P, G: shape (N, D, D). P is the forward output and G[i] = dL/dP[i].
    Returns dW of shape (N, D, D) with dW[i] = dL/dW[i]."""
```

Verify the result against the `W.grad` that autograd computes for the function of Part 2, or against
central finite differences $\bigl(L(W + \varepsilon E) - L(W - \varepsilon E)\bigr) / 2\varepsilon$, where
$E$ is 1 in a single entry and 0 elsewhere.

### Part 4 — Hillis–Steele parallel scan

The loop of Parts 1–3 performs $N - 1$ products one after another, because step $i$ needs the result of
step $i - 1$. Matrix multiplication is associative, so the same prefix products can be computed in
$\lceil \log_2 N \rceil$ rounds with the Hillis–Steele scan. Start from $x_i = W_i$. Round
$k = 0, 1, 2, \dots$ uses the stride $s = 2^k$ and is executed while $s < N$. In one round, simultaneously
for every $i \ge s$,

$$x_i \leftarrow x_{i-s}\, x_i ,$$

where the right-hand side uses the values from before the round, and the entries with $i < s$ stay
unchanged. After the last round $x_i = P_i$. The products inside one round do not depend on each other
and can run in parallel. For $N = 4$:

| | $x_0$ | $x_1$ | $x_2$ | $x_3$ |
| --- | --- | --- | --- | --- |
| start | $W_0$ | $W_1$ | $W_2$ | $W_3$ |
| after $s = 1$ | $W_0$ | $W_0 W_1$ | $W_1 W_2$ | $W_2 W_3$ |
| after $s = 2$ | $W_0$ | $W_0 W_1$ | $W_0 W_1 W_2$ | $W_0 W_1 W_2 W_3$ |

**(a)** Implement `scan_forward(W)`, which returns the same `P` as Part 2. Each round must be a single
batched matrix multiplication, with no Python loop over $i$.

**(b)** Derive and implement the backward pass of this scan: given `G`, return $\partial L / \partial W$
in $\lceil \log_2 N \rceil$ rounds.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two things to confirm with the interviewer before coding: whether "in place" means filling an output
tensor (assumed here) or overwriting `W` itself, and whether the products run left to right. The
opposite order moves every transpose below to the other side.

### Part 1

```python
import torch


def prefix_products_inplace(W):
    P = torch.empty_like(W)
    P[0] = W[0]
    for i in range(1, W.shape[0]):
        P[i] = P[i - 1] @ W[i]      # NOTE: P[i - 1] is a view of P, and this line writes into P
    return P
```

The backward pass of a product `A @ B` needs the values of `A` and `B`, so autograd keeps references
to them, called *saved tensors*. They are references, not copies. `P[i - 1]` is a *view*: a tensor that
shares its memory with `P`. Every tensor has a *version counter* that is incremented by each in-place
write, and a view shares the counter of the tensor it views. When `backward()` reads a saved tensor, it
compares the current counter with the value at the time of saving. The assignment `P[i] = ...` has
incremented the counter of `P` after `P[i - 1]` was saved, so the comparison fails and autograd raises
the error.

The check works per tensor, not per entry. In this loop the rows that were saved are never overwritten,
so the gradient would in fact have been correct, but autograd cannot know that and refuses rather than
risk returning a wrong gradient silently. If the loop overwrote `W[i]` itself, the old $W_i$ that the
backward pass needs would really be lost.

### Part 2

```python
def prefix_products(W):
    products = [W[0]]
    for i in range(1, W.shape[0]):
        products.append(products[-1] @ W[i])    # every product is a new tensor; nothing is overwritten
    return torch.stack(products)                # stack allocates a new (N, D, D) tensor and is differentiable
```

### Part 3

Write $\bar{X} = \partial L / \partial X$ for any matrix $X$. For a single product $Y = AB$ we have
$Y_{ab} = \sum_c A_{ac} B_{cb}$, so the chain rule gives
$\bar{A}_{ac} = \sum_b \bar{Y}_{ab} B_{cb}$ and $\bar{B}_{cb} = \sum_a A_{ac} \bar{Y}_{ab}$, that is

$$\bar{A} = \bar{Y} B^\top, \qquad \bar{B} = A^\top \bar{Y}.$$

In the forward pass $P_i$ is used twice: by the loss, which contributes $G_i$, and as the left factor of
$P_{i+1} = P_i W_{i+1}$. The total gradient $A_i$ arriving at $P_i$ is the sum of both contributions:

$$A_{N-1} = G_{N-1}, \qquad A_i = G_i + A_{i+1} W_{i+1}^\top .$$

$W_i$ is used once, as the right factor of $P_i = P_{i-1} W_i$, hence

$$\frac{\partial L}{\partial W_i} = P_{i-1}^\top A_i \quad (i \ge 1), \qquad \frac{\partial L}{\partial W_0} = A_0 .$$

One loop from $i = N - 1$ down to $0$ computes everything in $O(N D^3)$, the cost of the forward pass.

```python
def prefix_products_backward(W, P, G):
    dW = torch.empty_like(W)
    carry = torch.zeros_like(W[0])                          # holds A_i
    for i in reversed(range(W.shape[0])):
        carry = carry + G[i]                                # NOTE: a sum, because P[i] feeds the loss AND P[i+1]
        dW[i] = carry if i == 0 else P[i - 1].T @ carry     # NOTE: i == 0 has no left factor
        carry = carry @ W[i].T                              # the part of A_i that flows on to P[i-1]
    return dW
```

### Part 4

Forward. By induction, after the round with stride $s$, entry $i$ holds the product of the last
$\min(i + 1, 2s)$ matrices ending at index $i$: $x_{i-s}$ holds the block ending at $i - s$, $x_i$ holds
the adjacent block of $s$ matrices ending at $i$, and their product joins the two. After the last round
$2s \ge N$, so entry $i$ holds $P_i$.

```python
def scan_forward(W):
    """Returns (P, tape). tape[k] = (stride, input of round k), kept for the backward pass."""
    X, tape, stride = W, [], 1
    while stride < W.shape[0]:
        Y = X.clone()                               # NOTE: read from X, write to Y; never update X in place
        Y[stride:] = X[:-stride] @ X[stride:]       # NOTE: lower indices on the LEFT, matmul does not commute
        tape.append((stride, X))                    #       (diagonal test matrices would hide a swapped order)
        X, stride = Y, 2 * stride
    return X, tape
```

Backward. Undo the rounds from last to first. One round maps $X$ to $Y$ with $Y_j = X_j$ for $j < s$ and
$Y_j = X_{j-s} X_j$ for $j \ge s$. Given $H = \partial L / \partial Y$, entry $X_j$ receives one term for
each place where it is used, by the rule for a single product:

$$\bar{X}_j = \underbrace{H_j}_{j < s} + \underbrace{X_{j-s}^\top H_j}_{j \ge s} + \underbrace{H_{j+s} X_{j+s}^\top}_{j + s < N} .$$

```python
def scan_backward(tape, G):
    H = G
    for stride, X in reversed(tape):
        dX = torch.zeros_like(H)
        dX[:stride] += H[:stride]                                   # copied entries
        dX[stride:] += X[:-stride].transpose(1, 2) @ H[stride:]     # X_j as the right factor of Y_j
        dX[:-stride] += H[stride:] @ X[stride:].transpose(1, 2)     # X_j as the left factor of Y_{j+s}
        H = dX                                                      # NOTE: all three lines are +=, most entries
    return H                                                        #       are used twice in one round
```

The scan does $O(N \log N \cdot D^3)$ work instead of $O(N D^3)$, in $\lceil \log_2 N \rceil$ dependent
steps instead of $N$, and its tape stores $\lceil \log_2 N \rceil$ arrays of the size of `W`. It is
faster only when the products of a round really run in parallel.

### Follow-ups

- Package Part 3 as a `torch.autograd.Function`, so that autograd calls your `backward` (code below).
  Inside `forward` nothing is recorded, so indexed assignment is allowed there. If `forward` modifies
  one of its inputs in place, it must declare this with `ctx.mark_dirty`.
- Reduce the memory of the tape: recompute the rounds during the backward pass, or use the
  work-efficient scan of Blelloch, with $O(N)$ work in about $2 \log_2 N$ rounds.
- Where this is used: a linear recurrence $h_t = A_t h_{t-1} + b_t$ is a prefix scan over an associative
  operation on the pairs $(A_t, b_t)$, which is how linear recurrent networks and state-space models
  are trained in parallel along the sequence.

<details>
<summary>Checks and the torch.autograd.Function wrapper (runnable)</summary>

```python
class PrefixProducts(torch.autograd.Function):
    @staticmethod
    def forward(ctx, W):
        P = prefix_products_inplace(W)              # fine here: autograd records nothing inside forward()
        ctx.save_for_backward(W, P)
        return P

    @staticmethod
    def backward(ctx, G):
        W, P = ctx.saved_tensors
        return prefix_products_backward(W, P, G)


def numerical_gradient(f, W, eps=1e-6):
    grad = torch.zeros_like(W)
    for idx in torch.cartesian_prod(*[torch.arange(n) for n in W.shape]):
        E = torch.zeros_like(W)
        E[tuple(idx)] = eps
        grad[tuple(idx)] = (f(W + E) - f(W - E)) / (2 * eps)
    return grad


W_example = torch.tensor([[[1., 1.], [0., 1.]], [[2., 0.], [0., 1.]], [[1., 0.], [3., 1.]]])
assert torch.equal(prefix_products(W_example)[2], torch.tensor([[5., 1.], [3., 1.]]))

torch.manual_seed(0)
for N in (1, 2, 5, 8, 11):                                      # includes lengths that are not powers of two
    W = torch.randn(N, 3, 3, dtype=torch.float64, requires_grad=True)   # NOTE: float64; float32 is too coarse
    G = torch.randn(N, 3, 3, dtype=torch.float64)                       #       for finite differences / gradcheck
    loss = lambda W: (prefix_products(W) * G).sum()             # a loss whose upstream gradient is exactly G

    # Part 1: same values, but backward() raises
    assert torch.allclose(prefix_products_inplace(W), prefix_products(W))
    if N > 1:
        try:
            prefix_products_inplace(W).sum().backward()
            raise AssertionError("expected a RuntimeError")
        except RuntimeError as err:
            assert "modified by an inplace operation" in str(err)

    # Part 3: by hand == autograd == finite differences == custom Function
    (by_autograd,) = torch.autograd.grad(loss(W), W)
    Wd = W.detach()
    P = prefix_products(Wd)
    by_hand = prefix_products_backward(Wd, P, G)
    assert torch.allclose(by_hand, by_autograd)
    assert torch.allclose(by_hand, numerical_gradient(loss, Wd), atol=1e-6)
    (by_function,) = torch.autograd.grad((PrefixProducts.apply(W) * G).sum(), W)
    assert torch.allclose(by_function, by_autograd)

    # Part 4: the scan agrees with the loop, forward and backward
    P_scan, tape = scan_forward(Wd)
    assert torch.allclose(P_scan, P)
    assert torch.allclose(scan_backward(tape, G), by_hand)
    assert len(tape) == (N - 1).bit_length()                    # ceil(log2 N) rounds
assert torch.autograd.gradcheck(PrefixProducts.apply, (W,))
```

</details>

</details>
