# PyTorch Code Reading & Extension

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Code reading · PyTorch | ★☆☆☆☆ | — | RE · MLE | code-reading, pytorch, complexity | 3 parts + bonus |
<!-- meta:end -->

## Problem

The file below trains a classifier whose labels come from several annotators instead of a single
ground truth. There are $N$ samples, each a feature vector in $\mathbb{R}^D$; the true class, in
$\lbrace 0, \dots, C-1 \rbrace$, is never seen during training. There are $A$ annotators, and their labels are
stored in an integer tensor `Y` of shape `(N, A)`: `Y[i, a]` is the class annotator `a` reported for sample
`i`, or `-1` if annotator `a` never labeled sample `i` (every sample has at least 2 labels). Each annotator `a` has a *confusion
matrix* $M_a \in \mathbb{R}^{C \times C}$: given that the true class is $c$, annotator `a` reports class
$o$ with probability $M_a[c, o]$, so row $c$ of $M_a$ sums to 1. A reliable annotator's $M_a$ is close to
the identity matrix; an unreliable one's is close to uniform in every row.

A small classifier, `Net`, maps `X` to class probabilities `p` of shape `(N, C)`. The confusion matrices
are a second set of learnable parameters, held by `CrowdLayer`. Training never looks at the true class:
for every observed pair `(i, a)`, the predicted distribution over what annotator `a` reports is
`p[i] @ M[a]`, and the loss is the negative log-likelihood of the label `a` actually reported.

```python
import time
import torch
import torch.nn as nn
import torch.nn.functional as F

N, D, C, A, H = 400, 10, 4, 5, 24
N_TEST = 200
K_RANGE = (2, 4)                            # each sample gets labeled by 2 or 3 annotators, chosen at random
RELIABILITY = [0.95, 0.8, 0.6, 0.4, 0.15]   # ground-truth diagonal of each annotator's confusion matrix

CENTERS = torch.randn(C, D, generator=torch.Generator().manual_seed(0)) * 2.0   # shared by every call

M_TRUE = torch.zeros(A, C, C)
for a in range(A):
    r = RELIABILITY[a]
    for c in range(C):
        row = torch.full((C,), (1 - r) / (C - 1))
        row[c] = r
        M_TRUE[a, c] = row


def make_data(seed, n=N):
    g = torch.Generator().manual_seed(seed)
    y = torch.randint(0, C, (n,), generator=g)
    X = CENTERS[y] + torch.randn(n, D, generator=g) * 0.8

    Y = torch.full((n, A), -1, dtype=torch.long)
    for i in range(n):
        k = torch.randint(K_RANGE[0], K_RANGE[1], (1,), generator=g).item()
        for a in torch.randperm(A, generator=g)[:k].tolist():
            Y[i, a] = torch.multinomial(M_TRUE[a, y[i]], 1, generator=g).item()
    return X, y, Y


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.l1 = nn.Linear(D, H)
        self.l2 = nn.Linear(H, C)

    def forward(self, x):
        return self.l2(F.relu(self.l1(x)))


class CrowdLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.logits = nn.Parameter(torch.eye(C).unsqueeze(0).repeat(A, 1, 1) * 2.0)

    def forward(self):
        return F.softmax(self.logits, dim=-1)


def nll_loop(p, M, Y):
    # p: class probabilities from the classifier. M: annotator confusion matrices. Y: observed labels.
    total = torch.zeros(())
    for i in range(Y.shape[0]):
        for a in range(Y.shape[1]):
            lab = Y[i, a].item()
            if lab < 0:
                continue
            q = p[i] @ M[a]
            total = total + -torch.log(q[lab] + 1e-8)
    return total


def raw_annotator_accuracy(Y, y):
    # how often each annotator's own label matches the true class, wherever they voted; only
    # computable offline for evaluation, since y is never seen during training
    acc = torch.zeros(A)
    for a in range(A):
        voted = Y[:, a] >= 0
        acc[a] = (Y[voted, a] == y[voted]).float().mean()
    return acc


def run(seed=0, epochs=25, lr=5e-2):
    torch.manual_seed(seed)                 # reseeds Net's and CrowdLayer's weight init too
    X, y, Y = make_data(seed)
    X_test, y_test, _ = make_data(seed + 1000, n=N_TEST)
    net, crowd = Net(), CrowdLayer()
    opt = torch.optim.Adam(list(net.parameters()) + list(crowd.parameters()), lr=lr)
    n_votes = (Y >= 0).sum().item()

    t_start = time.time()
    for ep in range(epochs):
        opt.zero_grad()
        p = F.softmax(net(X), dim=-1)
        M = crowd()
        loss = nll_loop(p, M, Y) / n_votes
        loss.backward()
        opt.step()
        with torch.no_grad():
            train_probs = F.softmax(net(X), dim=-1)          # recomputed for logging, not reused from p
            train_acc = (train_probs.argmax(-1) == y).float().mean().item()
        if ep % 5 == 0 or ep == epochs - 1:
            print(f"epoch {ep:2d}  loss {loss.item():.4f}  train_acc {train_acc:.3f}")
    train_seconds = time.time() - t_start

    with torch.no_grad():
        test_acc = (net(X_test).argmax(-1) == y_test).float().mean().item()
    print(f"test_acc {test_acc:.3f}  ({epochs} epochs, {train_seconds:.1f}s)")
    raw_acc = [round(v, 2) for v in raw_annotator_accuracy(Y, y).tolist()]
    print("raw annotator accuracy vs ground truth:", raw_acc)
    print("ground-truth annotator reliability:     ", RELIABILITY)
    return net, crowd, X, Y


torch.manual_seed(0)
net, crowd, X, Y = run()
```

