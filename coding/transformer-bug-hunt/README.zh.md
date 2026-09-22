# Transformer 找 bug

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 调试 · PyTorch | ★★★★☆ | 中等 | MLE · RS · RE | transformer, debugging, kv-cache, pytorch | 4 个 bug + 1 个追问 |
<!-- meta:end -->

## 题目

下面的文件 `tiny_gpt.py` 用 PyTorch 实现了一个小型的仅解码器（decoder-only）Transformer，并训练它把一串数字倒过来。

一条训练序列有 13 个 token：六个随机数字（token `0` 到 `9`）、分隔符 token `10`，以及同样六个数字的逆序。

```text
位置       0  1  2  3  4  5   6   7  8  9 10 11 12
token      7  0  2  2  5  8  10   8  5  2  2  0  7
```

模型读入前 12 个 token，在每个位置 $t$ 输出位置 $t + 1$ 上那个 token 的 logits。自注意力是*因果的*（causal）：
位置 $t$ 只能关注 $\le t$ 的位置。损失是最后六个目标（即逆序的那六个数字）上的交叉熵。`run_tests` 检查三件事：

1. 改动输入的最后一个 token，此前所有位置的 logits 都不变；
2. 训练结束时的损失低于 0.05；
3. 给定六个数字和分隔符，用 `generate` 做贪心解码（greedy decoding），500 条新序列里有 99% 以上补全得一个 token 都不错。

### Part 1 —— 找出并修复四个 bug

文件里有四个 bug：一个在位置嵌入（positional embedding）的创建处，两个在 `SelfAttention` 里，一个在训练循环里。
其中三个是某一行写错了，一个是少了一行。对每个 bug，指出位置，解释它对训练或输出造成了什么影响、原因是什么，然后修复。
四个都修好之后，`python tiny_gpt.py` 在它的 400 步之内（CPU 上几秒钟）损失降到 0.05 以下，并打印 `all tests passed`。
数据、测试和超参数都是正确的，不需要改动。

