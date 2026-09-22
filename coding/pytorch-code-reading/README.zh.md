# PyTorch 读代码与扩展

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 读代码 · PyTorch | ★☆☆☆☆ | — | RE · MLE | code-reading, pytorch, complexity | 3 个部分 + 附加题 |
<!-- meta:end -->

## 题目

下面的文件训练一个分类器，它的训练标签来自多个标注者，而不是单一的真实标签。有 $N$ 个样本，每个样本是
$\mathbb{R}^D$ 中的一个特征向量；真实类别取值于 $\lbrace 0, \dots, C-1 \rbrace$，训练时不可见。有 $A$ 个标注者，
标注结果存放在形状为 `(N, A)` 的整数张量 `Y` 里：`Y[i, a]` 是标注者 `a` 给样本 `i` 标的类别，标注者 `a` 没有标过样本 `i` 时为
`-1`（每个样本至少有 2 个标签）。每个标注者 `a` 有一个*混淆矩阵*（confusion matrix） $M_a \in \mathbb{R}^{C \times C}$：
真实类别是 $c$ 时，标注者 `a` 上报类别 $o$ 的概率是 $M_a[c, o]$，即 $M_a$ 的每一行 $c$ 求和为 1。可靠的标注者
的 $M_a$ 接近单位阵，不可靠的接近每一行都均匀分布。

一个小分类器 `Net` 把 `X` 映射到类别概率 `p`（形状 `(N, C)`）。混淆矩阵是另一组可学习参数，由 `CrowdLayer`
持有。训练时从不使用真实类别：对每一个实际观察到的 `(i, a)` 标注对，标注者 `a` 上报各类别的预测分布是
`p[i] @ M[a]`，损失是 `a` 实际上报的那个标签的负对数似然。

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

Part 1 是关于上面这份代码的问题，Part 2 和 Part 3 在它的基础上扩展和重构。

### Part 1 —— 读代码：数据流、形状与复杂度

回答下面的问题。文件里定义的常量用 $N, D, C, A, H$ 表示，`(Y >= 0).sum()`（即实际观察到的
样本-标注者标注对的个数）用 $P$ 表示。

1. 从 `X` 开始，一直到 `opt.step()` 施加的更新，数据依次经过了哪些函数和张量？`y` 在哪一步（如果有的话）参与进来？
2. `net(X)`、`p = F.softmax(net(X), dim=-1)`、`crowd()` 这三个张量的形状分别是什么？
3. `nll_loop` 内部的 `q = p[i] @ M[a]` 是一次矩阵运算，它两个操作数的形状是什么？这次运算的时间复杂度是多少，
   `q` 占用多少内存（用 $C$ 表示）？
4. `net.l1` 和 `net.l2` 内部的矩阵乘法，各自的时间复杂度和前向输出占用的内存是多少（用 $N, D, H, C$ 表示）？
   反向传播还需要额外保留哪些张量？
5. `nll_loop` 整体的时间复杂度是多少？分别给出一个用 $N, A, C$ 表示的宽松上界，和一个用 $P$ 表示的更紧的界。
6. `nll_loop` 本身不曾物化任何 $O(N \cdot A \cdot C)$ 规模的张量。如果改成用 `einsum` 一次性对所有 $(i, a)$
   组合算出 `p[i] @ M[a]`，算完之后再用掩码筛掉没有标签的部分，这个中间张量占多少内存？这部分开销能不能避免？
7. 一次训练迭代里，`net` 的前向传播做了多少次乘加，`nll_loop` 又做了多少次？实际测出来哪一步更耗时？
   为什么这两个答案对不上？

### Part 2 —— 扩展：从学到的混淆矩阵估计标注者可靠度

给 `CrowdLayer` 加一个方法，直接从它学到的混淆矩阵估计每个标注者的可靠度，再写一个函数找出其中最不可靠的那个。
标注者的可靠度定义为：在 $C$ 个类别上取平均，它上报真实类别的概率：$\frac{1}{C}\sum_c M_a[c, c]$。
把 `reliability` 写成一个普通函数，再用 `CrowdLayer.reliability = reliability` 把它挂到类上。