Part 1 asks about the code above. Parts 2 and 3 extend and refactor it.

### Part 1 — Reading the code: data flow, shapes, and complexity

Answer the following, using $N, D, C, A, H$ for the constants the file defines and $P$ for
`(Y >= 0).sum()`, the number of observed (sample, annotator) pairs.

1. Trace the data from `X` to the update applied by `opt.step()`: which functions and tensors does it
   pass through, and at what point, if any, does `y` enter?
2. What are the shapes of `net(X)`, `p = F.softmax(net(X), dim=-1)`, and `crowd()`?
3. Inside `nll_loop`, `q = p[i] @ M[a]` is one matrix product. What are the shapes of its two operands?
   What is its time complexity, and how much memory does `q` occupy, in terms of $C$?
4. The matrix products inside `net.l1` and `net.l2` — what is the time complexity and forward-output
   memory of each, in terms of $N, D, H, C$? What extra tensors does the backward pass need to keep
   around?
5. What is the overall time complexity of `nll_loop`? Give a loose upper bound in terms of $N, A, C$,
   and a tighter one in terms of $P$.
6. `nll_loop` itself never materializes a tensor of size $O(N \cdot A \cdot C)$. If instead you computed
   `p[i] @ M[a]` for every $(i, a)$ pair at once with `einsum`, before masking out the missing ones, how
   much memory would that intermediate tensor use? Can this be avoided?
7. In one training step, how many multiply-adds does the forward pass of `net` do, compared to
   `nll_loop`? Which of the two actually takes longer to run, and why don't the two answers agree?

### Part 2 — Extension: annotator reliability from the learned confusion matrices

Add a method to `CrowdLayer` that estimates each annotator's reliability directly from its learned
confusion matrix, and a function that picks out the least reliable one. An annotator's reliability is
the average, over the $C$ classes, of the probability that it reports the true class:
$\frac{1}{C}\sum_c M_a[c, c]$. Implement `reliability` as a free function and attach it with
`CrowdLayer.reliability = reliability`.

```py
def reliability(self) -> torch.Tensor:
    """Attached as CrowdLayer.reliability. Returns r of shape (A,), r[a] in [0, 1]: the estimated
    reliability of annotator a, computed from self.forward(), the learned confusion matrices."""


def least_reliable(r: torch.Tensor) -> int:
    """r: (A,). Returns the index of the annotator with the lowest estimated reliability."""
```

The data above was generated with a fixed ground-truth reliability for every annotator, in
`RELIABILITY`; use it to check that `least_reliable` finds the right one.

### Part 3 — Refactor: vectorizing `nll_loop`