```py
import torch
import torch.nn as nn
import torch.nn.functional as F

N_DIGITS, SEP = 6, 10                       # tokens 0..9 are digits, token 10 is the separator
VOCAB, MAX_LEN = 11, 2 * N_DIGITS + 1


class SelfAttention(nn.Module):
    def __init__(self, d_model, n_head, max_len):
        super().__init__()
        self.n_head, self.d_head = n_head, d_model // n_head
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(self.d_head, d_model)
        # visible[i, j] is True when the query at position i may attend to the key at position j
        self.register_buffer("visible", torch.ones(max_len, max_len).tril().bool())

    def split_heads(self, x):               # (B, T, d_model) -> (B, n_head, T, d_head)
        return x.unflatten(-1, (self.n_head, self.d_head)).transpose(1, 2)

    def forward(self, x):
        T = x.shape[1]
        q, k, v = self.split_heads(self.w_q(x)), self.split_heads(self.w_k(x)), self.split_heads(self.w_v(x))
        scores = q @ k.transpose(-1, -2) / self.d_head ** 0.5           # (B, n_head, T, T)
        scores = scores.masked_fill(~self.visible[:T, :T], -1e-9)
        y = scores.softmax(dim=-1) @ v                                  # (B, n_head, T, d_head)
        return self.w_o(y.transpose(1, 2).flatten(-2))


class Block(nn.Module):
    def __init__(self, d_model, n_head, max_len):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        self.attn = SelfAttention(d_model, n_head, max_len)
        self.mlp = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model))

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


class TinyGPT(nn.Module):
    def __init__(self, vocab=VOCAB, d_model=64, n_head=4, n_layer=1, max_len=MAX_LEN):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab, d_model)
        self.pos_emb = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)
        self.blocks = nn.ModuleList([Block(d_model, n_head, max_len) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab)

    def forward(self, idx):                 # idx: (B, T) token ids -> logits (B, T, vocab)
        T = idx.shape[1]
        x = self.tok_emb(idx) + self.pos_emb[:, :T]
        for block in self.blocks:
            x = block(x)
        return self.head(self.ln_f(x))


def make_batch(batch_size, rng):            # each row: N_DIGITS random digits, SEP, the same digits reversed
    digits = torch.randint(0, 10, (batch_size, N_DIGITS), generator=rng)
    sep = torch.full((batch_size, 1), SEP)
    return torch.cat([digits, sep, digits.flip(1)], dim=1)


def train(model, steps=400, batch_size=64, lr=3e-3):
    rng = torch.Generator().manual_seed(0)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for step in range(steps):
        seq = make_batch(batch_size, rng)
        logits = model(seq[:, :-1])                                     # logits[:, t] predicts seq[:, t + 1]
        answer_logits, answer = logits[:, -N_DIGITS:], seq[:, -N_DIGITS:]   # only the reversed digits are scored
        loss = F.cross_entropy(answer_logits.reshape(-1, VOCAB), answer.reshape(-1))
        opt.zero_grad()
        opt.step()
        if step % 100 == 0 or step == steps - 1:
            print(f"step {step:3d}  loss {loss.item():.4f}")
    return loss.item()


@torch.no_grad()
def generate(model, prompt, n_new):         # greedy decoding: append the most likely next token, n_new times
    seq = prompt
    for _ in range(n_new):
        next_token = model(seq)[:, -1].argmax(dim=-1, keepdim=True)
        seq = torch.cat([seq, next_token], dim=1)
    return seq


@torch.no_grad()
def run_tests(model, final_loss):
    seq = make_batch(500, torch.Generator().manual_seed(1))
    a, b = seq[:, :-1].clone(), seq[:, :-1].clone()
    b[:, -1] = (b[:, -1] + 1) % 10                                      # a and b differ in the last token only
    early_a, early_b = model(a)[:, :-1], model(b)[:, :-1]               # logits at all positions before the change
    assert torch.allclose(early_a, early_b, atol=1e-5), "test 1: a later token changed earlier logits"
    assert final_loss < 0.05, "test 2: the loss did not converge"
    completed = generate(model, seq[:, :N_DIGITS + 1], N_DIGITS)
    accuracy = (completed == seq).all(dim=1).float().mean().item()
    assert accuracy > 0.99, f"test 3: only {accuracy:.1%} of the generated answers are right"


if __name__ == "__main__":
    torch.manual_seed(0)
    model = TinyGPT()
    final_loss = train(model)
    run_tests(model, final_loss)
    print("all tests passed")
```

### Part 2 —— 奇偶分类器

把修好的模型改成一个分类器，判断一个数是奇数还是偶数。输入 `idx` 的形状是 `(B, T)`，每一行是一个数的十进制数字，高位在前，
没有分隔符，允许前导零。例如 `7 0 2 2 5 8` 是偶数，`8 5 2 2 0 7` 是奇数。把词表输出头换成二分类的头；
在这个头之前，先把最终的隐藏状态（hidden states，即 `ln_f` 的输出，形状为 `(B, T, d_model)`）沿 $T$ 个位置取平均，
这一步称为*平均池化*（mean pooling）。相应地修改损失和预测。用随机的六位数训练，直到分类器对 1000 个新的数全部判断正确。

```py
class ParityClassifier(nn.Module):
    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        """idx: (B, T) digit tokens. Returns logits of shape (B, 2): class 0 = even, class 1 = odd."""
```

### Part 3 —— KV 缓存

`generate` 每生成一个新 token 就调用一次模型，每次调用都把此前所有位置的键（key）和值（value）重算一遍。
在因果注意力下，它们与后面的 token 无关，所以始终不变。*KV 缓存*（KV cache）为每一层保存已处理位置的键和值，
这样一次调用只需要处理新的 token。下面这个类是给定的，其中的方法 `update` 尚未实现。

