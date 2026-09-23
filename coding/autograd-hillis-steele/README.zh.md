# 前缀矩阵连乘：Autograd、手写反向、Hillis–Steele 扫描

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 编程（含数学推导）· PyTorch | ★★★★☆ | 困难 | RS · RE · MLE | autograd, linear-algebra, parallel-scan, pytorch | 4 个部分 / 75 分钟 |
<!-- meta:end -->

## 题目

`W` 是一个形状为 `(N, D, D)` 的浮点张量，$N \ge 1$。它存放 $N$ 个 $D \times D$ 的方阵 $W_0, W_1, \dots, W_{N-1}$，
其中 `W[i]` 就是 $W_i$。第 $i$ 个*前缀积*（prefix product）是前 $i + 1$ 个矩阵按从左到右的顺序相乘的结果：

$$P_i = W_0 W_1 \cdots W_i, \qquad i = 0, 1, \dots, N-1,$$

因此 $P_0 = W_0$，且当 $i \ge 1$ 时 $P_i = P_{i-1} W_i$。输出是形状为 `(N, D, D)` 的张量 `P`，其中 `P[i]` 等于 $P_i$，
即要返回全部 $N$ 个前缀积。例如取 $N = 3$、$D = 2$：

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

用 PyTorch 完成下面四个部分。

### Part 1 —— 用下标赋值实现前向传播

**(a)** 实现 `prefix_products_inplace(W)`。用 `P = torch.empty_like(W)` 分配输出，再在一个 `for` 循环里用
`P[i] = P[i - 1] @ W[i]` 填充它。下标赋值会直接改写已有张量 `P` 的内存，这类操作称为*原地*（in-place）操作。

```py
def prefix_products_inplace(W: torch.Tensor) -> torch.Tensor:
    """W: float tensor of shape (N, D, D). Returns P of shape (N, D, D) with P[i] = W[0] @ ... @ W[i]."""
```

**(b)** PyTorch 的自动微分引擎 *autograd* 会记录作用在带 `requires_grad=True` 的张量上的各个运算。
对一个标量 `loss` 调用 `loss.backward()` 时，它沿着记录下来的运算反向应用链式法则，并把 `loss` 对 `W` 的梯度存入 `W.grad`。
在 autograd 下，(a) 中的函数会失败：

```py
W = torch.randn(4, 3, 3, requires_grad=True)
P = prefix_products_inplace(W)      # the values in P are correct
loss = P.sum()
loss.backward()
# RuntimeError: one of the variables needed for gradient computation has been modified by an inplace operation
```

解释 PyTorch 为什么报这个错。

### Part 2 —— autograd 能够求导的前向传播

把函数改写为 `prefix_products(W)`，不使用任何原地操作，使 Part 1(b) 的代码能够运行，并且 `W.grad` 中是正确的梯度。

### Part 3 —— 手写反向传播

设 $L$ 是一个依赖于所有 $P_i$ 的标量损失，已知*上游梯度*（upstream gradient） $G_i = \partial L / \partial P_i$。
它与 $P_i$ 形状相同，位置 $(a, b)$ 上的元素是 $\partial L / \partial (P_i)_{ab}$。
不使用 autograd，推导 $\partial L / \partial W_i$ 的公式并实现：

```py
def prefix_products_backward(W: torch.Tensor, P: torch.Tensor, G: torch.Tensor) -> torch.Tensor:
    """W, P, G: shape (N, D, D). P is the forward output and G[i] = dL/dP[i].
    Returns dW of shape (N, D, D) with dW[i] = dL/dW[i]."""
```

用两种方式之一验证结果：与 autograd 对 Part 2 的函数算出的 `W.grad` 比较；或与中心有限差分
$\bigl(L(W + \varepsilon E) - L(W - \varepsilon E)\bigr) / 2\varepsilon$ 比较，其中 $E$ 只在一个位置上为 1，其余为 0。

### Part 4 —— Hillis–Steele 并行扫描

