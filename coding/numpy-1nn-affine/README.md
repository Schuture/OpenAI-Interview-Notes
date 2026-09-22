# NumPy 1-NN as an Affine Layer

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Coding with derivation · NumPy | ★★★★☆ | Medium | MLE · RE | numpy, vectorization, broadcasting, linear-algebra | 2 parts / 60 min |
<!-- meta:end -->

## Problem

`X_train` is a float array of shape `(n, d)` with $n \ge 1$. Its rows $x_0, \dots, x_{n-1} \in \mathbb{R}^d$
are the training points. `y_train` is an integer array of shape `(n,)`, and `y_train[i]` is the class
label of $x_i$, one of the integers $0, 1, \dots, c - 1$. `X_query` is a float array of shape `(m, d)`
whose rows $q_0, \dots, q_{m-1}$ are the points to classify.

*1-nearest-neighbour (1-NN) classification* gives a query $q$ the label of the training point closest
to it. Closeness is measured by the *squared Euclidean distance*

$$\lVert q - x_i \rVert^2 = \sum_{k=0}^{d-1} (q_k - x_{ik})^2 ,$$

and when several training points are equally close, the one with the smallest index wins:

$$\mathrm{nn}(q) = \text{the smallest } i \text{ such that } \lVert q - x_i \rVert^2 = \min_k \lVert q - x_k \rVert^2 .$$

The predicted label of $q$ is `y_train[nn(q)]`. Implement the following two parts in NumPy.

### Part 1 — 1-NN without Python loops

Return the predicted labels of all $m$ queries. The code must not iterate in Python over training
points, queries or coordinates: no `for` or `while`, no comprehension, no `map`, no `np.vectorize`.
Every step is an operation on whole arrays. State the shape of every intermediate array.

```py
def predict_1nn(X_train: np.ndarray, y_train: np.ndarray, X_query: np.ndarray) -> np.ndarray:
    """Shapes: X_train (n, d) float, y_train (n,) int, X_query (m, d) float.
    Returns the predicted labels, shape (m,)."""
```

Example with $n = 4$, $d = 2$, $m = 3$:

```text
X_train = [[0, 0],        y_train = [2, 0, 0, 1]        X_query = [[1, 0],
           [2, 0],                                                 [2, 1],
           [0, 2],                                                 [2, 3]]
           [3, 3]]
```

| query | sq. distance to $x_0$ | to $x_1$ | to $x_2$ | to $x_3$ | $\mathrm{nn}(q)$ | predicted label |
| --- | --- | --- | --- | --- | --- | --- |
| $q_0 = (1, 0)$ | 1 | 1 | 5 | 13 | 0 (tie between 0 and 1) | `y_train[0]` = 2 |
| $q_1 = (2, 1)$ | 5 | 1 | 5 | 5 | 1 | `y_train[1]` = 0 |
| $q_2 = (2, 3)$ | 13 | 9 | 5 | 1 | 3 | `y_train[3]` = 1 |

The function returns `[2, 0, 1]`.

### Part 2 — The same prediction as an affine layer followed by an activation

An *affine layer* (also called a fully connected or linear layer, `torch.nn.Linear` in PyTorch) maps an
input vector $x \in \mathbb{R}^d$ to $Wx + b$. The *weight matrix* $W$ and the *bias vector* $b$ do not
depend on $x$. An *activation function* is a fixed non-linear function applied to the output of a
layer. Here it is the *softmax*, which maps $z \in \mathbb{R}^n$ to a vector of $n$ probabilities:

$$\mathrm{softmax}(z)_i = \frac{e^{z_i}}{\sum_{k} e^{z_k}} .$$

The network of this part sends a query through one affine layer with $n$ outputs, applies the softmax,
takes the index of the largest probability (the smallest such index if there are several, which is
what `np.argmax` returns) and looks this index up in `y_train`.

**(a)** For a single query $q \in \mathbb{R}^d$ written as a column vector, find
$W_1 \in \mathbb{R}^{n \times d}$ and $b_1 \in \mathbb{R}^n$, computed from the training set alone, such
that for every $q$