```py
class KVCache:
    """Keys and values of all positions processed so far, one entry per layer."""

    def __init__(self, n_layer: int):
        self.k = [None] * n_layer       # per layer: (B, n_head, T_past, d_head), or None while empty
        self.v = [None] * n_layer

    @property
    def length(self) -> int:            # T_past
        return 0 if self.k[0] is None else self.k[0].shape[2]

    def update(self, layer: int, k: torch.Tensor, v: torch.Tensor):
        """k, v: (B, n_head, T_new, d_head), the new positions of this layer. Appends them to the cache
        and returns the keys and values of all T_past + T_new positions."""
        raise NotImplementedError
```

实现 `update`，并给 `TinyGPT.forward`、`Block.forward` 和 `SelfAttention.forward` 增加一个可选参数 `cache`。
调用 `model(idx, cache)` 时只传入新的 token，`idx` 的形状是 `(B, T_new)`；模型把它们的键和值追加进缓存，
返回这 `T_new` 个位置的 logits。对 `make_batch` 生成的任意一批 `seq`，结果必须与对整条序列做一次前向得到的对应切片相等：

```py
cache = KVCache(n_layer=len(model.blocks))
first = model(seq[:, :4], cache)                                        # four tokens in one call
rest = [model(seq[:, t:t + 1], cache) for t in range(4, seq.shape[1])]  # then one token per call
assert torch.allclose(torch.cat([first] + rest, dim=1), model(seq), atol=1e-5)
```

然后给 `generate` 加一个开关 `use_cache`：第一次调用处理整个提示（prompt），之后每次调用只处理最新的那个 token。

## 参考解答

<details>
<summary>展开参考解答</summary>

先把脚本跑起来，再细读代码：四个 bug 会一个接一个地暴露出来，症状各不相同。

### Part 1

| 已修复的 bug | `python tiny_gpt.py` 的输出 | 指向 |
| --- | --- | --- |
| 无 | `RuntimeError: mat1 and mat2 shapes cannot be multiplied (768x64 and 16x64)` | bug 1，`w_o` |
| 1 | 400 步里损失一直停在 2.55 附近；测试 1 失败 | bug 2，`backward()` |
| 1、2 | 损失降到 1.0 左右就停住；测试 1 失败 | bug 3，mask 的填充值 |
| 1、2、3 | 测试 1 通过；损失停在 1.4 附近；测试 2 失败 | bug 4，`pos_emb` |
| 全部 | 损失降到 0.0004；`all tests passed` | |

**Bug 1：`SelfAttention.__init__` 里的 `w_o`。** 调用栈的终点是 `SelfAttention.forward` 的最后一行，此时各个头已经重新拼在一起：
`y.transpose(1, 2).flatten(-2)` 的形状是 `(B, T, n_head * d_head) = (64, 12, 64)`，也就是报错信息里的 `768x64`；
而 `16x64` 是一个期望 `d_head = 16` 个输入特征的线性层转置后的权重。输出投影的作用是把各个头的信息混合起来，
所以它作用在所有头拼接之后的向量上，输入维度是 `d_model`。

```py
self.w_o = nn.Linear(d_model, d_model)      # was nn.Linear(self.d_head, d_model)
```

**Bug 2：`train` 里没有 `loss.backward()`。** `opt.step()` 根据每个参数的 `.grad` 来更新它，而只有 `loss.backward()` 才会填写 `.grad`。
少了这一行，`all(p.grad is None for p in model.parameters())` 始终为 `True`，Adam 会不声不响地跳过这些参数，于是没有任何参数发生变化。
损失只是随着每个 batch 的不同在初始值附近波动；对 11 个 token 均匀地猜，损失是 $\ln 11 \approx 2.40$。

```py
opt.zero_grad()                             # NOTE: before backward(); after it, it would erase the gradients
loss.backward()
opt.step()
```