```py
def reliability(self) -> torch.Tensor:
    """Attached as CrowdLayer.reliability. Returns r of shape (A,), r[a] in [0, 1]: the estimated
    reliability of annotator a, computed from self.forward(), the learned confusion matrices."""


def least_reliable(r: torch.Tensor) -> int:
    """r: (A,). Returns the index of the annotator with the lowest estimated reliability."""
```

上面的数据里，每个标注者的真实可靠度是固定的，存在 `RELIABILITY` 里；用它来检验 `least_reliable`
找出的是不是正确的那一个。

### Part 3 —— 重构：把 `nll_loop` 向量化

`nll_loop` 用一层 Python 循环遍历每个样本，内层再用一层循环遍历每个标注者来算损失。把它改写成 `nll_vectorized`，
不能对样本或标注者写任何 Python 循环——可以用索引、`gather`、`einsum` 或批量矩阵乘 `torch.bmm`——对任意形状
匹配的 `p`、`M`、`Y`，返回与 `nll_loop` 相同（在浮点误差内）的标量。

```py
def nll_vectorized(p: torch.Tensor, M: torch.Tensor, Y: torch.Tensor) -> torch.Tensor:
    """p: (N, C) class probabilities. M: (A, C, C) confusion matrices. Y: (N, A) observed labels,
    -1 for missing. Returns the same scalar as nll_loop(p, M, Y)."""
```

### Bonus —— 三个常见算子的复杂度

回答下面三个问题，不需要依赖上面的代码；每一问给出结论和一行理由。

1. 自注意力（self-attention）：序列长度为 $L$，隐藏维度为 $d$，分成 $h$ 个头，每个头的维度是 $d / h$。
   一次前向传播的时间复杂度是多少？反向传播需要的显存主要由哪一项决定？
2. 一个二维卷积层：输入 $(B, C_{in}, H_{in}, W_{in})$，卷积核 $k \times k$，输出通道数 $C_{out}$，
   输出空间尺寸 $H_{out} \times W_{out}$。一次前向传播的时间复杂度是多少？
3. 批量矩阵乘 `(B, n, m) @ (B, m, p)`：它的时间复杂度是多少，输出占用多少内存？

## 参考解答

<details>
<summary>展开参考解答</summary>

值得向面试官确认的一点：标注者的可靠度是像 Part 2 定义的那样对各类别取平均后的一个标量，还是需要按类别单独给出。
动手回答 Part 1 之前，先把 `run` 从头到尾读一遍，弄清楚哪些张量是优化器在更新的，哪些只是常量。

### Part 1

1. `make_data` 构造出 `X`（`(N, D)`）、观察到的标签 `Y`（`(N, A)`），并使用固定的 `M_TRUE`；真实类别 `y`
   之后只在 `train_acc` 和 `test_acc` 里出现，从未参与损失。在 `run` 里，`X` 经过 `net` 得到 logits，
   再 `softmax` 得到 `p`（`(N, C)`）；`crowd()` 给出 `M`（`(A, C, C)`）；`nll_loop(p, M, Y)` 把 `p`、`M`、`Y`
   合并成标量 `loss`；`loss.backward()` 把梯度写进 `net` 和 `crowd` 两者的参数，`opt.step()` 再用这些梯度更新参数。
2. `net(X)`：`(N, C) = (400, 4)`。`p`：形状相同，`(N, C) = (400, 4)`。`crowd()`：`(A, C, C) = (5, 4, 4)`。
3. `p[i]` 形状 `(C,)`，`M[a]` 形状 `(C, C)`：这是一次 `(m,) @ (m, k)` 的向量-矩阵乘，这里 $m = k = C$，
   时间 $O(C^2)$；结果 `q` 是长度为 $C$ 的向量，占用 $O(C)$。