$$\arg\max_i \mathrm{softmax}(W_1 q + b_1)_i = \mathrm{nn}(q) ,$$

including the rule for ties. Prove the equality.

**(b)** Implement the forward pass for the whole batch `X_query`, whose rows are the queries:
`logits = X_query @ W + b` with `W` of shape `(d, n)` and `b` of shape `(n,)`, followed by the softmax
of each row. `X_query` may be used in this one expression only. Say how `W` and `b` are obtained from
$W_1$ and $b_1$.

```py
def affine_layer(X_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Builds the layer from X_train of shape (n, d). Returns W of shape (d, n) and b of shape (n,)."""

def predict_1nn_affine(X_train: np.ndarray, y_train: np.ndarray,
                       X_query: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward pass. Returns (probs, labels): probs[j] = softmax(logits[j]), shape (m, n),
    and labels[j] = y_train[argmax(probs[j])], shape (m,)."""
```

For the data of Part 1, `probs` has shape `(3, 4)`, each of its rows sums to 1, and `labels` is again
`[2, 0, 1]`. For every input, `labels` must equal the output of `predict_1nn`.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Confirm with the interviewer before coding: whether the queries come one at a time or as an `(m, d)`
batch; whether "no loops" also excludes comprehensions and `np.vectorize` (assumed here); the distance
and the rule for ties; and in Part 2 whether the layer is wanted for a column vector, $W_1 q + b_1$, or
for a batch of rows, `X_query @ W + b`.

### Part 1

The direct loop-free version subtracts with broadcasting, `X_query[:, None, :] - X_train[None, :, :]`,
then squares and sums over the last axis. It is correct but allocates an `(m, n, d)` array. Expanding
the square removes the third axis:

$$\lVert q - x \rVert^2 = (q - x)^\top (q - x) = \lVert q \rVert^2 - 2 q^\top x + \lVert x \rVert^2 .$$

With $Q$ = `X_query` and $X$ = `X_train`, entry $(j, i)$ of the $m \times n$ matrix of squared distances is

$$D_{ji} = \lVert q_j \rVert^2 + \lVert x_i \rVert^2 - 2 (Q X^\top)_{ji} .$$

The three terms have shapes `(m, 1)`, `(n,)` and `(m, n)`, and broadcasting adds them to `(m, n)`. The
matrix product dominates: $O(mnd)$ time and $O(mn)$ extra memory. The square root is increasing, so the
Euclidean distance itself has the same argmin and is never needed.

```python
import numpy as np


def nearest_indices(X_train, X_query):
    sq_train = (X_train ** 2).sum(axis=1)                           # (n,)    |x_i|^2
    sq_query = (X_query ** 2).sum(axis=1, keepdims=True)            # (m, 1)  |q_j|^2
    # NOTE: keepdims=True. With shape (m,) the sum below raises "operands could not be broadcast together"
    #       if m != n, and if m == n it silently adds |q_j|^2 to COLUMN j, which changes the argmin.
    inner = X_query @ X_train.T                                     # (m, d) @ (d, n) -> (m, n)
    sqdist = sq_query + sq_train - 2.0 * inner                      # (m, 1) + (n,) - (m, n) -> (m, n)
    # NOTE: rounding can leave entries such as -7e-15. Harmless for argmin; clip at 0 before any sqrt.
    # NOTE: axis=1 runs over the training points, and argmin returns the FIRST minimum, which is the tie rule.
    return np.argmin(sqdist, axis=1)                                # (m,)


def predict_1nn(X_train, y_train, X_query):
    return y_train[nearest_indices(X_train, X_query)]               # integer-array indexing: (n,)[(m,)] -> (m,)
```

### Part 2

**(a)** Fix a query $q$ and look at its row of $D$. The term $\lVert q \rVert^2$ is the same for every
$i$. It shifts the whole row by a constant, so it changes neither the index of the minimum nor which
entries tie. Drop it and flip the sign:

$$z_i = 2 x_i^\top q - \lVert x_i \rVert^2 = \lVert q \rVert^2 - \lVert q - x_i \rVert^2 .$$

This is affine in $q$, namely $z = W_1 q + b_1$ with

$$W_1 = 2X \in \mathbb{R}^{n \times d} \quad (\text{row } i \text{ is } 2 x_i^\top), \qquad (b_1)_i = -\lVert x_i \rVert^2 ,$$

and both depend on the training set only. Because $z_i$ is a constant minus the squared distance, $z$
is largest exactly where the distance is smallest, so $\arg\max_i z_i = \mathrm{nn}(q)$ with the same
ties. The dropped term is quadratic in $q$, so no affine layer could have produced it. It is not needed
only because the argmax ignores a shift.

The softmax does not change the argmax. All $p_i = \mathrm{softmax}(z)_i$ share one positive
denominator and $t \mapsto e^t$ is strictly increasing, so $p_i > p_k$ if and only if $z_i > z_k$, and
$p_i = p_k$ if and only if $z_i = z_k$. Order and ties are preserved.

For the data of Part 1 and the query $q_1 = (2, 1)$ with $\lVert q_1 \rVert^2 = 5$:

```math
W_1 = \begin{pmatrix} 0 & 0 \\ 4 & 0 \\ 0 & 4 \\ 6 & 6 \end{pmatrix},\quad
b_1 = \begin{pmatrix} 0 \\ -4 \\ -4 \\ -18 \end{pmatrix},\quad
z = W_1 q_1 + b_1 = \begin{pmatrix} 0 \\ 4 \\ 0 \\ 0 \end{pmatrix},\quad
5 - z = \begin{pmatrix} 5 \\ 1 \\ 5 \\ 5 \end{pmatrix}
```

The last vector is the row of $q_1$ in the table of Part 1. The pair $(W_1, b_1)$ is not unique:
$(cW_1, cb_1 + t\mathbf{1})$ with any $c > 0$ and any $t$ has the same argmax, and $c$ acts as an inverse
temperature. With $c = 1$ the softmax cancels the shift by $\lVert q \rVert^2$ as well, so the
probabilities are Gaussian kernel weights, $p_i = e^{-\lVert q - x_i \rVert^2} / \sum_k e^{-\lVert q - x_k \rVert^2}$.

**(b)** Row $j$ of `logits` is the transpose of the single-query formula:
$(W_1 q_j + b_1)^\top = q_j^\top W_1^\top + b_1^\top$. Stacking the $m$ rows gives
$Z = Q W_1^\top + \mathbf{1} b_1^\top$, hence `W = W_1.T = 2 * X_train.T` of shape `(d, n)`, and `b = b_1`,
which broadcasting adds to every row. `torch.nn.Linear(d, n)` uses both conventions at once: it stores
a weight of shape `(n, d)`, which is $W_1$, and computes `x @ weight.T + bias`.

```python
def affine_layer(X_train):
    # NOTE: W is the TRANSPOSE of W_1, column i is 2 x_i. Without .T, X_query @ W raises a shape error
    #       if d != n and is silently wrong if d == n.
    W = 2.0 * X_train.T                                 # (d, n)
    b = -(X_train ** 2).sum(axis=1)                     # (n,)
    return W, b


def softmax(Z):
    # NOTE: the logits grow like |x|^2. np.exp(1000.0) is inf and inf / inf is nan, so shift every row to max 0.
    E = np.exp(Z - Z.max(axis=1, keepdims=True))        # (m, n) - (m, 1) -> (m, n)
    # NOTE: axis=1, one distribution per query. axis=0 runs without an error and changes the argmax.
    return E / E.sum(axis=1, keepdims=True)             # (m, n) / (m, 1) -> (m, n)


def predict_1nn_affine(X_train, y_train, X_query):
    W, b = affine_layer(X_train)
    logits = X_query @ W + b                            # (m, d) @ (d, n) + (n,) -> (m, n)
    # NOTE: b of shape (n,) lines up with the LAST axis of (m, n), so it is added to every row.
    probs = softmax(logits)                             # (m, n), every row sums to 1
    nearest = np.argmax(probs, axis=1)                  # (m,)
    # NOTE: in floating point the softmax can turn two distinct logits into a tie: softmax([[-1e-17, 0.]])
    #       is [[0.5, 0.5]], and the argmax moves from 1 to 0. np.argmax(logits, axis=1) avoids this.
    return probs, y_train[nearest]
```