**Bug 3：`SelfAttention.forward` 里的填充值 `-1e-9`。** softmax 给分数为 $s$ 的位置分配的权重正比于 $e^{s}$。
`-1e-9` 是一个绝对值极小的数，而不是一个很大的负数：$e^{-10^{-9}} \approx 1$，与一个分数为 0 的可见位置权重相同；
只有 $-\infty$ 才能得到 $e^{-\infty} = 0$。在未训练的模型里所有分数都接近 0，位置 0 的查询（query）把 0.92 的权重（约 11/12）
放在了它不该看到的 11 个位置上。训练时，位置 $t + 1$ 的输入恰好就是位置 $t$ 的目标，于是模型直接从输入里读出答案，而不是把它算出来。
只有这一个 bug 时损失仍然会下降（400 步后为 0.15），但测试 1 失败；而 `generate` 时后面的 token 并不存在，500 个提示一个也没有补全对。

```py
scores = scores.masked_fill(~self.visible[:T, :T], float("-inf"))      # was -1e-9
```

**Bug 4：`TinyGPT.__init__` 里 `pos_emb` 的形状 `(1, 1, d_model)`。** 对长度为 1 的维度做切片 `[:, :T]`，得到的长度仍然是 1，
随后广播（broadcasting）把这同一个向量加到了每个位置上，所以不会有任何报错。每个位置上都相同的向量不含任何位置信息：
注意力只能按内容给各个键分配权重，单层模型在分隔符处的输出只取决于它前面有哪些数字，与它们的顺序无关。
提示 `7 0 2 2 5 8 10` 和 `8 5 2 2 0 7 10` 在该位置给出相同的 logits（相差 $2 \cdot 10^{-7}$），而正确的下一个 token 分别是 8 和 7。
模型只能在还没输出的数字里猜，损失停在 1.4 附近。取 `n_layer=2` 时症状要轻一些：400 步后损失为 0.39，修复后是 0.0005。
这是因为因果 mask 本身会泄露一部分位置信息：位置 $t$ 恰好是对 $t + 1$ 个 token 取平均。

```py
self.pos_emb = nn.Parameter(torch.randn(1, max_len, d_model) * 0.02)    # one row per position; was (1, 1, d_model)
```

### Part 2

一共三处改动。输出头由 `VOCAB` 个输出改为两个输出。隐藏状态在进入输出头之前先沿时间维取平均。
损失是每条序列的一行 logits 对每条序列的一个标签，因此原来的 reshape 和截取答案位置的切片都不需要了。
下面的包装类不改动 `TinyGPT`：它把词表输出头换成 `nn.Identity()`，这样模型主体返回的就是隐藏状态。

```python
import torch.nn as nn


class ParityClassifier(nn.Module):
    def __init__(self, **kwargs):
        super().__init__()
        self.body = TinyGPT(**kwargs)
        d_model = self.body.head.in_features
        self.body.head = nn.Identity()              # drop the vocabulary head: body(idx) now returns hidden states
        self.cls = nn.Linear(d_model, 2)            # class 0 = even, class 1 = odd

    def forward(self, idx):                         # idx: (B, T) digits -> logits (B, 2)
        hidden = self.body(idx)                     # (B, T, d_model)
        return self.cls(hidden.mean(dim=1))         # NOTE: average over time (dim=1), not over features (dim=-1)
```

```py
labels = digits[:, -1] % 2                          # NOTE: one label per sequence; the last digit decides
loss = F.cross_entropy(model(digits), labels)       # logits (B, 2) against labels (B,)
pred = model(digits).argmax(dim=-1)                 # 0 = even, 1 = odd
```

沿用 Part 1 的优化器设置训练 200 步，分类器对 1000 个新的数全部判断正确。输出头是仿射变换，所以先池化再过输出头，
与先逐位置算 logits 再取平均，结果相同。在因果 mask 下只有最后一个位置看到了完整的数，因此因果模型通常取 `hidden[:, -1]` 作为读出；
在这里平均池化同样可行。

### Part 3

带缓存的一次调用只收到 $T$ 个新 token，另有 `past` 个位置已经存在缓存里。查询只需要为新位置计算，
键和值则要覆盖全部 `past + T` 个位置，所以分数的形状是 `(T, past + T)`。需要改三处：注意力把新的键和值追加进缓存，并使用完整的键和值；
mask 和位置嵌入按绝对位置 `past .. past + T - 1` 取下标，而不是 `0 .. T - 1`；`cache` 连同层号一起，
从 `TinyGPT` 经过 `Block` 一路传到 `SelfAttention`。

