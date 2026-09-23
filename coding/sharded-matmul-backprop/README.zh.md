# 分片矩阵乘法：前向、反向与找 bug

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 推导 + 编程 + 调试 · NumPy / PyTorch | ★☆☆☆☆ | 困难 | MLE · RE | linear-algebra, parallelism, autograd, numpy, pytorch, debugging | 3 个部分 |
<!-- meta:end -->

## 题目

设 $X$ 形状为 `(B, d_in)`，$W$ 形状为 `(d_in, d_out)`，$Y = XW$ 形状为 `(B, d_out)`。一个*设备*（device）
就是 Python 列表里的一个条目，里面存一个 NumPy 数组；整个计算仍然运行在单机上，设备之间的每一次数据交换都要
经过下面两个显式的函数之一：

- `all_gather(shards, axis)`：`shards[k]` 是设备 $k$ 持有的、沿 `axis` 切出来的那一片。返回一个长度为 $n$
  的列表，其中每一项都是同一个数组——把所有分片沿 `axis` 拼接起来的结果。
- `all_reduce(shards)`：`shards[k]` 是设备 $k$ 自己的数组，形状都相同，每个数组是一次求和里的一部分贡献。
  返回一个长度为 $n$ 的列表，其中每一项都是同一个数组——所有分片按元素求和的结果。

矩阵的一个*分片*（shard）是沿某个轴的一段连续切片，分配给一个设备。*按列切*（column-parallel）是把 $W$
沿它的输出轴切分（`axis=1`，大小为 `d_out`）成 $W_0, \dots, W_{n-1}$，每个设备都持有 $X$ 的完整副本。
*按行切*（row-parallel）是把 $W$ 沿它的输入轴切分（`axis=0`，大小为 `d_in`）成 $W_0, \dots, W_{n-1}$，$X$
也沿它自己的特征轴（大小同样是 `d_in`）做相应切分，于是设备 $k$ 只持有 $X_k$，即与 $W_k$ 的行对应的那些列。
被切的那个轴的长度不能整除 $n$ 时，余数按每片一个分给前面的分片：`d_out = 7`、$n = 3$ 个设备时列宽是
$3, 2, 2$，设备 0 持有的 $W$ 分片形状是 `(d_in, 3)`，设备 1、2 的形状是 `(d_in, 2)`。这里的规模都很小——
`B`、`d_in`、`d_out` 最大 50，元素的绝对值不超过 100——而且 $n$ 不超过被切的那个轴的长度，所以不会有设备
拿到空的分片。

### Part 1 —— 手推前向和反向

对**按列切**的情形，写出设备 $k$ 在前向传播里算的是什么，以及如何拼出完整的 $Y$。然后，给定上游梯度
（upstream gradient）$\bar Y = \partial L / \partial Y$（完整的数组，每个设备上都相同），为每个设备推导
$\bar W_k = \partial L / \partial W_k$ 和 $\bar X = \partial L / \partial X$，并指出哪一步（如果有的话）需要
通信、是哪一种通信。对**按行切**的情形做同样的事。

### Part 2 —— 实现分片线性层

实现 `all_gather`、`all_reduce`，以及两种切分方式的前向和反向传播：

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

用 `np.array_split` 切分 $W$，按行切时对 $X$ 也一样，这样 `d_out` 或 `d_in` 就不必能整除 $n$。在 `float64`
下，用 `np.allclose` 把两种切分方式的前向和反向都与不分片的 NumPy 参考实现、以及 PyTorch autograd 做对比；
至少覆盖一种切分不均匀的情形。

### Part 3 —— 调试一个分片 MLP

下面的文件实现了一个切到 $n$ 个设备上的两层 MLP：第一层是从 `d_in` 到 `d_hidden` 的按列切 Linear，后接
`tanh`；第二层是从 `d_hidden` 到 `d_out` 的按行切 Linear；损失是相对某个目标的均方误差。`check_gradients`
把分片的前向和反向传播，与用同一组权重构造的不分片 NumPy 参考实现相比较，返回 $Y$ 和三个梯度各自的最大
绝对误差。

文件里有 5 个相互独立的 bug：修好其中一个不需要动别的，每一个都对 `check_gradients` 有各自的影响。找出并
修复全部 5 个；对每一个，说明它的位置，以及它为什么会产生你观察到的现象。全部修好之后，对任意随机种子，
`check_gradients()` 对 $Y$、`dW1`、`dW2`、`dX` 返回的误差都应低于 `1e-8`。

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

## 参考解答

<details>
<summary>展开参考解答</summary>

有两点值得先向面试官确认：先按 $W$ 的哪个轴切，以及 $X$ 一开始是已经分片还是完整的副本（下面的推导是对称
的，换一种约定只需要把转置换到另一边）。把 `all_gather` 和 `all_reduce` 写成两个独立的函数，让每一次数据
交换都只经过它们，这是 Part 3 里能够靠打印形状定位 bug 的前提。