`nll_loop` computes the loss with a Python loop over every sample and, inside it, another loop over
every annotator. Rewrite it as `nll_vectorized`, with no Python loop over samples or annotators —
indexing, `gather`, `einsum`, or batched matrix multiplication (`torch.bmm`) — returning the same scalar
(up to floating-point error) as `nll_loop`, for any `p`, `M`, `Y` of matching shapes.

```py
def nll_vectorized(p: torch.Tensor, M: torch.Tensor, Y: torch.Tensor) -> torch.Tensor:
    """p: (N, C) class probabilities. M: (A, C, C) confusion matrices. Y: (N, A) observed labels,
    -1 for missing. Returns the same scalar as nll_loop(p, M, Y)."""
```

### Bonus — Complexity of three more operators

Answer the following without reference to the code above; give the conclusion and a one-line reason for
each.

1. Self-attention over a sequence of length $L$ with hidden dimension $d$, split into $h$ heads of
   dimension $d / h$ each. What is the time complexity of one forward pass? What term dominates the
   memory needed to run backward through it?
2. A 2D convolution layer: input $(B, C_{in}, H_{in}, W_{in})$, kernel $k \times k$, $C_{out}$ output
   channels, output spatial size $H_{out} \times W_{out}$. What is the time complexity of one forward
   pass?
3. Batched matrix multiplication `(B, n, m) @ (B, m, p)`: what is its time complexity, and how much
   memory does the output occupy?

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming with the interviewer: whether an annotator's reliability should be a single scalar
averaged over classes, as Part 2 defines it, or a full per-class breakdown. Read `run` once, top to bottom,
noting which tensors the optimizer updates and which are constants, before answering Part 1.

### Part 1

1. `make_data` builds `X` (`(N, D)`), the observed labels `Y` (`(N, A)`), and uses the fixed `M_TRUE`;
   `y`, the true class, only reappears afterwards in `train_acc` and `test_acc`, and never touches the
   loss. Inside `run`, `X` goes through `net` to logits, then `softmax` to `p` (`(N, C)`); `crowd()`
   produces `M` (`(A, C, C)`); `nll_loop(p, M, Y)` combines `p`, `M`, and `Y` into the scalar `loss`;
   `loss.backward()` writes gradients into the parameters of both `net` and `crowd`, and `opt.step()`
   applies them.
2. `net(X)`: `(N, C) = (400, 4)`. `p`: the same shape, `(N, C) = (400, 4)`. `crowd()`:
   `(A, C, C) = (5, 4, 4)`.
3. `p[i]` has shape `(C,)`, `M[a]` has shape `(C, C)`: a `(m,) @ (m, k)` vector-matrix product with
   $m = k = C$, costing $O(C^2)$ time; the result `q` is a length-$C$ vector, $O(C)$ memory.
4. `net.l1`: `(N, D) @ (D, H)`, time $O(NDH)$, forward output `(N, H)`, memory $O(NH)$. `net.l2`:
   `(N, H) @ (H, C)`, time $O(NHC)$, output `(N, C)`, memory $O(NC)$. Backward keeps `l1`'s input (`X`,
   $O(ND)$), the `ReLU` output ($O(NH)$; it is `l2`'s input and also gates the `ReLU` gradient, so the
   pre-activation itself is not kept) and the softmax output `p` ($O(NC)$): the same order as the forward
   activations.
5. Loose bound $O(NAC^2)$: the double loop runs up to $N \cdot A$ times, and every iteration that does
   not `continue` does an $O(C^2)$ vector-matrix product. Since it `continue`s whenever `lab < 0`, the
   tight bound is $O(PC^2)$, with $P$ the number of iterations that actually reach the product. Here
   $N \cdot A = 2000$ and $P = 998$ — about a factor of 2 apart.
6. Computing `p[i] @ M[a]` for every pair at once, e.g. with `einsum('nc,acd->nad', p, M)`, produces a
   tensor of shape `(N, A, C)`, $O(NAC)$ memory. At this scale that is $2000 \times 4 = 8000$ floats,
   nothing to worry about, but the ratio to the $O(PC)$ actually needed grows with $N \cdot A / P$: with
   many more annotators than any one item receives, most of that grid holds pairs with no label at all.
   It is avoidable — select the $P$ valid pairs before doing any arithmetic, which is what Part 3 does.