```py
class KVCache:
    def update(self, layer: int, k: torch.Tensor, v: torch.Tensor):
        if self.k[layer] is not None:
            k = torch.cat([self.k[layer], k], dim=2)        # NOTE: dim 2 is time in (B, n_head, T, d_head)
            v = torch.cat([self.v[layer], v], dim=2)
        self.k[layer], self.v[layer] = k, v
        return k, v


class SelfAttention(nn.Module):
    def forward(self, x, cache=None, layer=0):
        T = x.shape[1]                                                  # number of new positions
        q, k, v = ...                                                   # as before, from the T new tokens
        if cache is not None:
            k, v = cache.update(layer, k, v)                            # k, v now cover positions 0 .. past + T - 1
        past = k.shape[2] - T
        scores = q @ k.transpose(-1, -2) / self.d_head ** 0.5           # (B, n_head, T, past + T)
        # NOTE: new query i sits at absolute position past + i, so take rows past.. of the mask, not rows 0..
        scores = scores.masked_fill(~self.visible[past:past + T, :past + T], float("-inf"))
        ...                                                             # softmax, merge heads, w_o: unchanged


class Block(nn.Module):
    def forward(self, x, cache=None, layer=0):
        x = x + self.attn(self.ln1(x), cache, layer)                    # pass-through only
        return x + self.mlp(self.ln2(x))


class TinyGPT(nn.Module):
    def forward(self, idx, cache=None):     # idx: (B, T) token ids -> logits (B, T, vocab)
        T = idx.shape[1]
        past = cache.length if cache is not None else 0                 # NOTE: read before the blocks update it
        x = self.tok_emb(idx) + self.pos_emb[:, past:past + T]          # NOTE: positions past.., not 0..
        for layer, block in enumerate(self.blocks):
            x = block(x, cache, layer)
        return self.head(self.ln_f(x))


@torch.no_grad()
def generate(model, prompt, n_new, use_cache=False):
    cache = KVCache(len(model.blocks)) if use_cache else None
    seq, new = prompt, prompt                                           # the first call processes the whole prompt
    for _ in range(n_new):
        logits = model(new, cache) if use_cache else model(seq)
        new = logits[:, -1].argmax(dim=-1, keepdim=True)                # NOTE: later calls feed only this one token
        seq = torch.cat([seq, new], dim=1)
    return seq
```

题目里的那段检查在两层的模型上通过，`generate` 用不用缓存返回的 token 都相同。解码一步时注意力的代价由 $O(T^2)$ 降为 $O(T)$，
缓存里保存 `2 * n_layer * B * T * d_model` 个数。

### 追问

- 为什么用 `float("-inf")` 而不用 `-1e9`：在 float16 下，`scores.masked_fill(mask, -1e9)` 会报
  `RuntimeError: value cannot be converted to type c10::Half without overflow`。代价是：如果某一行的所有位置都被屏蔽（padding mask 可能造成），
  softmax 之后这一行会变成 NaN。
- 同类的其他 bug：在错误的维度上做归约、漏掉缩放因子 `d_head ** 0.5`、变量名里一个字符的笔误。
  把本文件改成 `softmax(dim=-2)`，损失照样能降到 0.0014，但测试 1 失败，`generate` 只有 2% 的提示补全正确。
- `torch.cat` 每一步都会把整个缓存复制一遍。实际系统会一次性分配 `(B, n_head, max_len, d_head)`，再把新的键和值写进切片 `[:, :, past:past + T]`。
- 长度不同的数需要填充（padding）。填充位置在注意力里要作为键被屏蔽，在 Part 2 取平均时也要排除。

<details>
<summary>完成 Part 1 和 Part 3 之后的完整文件，以及验证代码（可运行）</summary>

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

N_DIGITS, SEP = 6, 10                       # tokens 0..9 are digits, token 10 is the separator
VOCAB, MAX_LEN = 11, 2 * N_DIGITS + 1