The layer has one output unit per training point and $nd + n$ parameters, none of them trained: the
network stores the training set in its weights.

### Follow-ups

- **A score per class.** With the one-hot label matrix `Y` of shape `(n, c)`,
  `probs @ Y` has shape `(m, c)` and is a second linear layer. It is a vote of all training points with
  the kernel weights above and can disagree with 1-NN (example in the checks); the 1-NN label needs the
  argmax over the training points first and the lookup in `y_train` second.
- **L1 distance.** One affine layer with an argmax cannot represent it: the set of $q$ where unit $i$ wins
  is an intersection of half-spaces, hence convex, while an L1 nearest-neighbour cell need not be. Two
  layers are enough: $nd$ hidden units $q_k - x_{ik}$ with the activation $\lvert t \rvert$, then minus the
  sum of each group of $d$ units (both in the checks).
- **Cosine similarity.** Divide every training row by its norm and use $W = \hat{X}^\top$, $b = 0$. The
  norm of the query is a positive factor common to its whole row of logits and does not move the argmax.
- **$m \times n$ does not fit in memory.** Build `W` and `b` once and send `X_query` through in blocks of
  $B$ rows. The rows are independent, so the result is identical and the extra memory is $O(Bn)$.
- **Complexity.** $O(mnd)$ time, dominated by the matrix product, and $O(mn)$ extra memory, against
  $O(mnd)$ memory for the broadcast difference. For very large $n$, exact search gives way to an
  approximate nearest-neighbour index such as HNSW or IVF.

<details>
<summary>Checks and the code for the follow-ups (runnable)</summary>