7. `net`'s forward does about $NDH + NHC = 134{,}400$ multiply-adds; `nll_loop`'s tight bound is
   $PC^2 = 998 \times 16 = 15{,}968$, about $8\times$ fewer. Measured on one training step, though,
   `net`'s forward takes about 0.4 ms, while `nll_loop` takes about 34 ms to produce the loss and about
   67 ms to run backward through it — `nll_loop` dominates by two orders of magnitude despite doing less
   arithmetic. The reason: its $P$ products are $P$ separate Python-level tensor calls, each paying a
   fixed interpreter and autograd bookkeeping cost, while `net`'s two linear layers are two calls into a
   single batched matrix-multiply kernel. Multiply-add counts and wall-clock time are not the same
   thing.

### Part 2

An annotator's confusion matrix is a stochastic matrix whose row $c$ is its reporting distribution given
that the true class is $c$; the diagonal entry $M_a[c, c]$ is the probability it gets class $c$ right, so
averaging the diagonal gives one reliability number per annotator, without ever looking at `y`.

```python
def reliability(self):
    return self.forward().diagonal(dim1=-2, dim2=-1).mean(-1)


CrowdLayer.reliability = reliability          # attach to the CrowdLayer class given in the problem


def least_reliable(r):
    return int(r.argmin().item())
```

On the trained `crowd` of the problem statement, `crowd.reliability()` is about
`[0.94, 0.82, 0.58, 0.31, 0.26]`, against the ground truth `RELIABILITY = [0.95, 0.8, 0.6, 0.4, 0.15]`:
the ranking matches, `least_reliable` returns `4`, and the same holds for three more seeds trained for
fewer epochs. The last two estimates (0.31 and 0.26) lie closer together than the true values (0.4 and
0.15) — an annotator who rarely labels and reports close to uniformly gives the
corresponding row of $M_a$ little evidence to learn from — but the ordering `least_reliable` needs is
preserved.

### Part 3

Idea: instead of a Python loop over $(i, a)$, take the $P$ valid pairs at once with `nonzero`, gather the
corresponding rows of `p` and matrices of `M`, and run all $P$ vector-matrix products as one batched
matrix multiply.

```python
def nll_vectorized(p, M, Y):
    idx_i, idx_a = (Y >= 0).nonzero(as_tuple=True)                    # P pairs, P = (Y >= 0).sum()
    lab = Y[idx_i, idx_a]
    q = torch.bmm(p[idx_i].unsqueeze(1), M[idx_a]).squeeze(1)         # (P, 1, C) @ (P, C, C) -> (P, C)
    return -torch.log(q.gather(1, lab.unsqueeze(1)).squeeze(1) + 1e-8).sum()
```

`p[idx_i]` and `M[idx_a]` are advanced indexing, producing new tensors of shape `(P, C)` and
`(P, C, C)`; `torch.bmm` treats the leading dimension as a batch of $P$ independent `(1, C) @ (C, C)`
products; `gather` reads off, from each of the $P$ rows of `q`, the probability of the label that
annotator actually reported. The asymptotic time is the same $O(PC^2)$ as `nll_loop`'s tight bound — the
multiply-add count has not changed — and its intermediate tensors are $O(PC)$, not the $O(NAC)$ of Part
1's question 6, because `nonzero` selects the $P$ pairs before any arithmetic runs. What changes is that
those $P$ products are now one call into `torch.bmm` instead of $P$ Python-level calls. Checked against
`nll_loop` on the trained `p`, `M`, `Y` of the problem statement, the two agree to floating-point
tolerance, and so do their gradients with respect to `p` and `M`. Timed over 30 repetitions after a
few warm-up calls, `nll_loop` takes about 21 ms and `nll_vectorized` well under 1 ms — over a hundred
times faster at this scale ($N = 400$, $A = 5$, $P = 998$), almost entirely the Python-loop overhead
from Part 1's question 7, not a difference in algorithm.

### Bonus

1. Time $O(L^2 d + Ld^2)$: splitting into $h$ heads of dimension $d / h$ does not change the first term,
   since each head's $QK^\top$ and (weights) $\times V$ cost $O(L^2 \cdot d/h)$ and there are $h$ of
   them; the four projections ($Q$, $K$, $V$, output) each cost $O(Ld^2)$ regardless of $h$. Memory to
   run backward is dominated by $O(hL^2)$: the post-softmax attention weights of every head have to be
   kept for softmax's backward pass, and unlike the time cost, this grows linearly with $h$, not only
   with $d$. This is exactly the tensor that fused kernels such as FlashAttention avoid materializing,
   recomputing it during backward instead to bring memory down to $O(Ld)$.