class KVCache:                              # Part 3: the given class, with update() filled in
    """Keys and values of all positions processed so far, one entry per layer."""

    def __init__(self, n_layer: int):
        self.k = [None] * n_layer       # per layer: (B, n_head, T_past, d_head), or None while empty
        self.v = [None] * n_layer

    @property
    def length(self) -> int:            # T_past
        return 0 if self.k[0] is None else self.k[0].shape[2]

    def update(self, layer: int, k: torch.Tensor, v: torch.Tensor):
        """k, v: (B, n_head, T_new, d_head), the new positions of this layer. Appends them to the cache
        and returns the keys and values of all T_past + T_new positions."""
        if self.k[layer] is not None:
            k = torch.cat([self.k[layer], k], dim=2)        # NOTE: dim 2 is time in (B, n_head, T, d_head)
            v = torch.cat([self.v[layer], v], dim=2)
        self.k[layer], self.v[layer] = k, v
        return k, v


class SelfAttention(nn.Module):
    def __init__(self, d_model, n_head, max_len):
        super().__init__()
        self.n_head, self.d_head = n_head, d_model // n_head
        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)                          # bug 1: was nn.Linear(self.d_head, d_model)
        # visible[i, j] is True when the query at position i may attend to the key at position j
        self.register_buffer("visible", torch.ones(max_len, max_len).tril().bool())

    def split_heads(self, x):               # (B, T, d_model) -> (B, n_head, T, d_head)
        return x.unflatten(-1, (self.n_head, self.d_head)).transpose(1, 2)

    def forward(self, x, cache=None, layer=0):
        T = x.shape[1]                                                  # number of new positions
        q, k, v = self.split_heads(self.w_q(x)), self.split_heads(self.w_k(x)), self.split_heads(self.w_v(x))
        if cache is not None:
            k, v = cache.update(layer, k, v)                            # k, v now cover positions 0 .. past + T - 1
        past = k.shape[2] - T
        scores = q @ k.transpose(-1, -2) / self.d_head ** 0.5           # (B, n_head, T, past + T)
        # NOTE: new query i sits at absolute position past + i, so take rows past.. of the mask, not rows 0..
        scores = scores.masked_fill(~self.visible[past:past + T, :past + T], float("-inf"))     # bug 3: was -1e-9
        y = scores.softmax(dim=-1) @ v                                  # (B, n_head, T, d_head)
        return self.w_o(y.transpose(1, 2).flatten(-2))


class Block(nn.Module):
    def __init__(self, d_model, n_head, max_len):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        self.attn = SelfAttention(d_model, n_head, max_len)
        self.mlp = nn.Sequential(nn.Linear(d_model, 4 * d_model), nn.GELU(), nn.Linear(4 * d_model, d_model))

    def forward(self, x, cache=None, layer=0):
        x = x + self.attn(self.ln1(x), cache, layer)                    # pass-through only
        return x + self.mlp(self.ln2(x))


