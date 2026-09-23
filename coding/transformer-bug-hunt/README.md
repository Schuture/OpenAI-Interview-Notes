# Transformer Bug Hunt

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Debugging · PyTorch | ★★★★☆ | Medium | MLE · RS · RE | transformer, debugging, kv-cache, pytorch | 4 bugs + 2 follow-ups |
<!-- meta:end -->

## Problem

The file `tiny_gpt.py` below implements a small decoder-only Transformer in PyTorch and trains it to
reverse a string of digits.

A training sequence has 13 tokens: six random digits (tokens `0` to `9`), the separator token `10`, and
the same six digits in reverse order.

```text
position   0  1  2  3  4  5   6   7  8  9 10 11 12
token      7  0  2  2  5  8  10   8  5  2  2  0  7
```

The model receives the first 12 tokens and outputs, at every position $t$, the logits for the token at
position $t + 1$. Self-attention is *causal*: position $t$ may attend to positions $\le t$ only. The loss
is the cross-entropy over the last six targets, which are the reversed digits. `run_tests` checks three
things:

1. changing the last input token leaves the logits at all earlier positions unchanged;
2. the final training loss is below 0.05;
3. given the six digits and the separator, greedy decoding with `generate` completes more than 99% of
   500 new sequences without a single wrong token.

### Part 1 — Find and fix four bugs

The file contains four bugs: one in the set-up of the positional embedding, two in `SelfAttention`, and
one in the training loop. Three of them are a wrong line and one is a missing line. For each bug, give
its location, explain what it does to training or to the output and why, and fix it. With all four fixed,
`python tiny_gpt.py` reaches a loss below 0.05 within its 400 steps (a few seconds on a CPU) and prints
`all tests passed`. The data, the tests and the hyperparameters are correct and need no change.

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

### Part 2 — Odd/even classifier

Turn the fixed model into a classifier that labels a number as odd or even. The input `idx` of shape
`(B, T)` holds the decimal digits of each number, most significant digit first, without a
separator; leading zeros are allowed. For example, `7 0 2 2 5 8` is even and `8 5 2 2 0 7` is odd.
Replace the vocabulary head with a two-class head. Before that head, average the final hidden states
(the output of `ln_f`, of shape `(B, T, d_model)`) over the $T$ positions, which is called *mean
pooling*. Change the loss and the prediction to match. Train on random six-digit numbers until the
classifier labels 1000 new numbers without an error.

```py
class ParityClassifier(nn.Module):
    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        """idx: (B, T) digit tokens. Returns logits of shape (B, 2): class 0 = even, class 1 = odd."""
```

### Part 3 — KV cache

`generate` calls the model once per new token, and every call recomputes the keys and values of all
earlier positions. Under causal attention they do not depend on later tokens, so they never change. A
*KV cache* stores, for every layer, the keys and values of the positions processed so far, so that a
call only has to process the new tokens. The class below is given, and its method `update` is missing.

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

Implement `update`, and add an optional argument `cache` to `TinyGPT.forward`, `Block.forward` and
`SelfAttention.forward`. A call `model(idx, cache)` receives only the new tokens `idx` of shape
`(B, T_new)`, appends their keys and values to the cache, and returns the logits of these `T_new`
positions. A sequence is handed over as chunks of arbitrary lengths, in order, one call per chunk, and
a call processes its own `T_new` positions only: the keys and values of the earlier positions are read
from the cache, never recomputed. For any batch `seq` from `make_batch`, the logits of the chunks must
equal the matching slices of a forward pass over the whole sequence:

```py
cache = KVCache(n_layer=len(model.blocks))
chunks = [(0, 3), (3, 4), (4, 9), (9, 11), (11, 13)]        # chunk lengths 3, 1, 5, 2, 2
out = [model(seq[:, a:b], cache) for a, b in chunks]
assert torch.allclose(torch.cat(out, dim=1), model(seq), atol=1e-5)
```

Then give `generate` a flag `use_cache`: the first call processes the prompt, and every later call
processes only the newest token.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Run the script before reading it closely: the four bugs surface one after another, each with its own
symptom.

### Part 1

| Bugs fixed so far | Output of `python tiny_gpt.py` | Points to |
| --- | --- | --- |
| none | `RuntimeError: mat1 and mat2 shapes cannot be multiplied (768x64 and 16x64)` | bug 1, `w_o` |
| 1 | the loss stays near 2.55 for all 400 steps; test 1 fails | bug 2, `backward()` |
| 1, 2 | the loss falls to about 1.0 and stalls; test 1 fails | bug 3, mask value |
| 1, 2, 3 | test 1 passes; the loss stalls near 1.4; test 2 fails | bug 4, `pos_emb` |
| all | the loss reaches 0.0004; `all tests passed` | |

**Bug 1: `w_o` in `SelfAttention.__init__`.** The traceback ends in the last line of
`SelfAttention.forward`, where the heads have already been merged: `y.transpose(1, 2).flatten(-2)` has
shape `(B, T, n_head * d_head) = (64, 12, 64)`, the `768x64` of the message, while `16x64` is the
transposed weight of a layer that expects `d_head = 16` features. The output projection mixes the
heads, so it acts on their concatenation and takes `d_model` inputs.

```py
self.w_o = nn.Linear(d_model, d_model)      # was nn.Linear(self.d_head, d_model)
```

**Bug 2: no `loss.backward()` in `train`.** `opt.step()` changes every parameter according to its
`.grad`, and only `loss.backward()` fills `.grad`. Without it
`all(p.grad is None for p in model.parameters())` stays `True`, Adam skips such parameters without any
message, and no parameter ever changes. The loss only fluctuates from batch to batch around its initial
value; a uniform guess over 11 tokens would give $\ln 11 \approx 2.40$.