2. Time $O(B \cdot C_{in} \cdot C_{out} \cdot k^2 \cdot H_{out} \cdot W_{out})$: every one of the
   $B \cdot C_{out} \cdot H_{out} \cdot W_{out}$ output entries is a sum over $C_{in} \cdot k^2$ input
   entries.
3. Time $O(Bnmp)$: $B$ independent $(n, m) @ (m, p)$ products, each $O(nmp)$. The output has shape
   $(B, n, p)$, so it occupies $O(Bnp)$ memory.

### Follow-ups

- Computing the full grid with `einsum('nc,acd->nad', p, M)` and masking afterwards is mathematically
  the same computation as Part 3's version, but back to $O(NAC)$ memory; the only difference is
  selecting the valid pairs before or after doing the arithmetic.
- `q.gather(1, lab.unsqueeze(1))` could equally be written `q[torch.arange(len(lab)), lab]`; the two are
  equivalent, and `gather` generalizes more easily to higher dimensions.
- Training on mini-batches instead of the full `X` scales every step's cost down with the batch size,
  but it does not change the complexity conclusions of Part 1's questions 5 and 6 — it only spreads the
  same constants over more steps.
- With larger $C$, the `1e-8` floor inside `nll_loop` and `nll_vectorized` can stop being enough;
  working in log-probabilities throughout (log-softmax, `logsumexp`) rather than exponentiating and then
  taking a log again is the more robust choice.

<details>
<summary>Checks (runnable)</summary>

```python
import statistics as st

# Part 2: the learned confusion matrices recover the reliability ranking, without ever seeing y
with torch.no_grad():
    r_hat = crowd.reliability()
print("estimated reliability:", [round(v, 2) for v in r_hat.tolist()])
assert least_reliable(r_hat) == RELIABILITY.index(min(RELIABILITY))

for extra_seed in (1, 2, 3):                    # a few more runs, fewer epochs, same conclusion
    _, crowd_s, _, Y_s = run(seed=extra_seed, epochs=15)
    with torch.no_grad():
        r_s = crowd_s.reliability()
    assert least_reliable(r_s) == RELIABILITY.index(min(RELIABILITY))

# Part 3: same value and same gradient as the loop, on the trained model of the problem statement
with torch.no_grad():
    p, M = F.softmax(net(X), dim=-1), crowd()
    loop_val, vec_val = nll_loop(p, M, Y), nll_vectorized(p, M, Y)
    assert torch.allclose(loop_val, vec_val, atol=1e-4)

p_g = F.softmax(net(X), dim=-1).detach().requires_grad_(True)
M_g = crowd().detach().requires_grad_(True)
g_loop = torch.autograd.grad(nll_loop(p_g, M_g, Y), [p_g, M_g])
p_g2, M_g2 = p_g.detach().requires_grad_(True), M_g.detach().requires_grad_(True)
g_vec = torch.autograd.grad(nll_vectorized(p_g2, M_g2, Y), [p_g2, M_g2])
assert torch.allclose(g_loop[0], g_vec[0], atol=1e-5) and torch.allclose(g_loop[1], g_vec[1], atol=1e-5)

torch.set_num_threads(1)                        # a stable reading: thread-pool scheduling otherwise adds noise
for _ in range(5):                              # warm-up before timing
    nll_loop(p, M, Y)
    nll_vectorized(p, M, Y)
reps = 30
t0 = time.time()
for _ in range(reps):
    nll_loop(p, M, Y)
t_loop = (time.time() - t0) / reps
t0 = time.time()
for _ in range(reps):
    nll_vectorized(p, M, Y)
t_vec = (time.time() - t0) / reps
print(f"nll_loop {t_loop * 1000:.2f} ms   nll_vectorized {t_vec * 1000:.2f} ms   speedup {t_loop / t_vec:.0f}x")
assert t_vec < t_loop / 10                      # vectorized version is at least an order of magnitude faster
```

</details>

</details>