class TinyGPT(nn.Module):
    def __init__(self, vocab=VOCAB, d_model=64, n_head=4, n_layer=1, max_len=MAX_LEN):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab, d_model)
        self.pos_emb = nn.Parameter(torch.randn(1, max_len, d_model) * 0.02)    # bug 4: was randn(1, 1, d_model)
        self.blocks = nn.ModuleList([Block(d_model, n_head, max_len) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab)

    def forward(self, idx, cache=None):     # idx: (B, T) token ids -> logits (B, T, vocab)
        T = idx.shape[1]
        past = cache.length if cache is not None else 0                 # NOTE: read before the blocks update it
        x = self.tok_emb(idx) + self.pos_emb[:, past:past + T]          # NOTE: positions past.., not 0..
        for layer, block in enumerate(self.blocks):
            x = block(x, cache, layer)
        return self.head(self.ln_f(x))


def make_batch(batch_size, rng):            # each row: N_DIGITS random digits, SEP, the same digits reversed
    digits = torch.randint(0, 10, (batch_size, N_DIGITS), generator=rng)
    sep = torch.full((batch_size, 1), SEP)
    return torch.cat([digits, sep, digits.flip(1)], dim=1)


def train(model, steps=400, batch_size=64, lr=3e-3):
    rng = torch.Generator().manual_seed(0)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    for step in range(steps):
        seq = make_batch(batch_size, rng)
        logits = model(seq[:, :-1])                                     # logits[:, t] predicts seq[:, t + 1]
        answer_logits, answer = logits[:, -N_DIGITS:], seq[:, -N_DIGITS:]   # only the reversed digits are scored
        loss = F.cross_entropy(answer_logits.reshape(-1, VOCAB), answer.reshape(-1))
        opt.zero_grad()
        loss.backward()                                                 # bug 2: this line was missing
        opt.step()
        if step % 100 == 0 or step == steps - 1:
            print(f"step {step:3d}  loss {loss.item():.4f}")
    return loss.item()


@torch.no_grad()
def generate(model, prompt, n_new, use_cache=False):
    cache = KVCache(len(model.blocks)) if use_cache else None
    seq, new = prompt, prompt                                           # the first call processes the whole prompt
    for _ in range(n_new):
        logits = model(new, cache) if use_cache else model(seq)
        new = logits[:, -1].argmax(dim=-1, keepdim=True)                # NOTE: later calls feed only this one token
        seq = torch.cat([seq, new], dim=1)
    return seq


@torch.no_grad()
def run_tests(model, final_loss):
    seq = make_batch(500, torch.Generator().manual_seed(1))
    a, b = seq[:, :-1].clone(), seq[:, :-1].clone()
    b[:, -1] = (b[:, -1] + 1) % 10                                      # a and b differ in the last token only
    early_a, early_b = model(a)[:, :-1], model(b)[:, :-1]               # logits at all positions before the change
    assert torch.allclose(early_a, early_b, atol=1e-5), "test 1: a later token changed earlier logits"
    assert final_loss < 0.05, "test 2: the loss did not converge"
    completed = generate(model, seq[:, :N_DIGITS + 1], N_DIGITS)
    accuracy = (completed == seq).all(dim=1).float().mean().item()
    assert accuracy > 0.99, f"test 3: only {accuracy:.1%} of the generated answers are right"


if __name__ == "__main__":
    torch.manual_seed(0)
    model = TinyGPT()
    final_loss = train(model)
    run_tests(model, final_loss)
    print("all tests passed")
```

```python
torch.manual_seed(0)
model = TinyGPT()
final_loss = train(model)
run_tests(model, final_loss)                        # Part 1: the three tests of the file pass

# Part 2: train the classifier, then label 1000 new numbers
clf = ParityClassifier()
opt = torch.optim.Adam(clf.parameters(), lr=3e-3)
rng = torch.Generator().manual_seed(2)
for _ in range(200):
    digits = torch.randint(0, 10, (64, N_DIGITS), generator=rng)
    loss = F.cross_entropy(clf(digits), digits[:, -1] % 2)
    opt.zero_grad()
    loss.backward()
    opt.step()
numbers = torch.randint(0, 10, (1000, N_DIGITS), generator=rng)
with torch.no_grad():
    assert torch.equal(clf(numbers).argmax(dim=-1), numbers[:, -1] % 2)

# Part 3: four tokens in one call, then one token per call, against one full forward pass (two layers)
deep = TinyGPT(n_layer=2)
seq = make_batch(8, rng)
with torch.no_grad():
    cache = KVCache(n_layer=2)
    first = deep(seq[:, :4], cache)
    rest = [deep(seq[:, t:t + 1], cache) for t in range(4, seq.shape[1])]
    assert cache.length == seq.shape[1]
    assert torch.allclose(torch.cat([first] + rest, dim=1), deep(seq), atol=1e-5)
prompts = seq[:, :N_DIGITS + 1]
assert torch.equal(generate(model, prompts, N_DIGITS, use_cache=True), generate(model, prompts, N_DIGITS))
assert torch.equal(generate(model, prompts, N_DIGITS, use_cache=True), seq)
```

</details>

</details>