### Part 1

对任意数组 $A$，记 $\bar A = \partial L / \partial A$。

**按列切。** 设备 $k$ 持有 $W$ 的第 $k$ 块列 $W_k$，形状 `(d_in, d_out_k)`，以及 $X$ 的完整副本。

$$Y_k = X W_k \quad (B \times d_{out,k}), \qquad Y = \operatorname{all\_gather}_{\mathrm{axis}=1}(Y_0, \dots, Y_{n-1}).$$

算出 $Y_k$ 本身不需要通信；只有当别处需要每个设备上都有完整的 $Y$ 时才用得到这次拼接。把给定的 $\bar Y$
就地切成 $\bar Y_k$（设备 $k$ 的那些列），对 $Y_k = X W_k$ 应用乘法的链式法则：

$$\bar W_k = X^\top \bar Y_k \quad \text{（本地）}, \qquad \bar X = \sum_k \bar Y_k W_k^\top = \operatorname{all\_reduce}\bigl(\bar Y_k W_k^\top\bigr).$$

$X$ 参与了每个设备的本地乘法，所以它的梯度是跨设备的求和——一次 all-reduce。

**按行切。** 设备 $k$ 持有 $W$ 的第 $k$ 块行 $W_k$，形状 `(d_in_k, d_out)`，以及 $X$ 对应的那块列 $X_k$，
形状 `(B, d_in_k)`。

$$Y_k = X_k W_k \quad \text{（部分和，形状 } B \times d_{out}\text{）}, \qquad Y = \sum_k Y_k = \operatorname{all\_reduce}(Y_0, \dots, Y_{n-1}).$$

这里 $Y_k$ 的形状已经对了，但只是答案的一部分，所以前向传播本身就需要一次 all-reduce。给定完整的 $\bar Y$
（这次归约做完之后，每个设备上都相同）：

$$\bar W_k = X_k^\top \bar Y \quad \text{（本地）}, \qquad \bar X_k = \bar Y W_k^\top \quad \text{（本地；设备 } k\text{ 自己那块 } \bar X\text{）}.$$

两个梯度都是本地的：$X_k$ 和 $W_k$ 各自只被一个设备用到，不需要合并。

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

用 `np.array_split(A, n, axis=...)` 做切分，它会把不能整除的大小尽量分均匀（`d_out = 7`、$n = 3$ 时宽度是
$3, 2, 2$）；按行切时对 $X$ 的特征轴用同样的 $n$ 调用它，能保证 $X_k$ 和 $W_k$ 在 `d_in_k` 上一致。末尾的
验证代码在 `float64` 下，对整除和不整除两种情形，都对照不分片的参考实现和 `torch.autograd` 做了检查。

### Part 3

各行按 bug 暴露的先后顺序排列：每一行的输出，都是把它上面各行的 bug 修好之后运行 `check_gradients()` 得到的。

| 已修好 | `check_gradients()` 的输出 | 指向 |
| --- | --- | --- |
| 无 | `ValueError: matmul: ... (size 2 is different from 3)`，出自 `layer2_forward` | `shard_rows` 的切分边界与 `shard_columns` 不一致 |
| 第 1 行 | `ValueError: ... along dimension 0, the array at index 0 has size 3 and the array at index 1 has size 2`，出自拼接 `dW1_shards` 的那一行 | `dW1` 的转置写反了 |
| 第 1–2 行 | 误差：`Y` 1.01，`dW1` 0.50，`dW2` 0.20，`dX` 0.28 | 前向结果就是错的：`layer2_forward` 缺了 all-reduce |
| 第 1–3 行 | `Y`、`dW2` 精确到 `1e-16`；`dW1` 0.77，`dX` 0.31 | 只有经过 `layer1_backward` 的量出错：激活函数的导数 |
| 第 1–4 行 | `Y`、`dW1`、`dW2` 都精确；`dX` 0.29 | 只有 $\bar X$ 错了：没有谁把它跨设备加起来 |
| 全部 5 个 | 四项误差都不超过 `1e-16` | — |