4. `net.l1`：`(N, D) @ (D, H)`，时间 $O(NDH)$，前向输出 `(N, H)`，占用 $O(NH)$。`net.l2`：`(N, H) @ (H, C)`，
   时间 $O(NHC)$，输出 `(N, C)`，占用 $O(NC)$。反向传播要保留 `l1` 的输入（`X`，$O(ND)$）、`ReLU` 的输出
   （$O(NH)$；它既是 `l2` 的输入，也用来决定梯度能否通过 `ReLU`，所以激活前的值不必保留）和 softmax 的输出 `p`（$O(NC)$），
   都与前向的激活同阶。
5. 宽松上界 $O(NAC^2)$：双重循环最多跑 $N \cdot A$ 次，每一次不 `continue` 的迭代都做一次 $O(C^2)$ 的
   向量-矩阵乘。因为 `lab < 0` 时会直接 `continue`，更紧的界是 $O(PC^2)$，$P$ 是真正跑到乘法那一步的迭代次数。
   这里 $N \cdot A = 2000$，$P = 998$——相差约 2 倍。
6. 一次性对所有组合计算 `p[i] @ M[a]`，比如用 `einsum('nc,acd->nad', p, M)`，得到的张量形状是 `(N, A, C)`，
   占用 $O(NAC)$ 内存。在这个规模下是 $2000 \times 4 = 8000$ 个浮点数，不算什么，但它与真正需要的 $O(PC)$
   之间的比例会随 $N \cdot A / P$ 增长：标注者远多于每条样本实际拥有的标注数时，这张网格里大部分位置都对应
   没有标签的组合。这部分开销可以避免——在做任何计算之前先选出这 $P$ 个有效组合，这正是 Part 3 要做的事。
7. `net` 的前向传播约做 $NDH + NHC = 134{,}400$ 次乘加；`nll_loop` 紧的上界是 $PC^2 = 998 \times 16 = 15{,}968$，
   少了约 8 倍。但实测一次训练迭代：`net` 的前向传播约 0.4 毫秒，`nll_loop` 算出损失约 34 毫秒，
   反向传播约 67 毫秒——尽管算得更少，`nll_loop` 反而把总时间拖慢了两个数量级。原因是它的 $P$ 次乘法是
   $P$ 次各自独立的 Python 级张量调用，每一次都要付出解释器和 autograd 记录节点的固定开销；而 `net` 的两个
   线性层只是两次对同一个批量矩阵乘内核的调用。乘加次数和实际用时不是一回事。

### Part 2

标注者的混淆矩阵是一个随机矩阵，它的第 $c$ 行是真实类别为 $c$ 时它的上报分布；对角线上的 $M_a[c, c]$ 就是
它答对类别 $c$ 的概率，对对角线取平均就得到每个标注者的一个可靠度数字，而且全程没有用到 `y`。

```python
def reliability(self):
    return self.forward().diagonal(dim1=-2, dim2=-1).mean(-1)


CrowdLayer.reliability = reliability          # attach to the CrowdLayer class given in the problem


def least_reliable(r):
    return int(r.argmin().item())
```

在题目里训练好的 `crowd` 上，`crowd.reliability()` 约为 `[0.94, 0.82, 0.58, 0.31, 0.26]`，而真实值
`RELIABILITY = [0.95, 0.8, 0.6, 0.4, 0.15]`：排序一致，`least_reliable` 返回 `4`，换三个种子、训练更少
轮次也是同样的结果。最后两个估计值（0.31 和 0.26）之间的差距比真实值（0.4 和 0.15）小——
一个标注次数本来就少、上报又接近均匀分布的标注者，能提供给 $M_a$ 对应行的证据本就不多——但 `least_reliable`
需要的排序始终是对的。

### Part 3

思路：不再对 $(i, a)$ 写 Python 循环，而是用 `nonzero` 一次性取出全部 $P$ 个有效组合，取出 `p` 对应的行和
`M` 对应的矩阵，把这 $P$ 次向量-矩阵乘当成一次批量矩阵乘算出来。

