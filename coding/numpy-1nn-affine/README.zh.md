# NumPy 1-NN 写成一层 Wx+b

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程（含数学推导）· NumPy | ★★★★☆ | 中等 | MLE · RE | numpy, vectorization, broadcasting, linear-algebra | 2 个部分 / 60 分钟 |
<!-- meta:end -->

## 题目

`X_train` 是形状为 `(n, d)` 的浮点数组，$n \ge 1$，它的各行 $x_0, \dots, x_{n-1} \in \mathbb{R}^d$ 是训练点。
`y_train` 是形状为 `(n,)` 的整数数组，`y_train[i]` 是 $x_i$ 的类别标签，取值为整数 $0, 1, \dots, c - 1$ 之一。
`X_query` 是形状为 `(m, d)` 的浮点数组，它的各行 $q_0, \dots, q_{m-1}$ 是待分类的查询点。

*1-最近邻（1-nearest-neighbour，1-NN）分类*把离查询点 $q$ 最近的那个训练点的标签作为 $q$ 的预测标签。
远近用*平方欧氏距离*（squared Euclidean distance）衡量：

$$\lVert q - x_i \rVert^2 = \sum_{k=0}^{d-1} (q_k - x_{ik})^2 ,$$

有多个训练点同样近时，取下标最小的那个：

$$\mathrm{nn}(q) = \text{满足 } \lVert q - x_i \rVert^2 = \min_k \lVert q - x_k \rVert^2 \text{ 的最小下标 } i .$$

$q$ 的预测标签是 `y_train[nn(q)]`。用 NumPy 完成下面两个部分。

### Part 1 —— 不用 Python 循环的 1-NN

返回全部 $m$ 个查询点的预测标签。代码不得在 Python 层面对训练点、查询点或坐标做迭代：不能用 `for`、`while`、推导式、`map`、
`np.vectorize`，每一步都是对整个数组的运算。说明每个中间数组的形状。

```py
def predict_1nn(X_train: np.ndarray, y_train: np.ndarray, X_query: np.ndarray) -> np.ndarray:
    """Shapes: X_train (n, d) float, y_train (n,) int, X_query (m, d) float.
    Returns the predicted labels, shape (m,)."""
```

例子，$n = 4$、$d = 2$、$m = 3$：

```text
X_train = [[0, 0],        y_train = [2, 0, 0, 1]        X_query = [[1, 0],
           [2, 0],                                                 [2, 1],
           [0, 2],                                                 [2, 3]]
           [3, 3]]
```

| 查询点 | 到 $x_0$ 的平方距离 | 到 $x_1$ | 到 $x_2$ | 到 $x_3$ | $\mathrm{nn}(q)$ | 预测标签 |
| --- | --- | --- | --- | --- | --- | --- |
| $q_0 = (1, 0)$ | 1 | 1 | 5 | 13 | 0（下标 0 与 1 并列） | `y_train[0]` = 2 |
| $q_1 = (2, 1)$ | 5 | 1 | 5 | 5 | 1 | `y_train[1]` = 0 |
| $q_2 = (2, 3)$ | 13 | 9 | 5 | 1 | 3 | `y_train[3]` = 1 |

函数返回 `[2, 0, 1]`。

### Part 2 —— 同样的预测写成一层仿射变换加激活函数

*仿射层*（affine layer）也叫全连接层或线性层，在 PyTorch 里是 `torch.nn.Linear`。它把输入向量 $x \in \mathbb{R}^d$ 映射为 $Wx + b$，
其中*权重矩阵*（weight matrix） $W$ 和*偏置向量*（bias vector） $b$ 与 $x$ 无关。*激活函数*（activation function）是作用在一层输出上的
一个固定的非线性函数。这里用的是 *softmax*，它把 $z \in \mathbb{R}^n$ 映射为一个含 $n$ 个概率的向量：

$$\mathrm{softmax}(z)_i = \frac{e^{z_i}}{\sum_{k} e^{z_k}} .$$

这一问的网络让查询点先经过一个有 $n$ 个输出的仿射层，再经过 softmax，然后取概率最大的下标
（最大值不止一个时取其中最小的下标，`np.argmax` 正是这样做的），最后用这个下标到 `y_train` 里取标签。