Part 1–3 的循环要依次做 $N - 1$ 次乘法，因为第 $i$ 步需要第 $i - 1$ 步的结果。矩阵乘法满足结合律，
所以同样的前缀积可以用 Hillis–Steele 扫描在 $\lceil \log_2 N \rceil$ 轮内算出。初始时 $x_i = W_i$。
第 $k = 0, 1, 2, \dots$ 轮使用步长 $s = 2^k$，只要 $s < N$ 就执行。在一轮之内，对所有 $i \ge s$ 同时执行

$$x_i \leftarrow x_{i-s}\, x_i ,$$

其中右边使用的是这一轮开始之前的值，$i < s$ 的元素保持不变。最后一轮结束后 $x_i = P_i$。
同一轮内的各次乘法互不依赖，可以并行执行。以 $N = 4$ 为例：

| | $x_0$ | $x_1$ | $x_2$ | $x_3$ |
| --- | --- | --- | --- | --- |
| 初始 | $W_0$ | $W_1$ | $W_2$ | $W_3$ |
| $s = 1$ 之后 | $W_0$ | $W_0 W_1$ | $W_1 W_2$ | $W_2 W_3$ |
| $s = 2$ 之后 | $W_0$ | $W_0 W_1$ | $W_0 W_1 W_2$ | $W_0 W_1 W_2 W_3$ |

**(a)** 实现 `scan_forward(W)`，返回与 Part 2 相同的 `P`。每一轮必须是一次批量矩阵乘法，不能对 $i$ 写 Python 循环。

**(b)** 推导并实现这个扫描的反向传播：给定 `G`，在 $\lceil \log_2 N \rceil$ 轮内返回 $\partial L / \partial W$。

## 参考解答

<details>
<summary>展开参考解答</summary>

动手之前先向面试官确认两点：“原地”是指逐个位置填充输出张量（本文的假设），还是直接覆盖 `W` 本身；乘积是否从左往右。
如果顺序相反，下面所有的转置都要换到另一边。

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

乘法 `A @ B` 的反向传播需要 `A` 和 `B` 的值，所以 autograd 会保留对它们的引用，称为*保存的张量*（saved tensors）。
保存的是引用，不是拷贝。`P[i - 1]` 是一个*视图*（view）：与 `P` 共享内存的张量。每个张量都有一个*版本计数器*（version counter），
每次原地写入都会使它加一，视图与它所属的原张量共用同一个计数器。`backward()` 读取保存的张量时，会把当前的计数器值与保存时的值比较。
在 `P[i - 1]` 被保存之后，赋值 `P[i] = ...` 又让 `P` 的计数器加了一，于是比较失败，autograd 抛出这个错误。

这个检查是以张量为单位的，不是以元素为单位的。在这个循环里，被保存过的那些行后来并没有被覆盖，梯度其实本来是对的；
但 autograd 无法知道这一点，它宁可拒绝，也不冒悄悄返回错误梯度的风险。如果循环覆盖的是 `W[i]` 本身，
反向传播需要的旧 $W_i$ 就真的丢失了。

### Part 2

```python
def prefix_products(W):
    products = [W[0]]
    for i in range(1, W.shape[0]):
        products.append(products[-1] @ W[i])    # every product is a new tensor; nothing is overwritten
    return torch.stack(products)                # stack allocates a new (N, D, D) tensor and is differentiable
```

### Part 3

对任意矩阵 $X$，记 $\bar{X} = \partial L / \partial X$。对单次乘法 $Y = AB$，有 $Y_{ab} = \sum_c A_{ac} B_{cb}$，由链式法则得
$\bar{A}_{ac} = \sum_b \bar{Y}_{ab} B_{cb}$，$\bar{B}_{cb} = \sum_a A_{ac} \bar{Y}_{ab}$，即

$$\bar{A} = \bar{Y} B^\top, \qquad \bar{B} = A^\top \bar{Y}.$$

在前向传播中 $P_i$ 被用了两次：被损失直接使用，贡献 $G_i$；以及作为 $P_{i+1} = P_i W_{i+1}$ 的左因子。
到达 $P_i$ 的总梯度 $A_i$ 是这两项贡献之和：