```python
def nearest_indices_loops(X_train, X_query):                # the definition, with two explicit loops
    nearest = []
    for q in X_query:
        best, best_dist = 0, np.inf
        for i, x in enumerate(X_train):
            dist = np.sum((q - x) ** 2)
            if dist < best_dist:                            # NOTE: strict <, so the first minimum is kept
                best, best_dist = i, dist
        nearest.append(best)
    return np.array(nearest)


def nearest_indices_broadcast(X_train, X_query, p=2):       # (m, n, d) differences; p=1 is the L1 distance
    diff = X_query[:, None, :] - X_train[None, :, :]
    return np.argmin(np.sum(np.abs(diff) ** p, axis=2), axis=1)


def predict_1nn_blocks(X_train, y_train, X_query, block=1024):
    W, b = affine_layer(X_train)
    nearest = np.empty(len(X_query), dtype=np.intp)
    for start in range(0, len(X_query), block):             # a loop over blocks of queries, not over points
        nearest[start:start + block] = np.argmax(X_query[start:start + block] @ W + b, axis=1)
    return y_train[nearest]


def predict_1nn_l1_network(X_train, y_train, X_query):
    n, d = X_train.shape
    W1 = np.tile(np.eye(d), (1, n))                         # (d, n*d)  hidden unit i*d + k computes q_k - x_ik
    b1 = -X_train.reshape(-1)                               # (n*d,)
    hidden = np.abs(X_query @ W1 + b1)                      # (m, n*d)  |t| = relu(t) + relu(-t)
    W2 = -np.kron(np.eye(n), np.ones((d, 1)))               # (n*d, n)  minus the sum of each group of d units
    return y_train[np.argmax(hidden @ W2, axis=1)]


# The example of the statement
X_train = np.array([[0., 0.], [2., 0.], [0., 2.], [3., 3.]])
y_train = np.array([2, 0, 0, 1])
X_query = np.array([[1., 0.], [2., 1.], [2., 3.]])
assert nearest_indices(X_train, X_query).tolist() == [0, 1, 3]              # q_0 is a tie between 0 and 1
assert predict_1nn(X_train, y_train, X_query).tolist() == [2, 0, 1]
W, b = affine_layer(X_train)
assert W.T.tolist() == [[0, 0], [4, 0], [0, 4], [6, 6]] and b.tolist() == [0, -4, -4, -18]
z = W.T @ X_query[1] + b                                                    # column form W_1 q + b_1, shape (n,)
assert z.tolist() == [0, 4, 0, 0] and (5 - z).tolist() == [5, 1, 5, 5]
probs, labels = predict_1nn_affine(X_train, y_train, X_query)
assert labels.tolist() == [2, 0, 1] and probs[0, 0] == probs[0, 1] == probs[0].max()

# Random tests against the double loop
rng = np.random.default_rng(0)
ties = 0
for trial in range(300):
    n, d, m = rng.integers(1, 9), rng.integers(1, 5), rng.integers(1, 8)
    if trial % 2:                   # NOTE: small integer coordinates produce exact ties and duplicate points
        X_train = rng.integers(0, 3, (n, d)).astype(float)
        X_query = rng.integers(0, 3, (m, d)).astype(float)
    else:
        X_train, X_query = rng.normal(size=(n, d)), rng.normal(size=(m, d))
    y_train = rng.integers(0, 3, n)
    expected = nearest_indices_loops(X_train, X_query)
    dist = np.sum((X_query[:, None, :] - X_train[None, :, :]) ** 2, axis=2)
    ties += np.sum(np.sum(dist == dist.min(axis=1, keepdims=True), axis=1) > 1)

    assert np.array_equal(nearest_indices(X_train, X_query), expected)
    assert np.array_equal(nearest_indices_broadcast(X_train, X_query), expected)
    W, b = affine_layer(X_train)
    probs, labels = predict_1nn_affine(X_train, y_train, X_query)
    assert W.shape == (d, n) and b.shape == (n,) and probs.shape == (m, n) and labels.shape == (m,)
    assert np.array_equal(np.argmax(probs, axis=1), expected)               # affine layer == distances == loops
    assert np.array_equal(labels, predict_1nn(X_train, y_train, X_query))
    kernel = np.exp(-dist)
    assert np.allclose(probs, kernel / kernel.sum(axis=1, keepdims=True))   # Gaussian kernel weights, rows sum to 1
    assert np.array_equal(predict_1nn_blocks(X_train, y_train, X_query, block=3), labels)
    l1 = nearest_indices_broadcast(X_train, X_query, p=1)
    assert np.array_equal(predict_1nn_l1_network(X_train, y_train, X_query), y_train[l1])
assert ties > 100                   # the tie rule was really exercised

# Softmax: large logits stay finite; two distinct logits can become a tie
assert np.allclose(softmax(np.array([[1872., 1873.]])), [[0.26894142, 0.73105858]])
tiny = np.array([[-1e-17, 0.0]])
assert np.argmax(tiny, axis=1)[0] == 1 and softmax(tiny).tolist() == [[0.5, 0.5]]

# Follow-up: the soft vote disagrees with 1-NN. The nearest point has class 0, class 1 gets 0.64 of the vote
X1, y1 = np.array([[0.0], [1.1], [1.1]]), np.array([0, 1, 1])
probs, labels = predict_1nn_affine(X1, y1, np.array([[0.5]]))
votes = probs @ np.eye(2)[y1]                                               # (1, 3) @ (3, 2) -> (1, 2)
assert labels[0] == 0 and np.argmax(votes[0]) == 1 and round(votes[0, 1], 2) == 0.64

# Follow-up: an L1 nearest-neighbour cell that is not convex. A and B belong to x_0, their midpoint to x_1
X2 = np.array([[0., 0.], [2., 1.]])
A, B = np.array([0.4, 2.0]), np.array([1.4, 0.0])
assert nearest_indices_broadcast(X2, np.stack([A, B, (A + B) / 2]), p=1).tolist() == [0, 0, 1]
```

</details>

</details>