**(a)** 把单个查询点 $q \in \mathbb{R}^d$ 写成列向量。找出只由训练集算出的 $W_1 \in \mathbb{R}^{n \times d}$ 和
$b_1 \in \mathbb{R}^n$，使得对任意 $q$ 都有

$$\arg\max_i \mathrm{softmax}(W_1 q + b_1)_i = \mathrm{nn}(q) ,$$

并列时的取法也要一致。证明这个等式。

**(b)** 对整批查询点 `X_query`（每行一个查询点）实现前向传播：`logits = X_query @ W + b`，其中 `W` 的形状是 `(d, n)`，
`b` 的形状是 `(n,)`，然后对每一行做 softmax。`X_query` 只允许出现在这一个表达式里。说明 `W`、`b` 与 $W_1$、$b_1$ 的关系。

```py
def affine_layer(X_train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Builds the layer from X_train of shape (n, d). Returns W of shape (d, n) and b of shape (n,)."""

def predict_1nn_affine(X_train: np.ndarray, y_train: np.ndarray,
                       X_query: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward pass. Returns (probs, labels): probs[j] = softmax(logits[j]), shape (m, n),
    and labels[j] = y_train[argmax(probs[j])], shape (m,)."""
```

对 Part 1 的数据，`probs` 的形状是 `(3, 4)`，每一行之和为 1，`labels` 仍然是 `[2, 0, 1]`。
对任何输入，`labels` 都必须与 `predict_1nn` 的输出相同。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前先向面试官确认：查询点是一个一个给，还是一次给一批 `(m, d)`；“不用循环”是否也排除推导式和 `np.vectorize`（本文按排除处理）；
用什么距离、并列时怎么取；Part 2 要的是列向量写法 $W_1 q + b_1$，还是按行成批的写法 `X_query @ W + b`。

### Part 1

最直接的无循环写法是用广播（broadcasting）相减：`X_query[:, None, :] - X_train[None, :, :]`，再平方、沿最后一个轴求和。
结果正确，但要分配一个 `(m, n, d)` 的数组。把平方展开，就可以去掉第三个轴：

$$\lVert q - x \rVert^2 = (q - x)^\top (q - x) = \lVert q \rVert^2 - 2 q^\top x + \lVert x \rVert^2 .$$

记 $Q$ = `X_query`、$X$ = `X_train`，$m \times n$ 的平方距离矩阵在 $(j, i)$ 处的元素是

$$D_{ji} = \lVert q_j \rVert^2 + \lVert x_i \rVert^2 - 2 (Q X^\top)_{ji} .$$

三项的形状分别是 `(m, 1)`、`(n,)`、`(m, n)`，经广播相加得到 `(m, n)`。开销主要在矩阵乘法上：时间 $O(mnd)$，额外空间 $O(mn)$。
平方根是增函数，所以欧氏距离本身的 argmin 与平方距离的相同，不需要开方。

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

**(a)** 固定一个查询点 $q$，看 $D$ 中它对应的那一行。$\lVert q \rVert^2$ 这一项对所有 $i$ 都相同，只是把整行平移了一个常数，
既不改变最小值的位置，也不改变哪些元素并列。去掉它，再取相反数：

$$z_i = 2 x_i^\top q - \lVert x_i \rVert^2 = \lVert q \rVert^2 - \lVert q - x_i \rVert^2 .$$

它是 $q$ 的仿射函数，即 $z = W_1 q + b_1$，其中

$$W_1 = 2X \in \mathbb{R}^{n \times d} \quad (\text{第 } i \text{ 行是 } 2 x_i^\top), \qquad (b_1)_i = -\lVert x_i \rVert^2 ,$$

两者都只依赖训练集。$z_i$ 等于一个常数减去平方距离，所以距离最小的位置恰好就是 $z$ 最大的位置，
即 $\arg\max_i z_i = \mathrm{nn}(q)$，并列的情况也完全相同。被去掉的那一项是 $q$ 的二次函数，任何仿射层都算不出它；
之所以用不着它，只是因为 argmax 不受平移的影响。