$$A_{N-1} = G_{N-1}, \qquad A_i = G_i + A_{i+1} W_{i+1}^\top .$$

$W_i$ 只被用了一次，作为 $P_i = P_{i-1} W_i$ 的右因子，因此

$$\frac{\partial L}{\partial W_i} = P_{i-1}^\top A_i \quad (i \ge 1), \qquad \frac{\partial L}{\partial W_0} = A_0 .$$

一个从 $i = N - 1$ 到 $0$ 的循环就能算出全部结果，代价是 $O(N D^3)$，与前向传播相同。

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

前向。用归纳法：步长为 $s$ 的那一轮结束后，第 $i$ 个元素保存的是以下标 $i$ 结尾的最后 $\min(i + 1, 2s)$ 个矩阵的乘积。
这是因为 $x_{i-s}$ 保存的是以 $i - s$ 结尾的那一段，$x_i$ 保存的是紧接其后、以 $i$ 结尾的 $s$ 个矩阵，两者相乘正好把两段接起来。
最后一轮之后 $2s \ge N$，所以第 $i$ 个元素就是 $P_i$。

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

反向。从最后一轮到第一轮逐轮回退。一轮运算把 $X$ 映射为 $Y$：$j < s$ 时 $Y_j = X_j$，$j \ge s$ 时 $Y_j = X_{j-s} X_j$。
已知 $H = \partial L / \partial Y$，则 $X_j$ 每被使用一次，就按单次乘法的梯度公式得到一项：

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

扫描的计算量是 $O(N \log N \cdot D^3)$，顺序循环是 $O(N D^3)$；扫描只需要 $\lceil \log_2 N \rceil$ 个相互依赖的步骤，顺序循环需要 $N$ 个；
扫描的 tape 要保存 $\lceil \log_2 N \rceil$ 个与 `W` 同样大小的数组。只有当同一轮内的乘法真正并行执行时，扫描才更快。

### 追问

- 把 Part 3 封装成 `torch.autograd.Function`，让 autograd 调用你写的 `backward`（代码见下）。在 `forward` 内部 autograd 不记录任何运算，
  所以那里可以使用下标赋值。如果 `forward` 原地修改了某个输入，必须用 `ctx.mark_dirty` 声明。
- 降低 tape 的内存：在反向传播时重新计算各轮，或者改用 Blelloch 的 work-efficient 扫描，它的计算量是 $O(N)$，轮数约为 $2 \log_2 N$。
- 实际用途：线性递推 $h_t = A_t h_{t-1} + b_t$ 是在二元组 $(A_t, b_t)$ 上对一个满足结合律的运算做前缀扫描，
  线性循环网络和状态空间模型就是靠它在序列维度上并行训练的。
- 取 $D = 1$，Part 3–4 就变成一个一维版本——对标量 $x_1, \dots, x_n$（$n \le 2 \times 10^5$）求前缀积，
  并由上游梯度 $g$ 算出 $dx$——Part 3 的同一个 carry 递推本身就只用乘法完成这件事，不需要除法，
  即便某个 $x_i = 0$，$dx$ 依然正确。

<details>
<summary>验证代码与 torch.autograd.Function 封装（可运行）</summary>

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

# Follow-up: D = 1 is the 1D vector variant; the same carry recurrence needs no division and stays
# correct where x_i = 0.
x_vec = torch.tensor([[[2.]], [[0.]], [[3.]], [[-1.]]], dtype=torch.float64, requires_grad=True)
g_vec = torch.randn(4, 1, 1, dtype=torch.float64)
p_vec = prefix_products(x_vec)
(dx_autograd,) = torch.autograd.grad((p_vec * g_vec).sum(), x_vec)
dx_hand = prefix_products_backward(x_vec.detach(), p_vec.detach(), g_vec)
assert torch.allclose(dx_hand, dx_autograd)
```

</details>

</details>