```py
opt.zero_grad()                             # NOTE: before backward(); after it, it would erase the gradients
loss.backward()
opt.step()
```

**Bug 3: the fill value `-1e-9` in `SelfAttention.forward`.** Softmax gives a position with score $s$ a
weight proportional to $e^{s}$. `-1e-9` is a tiny number, not a large negative one:
$e^{-10^{-9}} \approx 1$, the weight of a visible position with score 0, and only $-\infty$ gives
$e^{-\infty} = 0$. In the untrained model, where all scores are near 0, the query at position 0 puts 0.92
of its weight, about 11/12, on the 11 positions it must not see. During training the input at position
$t + 1$ is exactly the target of position $t$, so the model reads the answer instead of computing it.
With this bug alone the loss still falls (0.15 after 400 steps), but test 1 fails, and `generate`, where
no later tokens exist, completes 0 of 500 prompts.

```py
scores = scores.masked_fill(~self.visible[:T, :T], float("-inf"))      # was -1e-9
```

**Bug 4: the shape `(1, 1, d_model)` of `pos_emb` in `TinyGPT.__init__`.** Slicing a dimension of size 1
with `[:, :T]` returns size 1 again, and broadcasting adds this one vector to every position, so nothing
fails. The same vector everywhere carries no position information: attention then weights the keys by
content alone, and the output of the single layer at the separator depends on which digits precede it,
not on their order. The prompts `7 0 2 2 5 8 10` and `8 5 2 2 0 7 10` give the same logits there
(difference $2 \cdot 10^{-7}$), although the correct next tokens are 8 and 7. The model can only guess
among the digits still missing, and the loss stalls near 1.4. With `n_layer=2` the symptom is weaker,
0.39 after 400 steps against 0.0005 when fixed, because the causal mask itself leaks some position
information: position $t$ averages over exactly $t + 1$ tokens.

```py
self.pos_emb = nn.Parameter(torch.randn(1, max_len, d_model) * 0.02)    # one row per position; was (1, 1, d_model)
```

### Part 2

Three edits. The head has two outputs instead of `VOCAB`. The hidden states are averaged over the time
dimension before the head. The loss compares one row of logits per sequence with one label per
sequence, so the reshaping and the slicing of answer positions disappear. The wrapper below leaves
`TinyGPT` untouched: it replaces the vocabulary head with `nn.Identity()`, so that the body returns the
hidden states.

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

After 200 steps with the optimiser settings of Part 1 the classifier labels 1000 new numbers without an
error. The head is affine, so pooling before it equals averaging the per-position logits. Under the
causal mask only the last position sees the whole number, which is why causal models are usually read
out at `hidden[:, -1]`; mean pooling works here as well.

### Part 3

A call with a cache receives only the $T$ new tokens, while `past` positions are already stored. Queries
are needed for the new positions only, keys and values for all `past + T` positions, so the scores have
shape `(T, past + T)`. Three things change. Attention appends its new keys and values to the cache and
works with the full ones. The mask and the positional embedding are indexed by the absolute positions
`past .. past + T - 1` instead of `0 .. T - 1`. And `cache`, together with the layer index, is passed
from `TinyGPT` through `Block` down to `SelfAttention`.

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

The check of the statement passes on a two-layer model, and `generate` returns the same tokens with and
without the cache. Attention in one decoding step costs $O(T)$ instead of $O(T^2)$, and the cache holds
`2 * n_layer * B * T * d_model` numbers.

### Follow-ups

- `float("-inf")` rather than `-1e9`: in float16, `scores.masked_fill(mask, -1e9)` raises
  `RuntimeError: value cannot be converted to type c10::Half without overflow`. In exchange, a fully
  masked row, which padding masks can produce, becomes NaN under softmax.
- Other bugs of the same kind: a reduction over the wrong axis, a missing scale factor `d_head ** 0.5`, a
  hand-written softmax that exponentiates the scores without subtracting each row's maximum first, a
  one-character typo in a variable name. With `softmax(dim=-2)` this file still reaches a loss of 0.0014, yet test 1
  fails and `generate` gets 2% of the prompts right.
- `torch.cat` copies the whole cache at every step. Production code allocates
  `(B, n_head, max_len, d_head)` once and writes into the slice `[:, :, past:past + T]`.
- Numbers of different lengths need padding. Padded positions are then masked as keys and left out of
  the mean of Part 2.

<details>
<summary>The complete file after Parts 1 and 3, and the checks (runnable)</summary>

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

# Part 3: chunks of lengths 3, 1, 5, 2, 2 against one full forward pass (two layers)
deep = TinyGPT(n_layer=2)
seq = make_batch(8, rng)
with torch.no_grad():
    cache, out = KVCache(n_layer=2), []
    for a, b in [(0, 3), (3, 4), (4, 9), (9, 11), (11, 13)]:
        out.append(deep(seq[:, a:b], cache))
        assert cache.length == b                    # NOTE: a call adds its own positions and no others
    assert torch.allclose(torch.cat(out, dim=1), deep(seq), atol=1e-5)

row = torch.tensor([[0.0, 120.0, float("-inf")]])   # a softmax that skips the row maximum: exp(120) overflows
naive = row.exp() / row.exp().sum(dim=-1, keepdim=True)
assert naive.isnan().any() and torch.equal(row.softmax(dim=-1), torch.tensor([[0.0, 1.0, 0.0]]))
prompts = seq[:, :N_DIGITS + 1]
assert torch.equal(generate(model, prompts, N_DIGITS, use_cache=True), generate(model, prompts, N_DIGITS))
assert torch.equal(generate(model, prompts, N_DIGITS, use_cache=True), seq)
```

</details>

</details>