softmax 不改变 argmax。所有的 $p_i = \mathrm{softmax}(z)_i$ 共用同一个正的分母，而 $t \mapsto e^t$ 严格递增，
所以 $p_i > p_k$ 当且仅当 $z_i > z_k$，$p_i = p_k$ 当且仅当 $z_i = z_k$：大小顺序和并列关系都保持不变。

对 Part 1 的数据和查询点 $q_1 = (2, 1)$，有 $\lVert q_1 \rVert^2 = 5$，并且

```math
W_1 = \begin{pmatrix} 0 & 0 \\ 4 & 0 \\ 0 & 4 \\ 6 & 6 \end{pmatrix},\quad
b_1 = \begin{pmatrix} 0 \\ -4 \\ -4 \\ -18 \end{pmatrix},\quad
z = W_1 q_1 + b_1 = \begin{pmatrix} 0 \\ 4 \\ 0 \\ 0 \end{pmatrix},\quad
5 - z = \begin{pmatrix} 5 \\ 1 \\ 5 \\ 5 \end{pmatrix}
```

最后一个向量就是 Part 1 的表格里 $q_1$ 的那一行。$(W_1, b_1)$ 并不唯一：对任意 $c > 0$ 和任意 $t$，
$(cW_1, cb_1 + t\mathbf{1})$ 的 argmax 都相同，$c$ 的作用相当于温度的倒数。取 $c = 1$ 时，softmax 同样会消去 $\lVert q \rVert^2$ 这个平移量，
所以这些概率就是高斯核权重：$p_i = e^{-\lVert q - x_i \rVert^2} / \sum_k e^{-\lVert q - x_k \rVert^2}$。

**(b)** `logits` 的第 $j$ 行是单个查询点公式的转置：$(W_1 q_j + b_1)^\top = q_j^\top W_1^\top + b_1^\top$。
把 $m$ 行叠起来得到 $Z = Q W_1^\top + \mathbf{1} b_1^\top$，因此 `W = W_1.T = 2 * X_train.T`，形状为 `(d, n)`；`b = b_1`，由广播加到每一行上。
`torch.nn.Linear(d, n)` 同时用到了这两种约定：它保存的权重形状是 `(n, d)`，也就是 $W_1$；计算时用的是 `x @ weight.T + bias`。

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

这一层给每个训练点配一个输出单元，共 $nd + n$ 个参数，全都不需要训练：网络把训练集原样存进了权重。

### 追问

- **输出每个类别的得分。** 设 `Y` 是形状为 `(n, c)` 的 one-hot 标签矩阵，则 `probs @ Y` 的形状是 `(m, c)`，相当于第二个线性层。
  它是全体训练点按上面的核权重做的加权投票，结果可能与 1-NN 不同（例子见验证代码）；要得到 1-NN 的标签，
  必须先对训练点取 argmax，再到 `y_train` 里取标签。
- **L1 距离。** 一层仿射加 argmax 无法表示它：使单元 $i$ 取胜的 $q$ 的集合是若干半空间的交集，必为凸集，而 L1 距离下的最近邻区域可以不是凸的。
  两层就够了：$nd$ 个隐藏单元计算 $q_k - x_{ik}$，激活函数取 $\lvert t \rvert$，第二层把每组 $d$ 个单元求和并取负（反例和实现都在验证代码里）。
- **余弦相似度。** 把每个训练点除以它自己的范数，取 $W = \hat{X}^\top$、$b = 0$。查询点的范数是它那一行 logits 共有的正因子，不影响 argmax。
- **$m \times n$ 放不进内存。** `W` 和 `b` 只算一次，把 `X_query` 按每块 $B$ 行分块送入。各行互不相关，所以结果完全相同，额外空间是 $O(Bn)$。
- **复杂度。** 时间 $O(mnd)$，主要花在矩阵乘法上；额外空间 $O(mn)$，而广播相减的写法需要 $O(mnd)$ 的空间。
  $n$ 非常大时不再做精确搜索，改用近似最近邻索引，例如 HNSW 或 IVF。

<details>
<summary>验证代码与追问的代码（可运行）</summary>

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