**分片边界不一致。** `shard_columns` 用 `np.array_split`，对 `D_HIDDEN = 7`、$n = 3$ 给出的隐藏维宽度是
$3, 2, 2$。切 $W_2$ 用的 `shard_rows` 却做整除（$7 \mathbin{//} 3 = 2$），切成固定的 2 一块，只覆盖了 7
行里的 6 行，与 $W_1$ 的列边界对不上。设备 0 的 $H_0$（来自 $W_1$ 的切分）有 3 列，而 $W_{2,0}$（来自不
一致的切分）只有 2 行，于是 $H_0 @ W_{2,0}$ 在按行切前向传播的第一次调用就失败了。

```py
def shard_rows(A, n):
    return np.array_split(A, n, axis=0)      # same split function as shard_columns, only the axis differs
```

**转置写反了。** 对 $Y = AB$ 有 $\bar B = A^\top \bar Y$；这里 $Y_k = X W_{1,k}$，所以
$\bar W_{1,k} = X^\top \bar Z_{1,k}$，形状 `(d_in, hidden_k)`。出 bug 的 $\bar Z_{1,k}^\top X$ 算的是它的
转置，形状 `(hidden_k, d_in)`。三个 `hidden_k` 的宽度不相等（3、2、2），把三块形状不对的结果沿 `axis=1`
拼接会直接失败——这个 bug 是被一次形状错误捕获的，而不是悄悄给出一个形状错误的 `dW1`。

```py
dW1_shards = [X.T @ dZ1k for dZ1k in dZ1_shards]     # (d_in, hidden_k), matches W1_shards[k]
```

**缺了 all-reduce。** 按行切的前向传播在每个设备上只算出部分和 $Y_k = H_k W_{2,k}$；$Y = \sum_k Y_k$ 需要
跨设备求和，这正是 `all_reduce` 做的事。漏掉它，每个设备手里就只剩自己那一项，量级大约是 $Y$ 的 $1/n$；
下游的每个量——$\bar Y$、两个权重梯度、$\bar X$——都是从这个错误的 $Y$ 算出来的，所以都带着同样的误差。
形状是对的，所以不会报错。

```py
def layer2_forward(H_shards, W2_shards):
    Y_partial = [Hk @ W2k for Hk, W2k in zip(H_shards, W2_shards)]
    return all_reduce(Y_partial)      # row-parallel forward: sum the partial products across devices
```

**激活函数的导数用错了张量。** `layer1_backward` 要算的是 $\bar Z_1 = \bar H \odot \tanh'(Z_1)$。正确的
导数 $\tanh'(z) = 1 - \tanh(z)^2 = 1 - h^2$ 是*输出* $h$ 的函数，而不是预激活值 $z$ 的函数；出 bug 的那一
行却用 $z$ 代替了 $h$，在 $z \ne h$ 的地方（也就是 `tanh` 真正起作用、弯曲输入的地方）都算成了 $1 - z^2$。
两个数组形状都是 `(B, hidden_k)`，所以不会报错：`dZ1` 悄悄地算错了，连累 `dW1` 和 `dX`，而 $Y$ 和 $\bar
W_2$ 都不依赖这一行，仍然精确。把 `tanh` 换成 `relu` 时，同样地写错反而看不出来——`z > 0` 和 `h > 0` 是同
一个 mask——那里真正会出事的写法是把导数写成激活函数本身 `np.where(z > 0, z, 0)`，它是按 $z$ 缩放梯度，而
不是做遮挡。

```py
dZ1_shards = [dHk * (1 - Hk ** 2) for dHk, Hk in zip(dH_shards, H_shards)]   # tanh'(z) = 1 - h^2, h = tanh(z)
```

**输入的梯度没有跨设备求和。** 每个设备乘的都是同一个 $X$，所以 $X$ 经由全部 $n$ 个本地乘法影响损失，它的
梯度是这些项之和 $\bar X = \sum_k \bar Z_{1,k} W_{1,k}^\top$：前向传播复制或拼接了什么，反向传播就要把
什么加回来。直接返回这一串本地乘积，每个设备手里就只有 $n$ 项里的一项；所有数组的形状都还是 `(B, d_in)`，
所以不会报错，而不读 $\bar X$ 的 $Y$、$\bar W_1$、$\bar W_2$ 仍然精确。

```py
dX_partial = [dZ1k @ W1k.T for dZ1k, W1k in zip(dZ1_shards, W1_shards)]
dX_shards = all_reduce(dX_partial)      # X is replicated, so its gradient is summed across devices
```

### 追问

- 第一层按列切、第二层按行切时，第一层的输出已经沿 `d_hidden` 分片，逐元素的激活函数保持这个切分方式不
  变，正好是第二层需要的输入形式——两层之间不发生任何通信。
- 前向传播里有一次 `all_reduce`（第二层的求和），反向传播里也有一次（第一层 `dX` 的求和）；这个 MLP 里
  其余的计算都是本地的。
- 偏置 $b$ 按它所属的那个权重来切：按列切时 $b$ 按 $W$ 的列切分方式切开、本地相加；按行切时（不切分的）
  $b$ 在前向的 `all_reduce` 之后只加一次，或者在归约之前每个设备都加 $b / n$，避免被重复加 $n$ 次。
- 环形（ring）实现下，一次 all-reduce 每个设备要发送约 $2(n-1)/n$ 倍数组大小的数据，all-gather 约 $(n-1)/n$ 倍：
  设备变多，每个设备的计算量变小，通信量却几乎不变。
- 如果激活函数不是逐元素的（比如沿 `d_hidden` 做 softmax），每个设备就需要完整的预激活那一行，两层之间
  原本不需要的通信就变成了一次额外的 `all_gather`。

<details>
<summary>验证代码（可运行）</summary>

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