```python
def nll_vectorized(p, M, Y):
    idx_i, idx_a = (Y >= 0).nonzero(as_tuple=True)                    # P pairs, P = (Y >= 0).sum()
    lab = Y[idx_i, idx_a]
    q = torch.bmm(p[idx_i].unsqueeze(1), M[idx_a]).squeeze(1)         # (P, 1, C) @ (P, C, C) -> (P, C)
    return -torch.log(q.gather(1, lab.unsqueeze(1)).squeeze(1) + 1e-8).sum()
```

`p[idx_i]` 和 `M[idx_a]` 是高级索引，产生形状 `(P, C)` 和 `(P, C, C)` 的新张量；`torch.bmm` 把最前面
的维度当成 $P$ 个互相独立的 `(1, C) @ (C, C)` 乘积一起算；`gather` 从 `q` 的这 $P$ 行里，各自取出标注者
实际上报的那个类别对应的概率。渐进时间与 `nll_loop` 紧的上界一样，都是 $O(PC^2)$——乘加次数没有变——中间
张量占用 $O(PC)$，而不是 Part 1 问题 6 里的 $O(NAC)$，因为 `nonzero` 在做任何算术之前就先选出了这 $P$
个组合。变化的地方在于：这 $P$ 次乘法现在是对 `torch.bmm` 的一次调用，而不是 $P$ 次 Python 级调用。
在题目里训练好的 `p`、`M`、`Y` 上和 `nll_loop` 核对，两者在浮点误差内一致，对 `p`、`M` 的梯度也一致。
预热几次之后重复测量 30 次取平均，`nll_loop` 约 21 毫秒，`nll_vectorized` 远小于 1 毫秒——在这个规模下
（$N = 400$、$A = 5$、$P = 998$）快了一百倍以上，几乎全部来自 Part 1 问题 7 里说的 Python 循环开销，
而不是算法本身的差别。

### Bonus

1. 时间 $O(L^2 d + Ld^2)$：拆成 $h$ 个维度为 $d / h$ 的头不会改变第一项，因为每个头的 $QK^\top$ 和
   注意力权重 $\times V$ 各花 $O(L^2 \cdot d/h)$，一共 $h$ 个头；$Q$、$K$、$V$ 和输出这四次投影各花
   $O(Ld^2)$，与 $h$ 无关。反向传播所需的显存由 $O(hL^2)$ 主导：每个头 softmax 之后的注意力权重都要保留下来，
   供 softmax 的反向传播使用，这一项随 $h$ 线性增长，不只是随 $d$ 增长。这正是 FlashAttention 一类融合算子
   要避免物化的张量——它们在反向传播时重新算一遍，把显存降到 $O(Ld)$。
2. 时间 $O(B \cdot C_{in} \cdot C_{out} \cdot k^2 \cdot H_{out} \cdot W_{out})$：$B \cdot C_{out} \cdot H_{out} \cdot W_{out}$
   个输出位置里的每一个，都是对 $C_{in} \cdot k^2$ 个输入元素求和。
3. 时间 $O(Bnmp)$：$B$ 个互相独立的 $(n, m) @ (m, p)$ 乘积，每个 $O(nmp)$。输出形状 $(B, n, p)$，占用
   $O(Bnp)$ 内存。

### 追问

- 先用 `einsum('nc,acd->nad', p, M)` 算出完整的网格，再用掩码筛选，在数学上与 Part 3 的做法等价，
  但内存又回到了 $O(NAC)$；唯一的区别是在算术之前还是之后筛选有效组合。
- `q.gather(1, lab.unsqueeze(1))` 也可以写成 `q[torch.arange(len(lab)), lab]`，效果相同，`gather`
  在维度更高时更好推广。
- 用小批量（mini-batch）训练而不是整个 `X`，能让每一步 `nll_loop`/`nll_vectorized` 的开销随批大小成比例
  下降，但不会改变 Part 1 问题 5、6 的复杂度结论，只是把同样的常数摊到了更多步里。
- $C$ 变大时，`nll_loop` 和 `nll_vectorized` 里的 `1e-8` 下界可能不够用；更稳妥的做法是全程用对数概率
  （log-softmax、`logsumexp`），而不是先算出概率再取一次对数。

<details>
<summary>验证代码（可运行）</summary>

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
