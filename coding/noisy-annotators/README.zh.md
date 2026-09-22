# 含噪标注者

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| ML 编程 · Python | ★★★★☆ | 中等 | MLE · RS · RE | data-cleaning, label-noise, evaluation, numpy | 3 个部分 |
<!-- meta:end -->

## 题目

`X_train` 是形状为 `(2000, 60)` 的浮点数组，它的每一行是 $\mathbb{R}^{60}$ 中的一个训练点。
`X_test` 和 `y_test`，形状分别为 `(1000, 60)` 和 `(1000,)`，是一个留出的测试集，真实类别取值于 `{0, 1, 2}`。
训练点没有单一可信的标签；取而代之的是形状为 `(2000, 6)` 的整数数组 `annotations`：`annotations[i, j]` 是
标注者 `j` 给样本 `i` 打的类别，如果标注者 `j` 没有标注样本 `i`，则为 `-1`。每一行至少有两个不为 `-1` 的元素。
6 个标注者中有少数不可靠：在他们标注过的样本上，有的标注接近随机，有的系统性地偏向某一个类别。

```python
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

N_TRAIN, N_TEST, N_FEATURES, N_CLASSES, N_ANNOTATORS = 2000, 1000, 60, 3, 6


def make_dataset(seed):
    """Returns (X_train, y_train_true, X_test, y_test, annotations), built deterministically from seed.
    y_train_true, shape (2000,), is the ground-truth class of every training point: use it only to
    check your answer to Part 1, never to build a training label. annotations, shape (2000, 6), has
    entries in {-1, 0, 1, 2}."""
    rng = np.random.default_rng(seed)
    X, y = make_classification(n_samples=N_TRAIN + N_TEST, n_features=N_FEATURES, n_informative=40,
                                n_redundant=10, n_classes=N_CLASSES, n_clusters_per_class=2,
                                class_sep=1.6, flip_y=0.01, random_state=seed)
    X_train, X_test = X[:N_TRAIN], X[N_TRAIN:]
    y_train, y_test = y[:N_TRAIN], y[N_TRAIN:]

    annotations = np.full((N_TRAIN, N_ANNOTATORS), -1)
    for i in range(N_TRAIN):
        k = rng.integers(2, 5)                                    # 2 to 4 annotators label this sample
        for j in rng.choice(N_ANNOTATORS, size=int(k), replace=False):
            if j == 4:                                             # NOTE: ignores X_train and y_train entirely
                annotations[i, j] = rng.integers(0, N_CLASSES)
            elif j == 5:                                           # NOTE: systematically biased, not noisy
                annotations[i, j] = 0
            elif rng.random() < 0.92:
                annotations[i, j] = y_train[i]
            else:
                others = [c for c in range(N_CLASSES) if c != y_train[i]]
                annotations[i, j] = rng.choice(others)
    return X_train, y_train, X_test, y_test, annotations
```

把 `annotations` 变成训练标签和一个分类器，分三个 Part 完成这条流水线。

### Part 1 —— 聚合投票，给标注者打分

**(a)** 实现 `aggregate_labels(annotations, n_classes, weights=None)`。对每个样本，把标注过它的每个标注者的
权重（`weights` 为 `None` 时每个标注者权重都是 `1.0`）累加到它所选的类别上，预测总权重最大的那个类别，
并列时取较小的类别下标。没有人标注过的样本——或者标注过它的所有标注者权重都是 `0`——没有预测结果。

```py
def aggregate_labels(annotations: np.ndarray, n_classes: int,
                      weights: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """annotations: (n, A) int, -1 for missing. weights: (A,) or None (all-ones).
    Returns (labels, has_label): labels[i] is the predicted class (arbitrary if has_label[i] is False),
    has_label[i] is False iff sample i got no label with positive total weight."""
```

**(b)** 实现 `annotator_reliability(annotations, n_classes)`：标注者 `j` 的*可靠度分数*（reliability score），
是它标注过的样本中，它给出的标签与*其余*标注者（不加权）的 `aggregate_labels` 结果一致的比例。
如果标注过某个样本的其余标注者少于一个，这个样本就不计入 `j` 的分数。

```py
def annotator_reliability(annotations: np.ndarray, n_classes: int) -> np.ndarray:
    """Returns r of shape (A,), each entry in [0, 1]."""
```

**(c)** 实现 `flag_bad_annotators(r)`：当标注者 `j` 的分数比全部 `A` 个分数的均值低出一个标准差以上时，标记它。

```py
def flag_bad_annotators(r: np.ndarray) -> np.ndarray:
    """r: (A,). Returns a boolean array of shape (A,), True where the annotator is flagged."""
```

例子，`n_classes = 2`，7 个样本、4 个标注者（`-1` 表示未标注）：

```text
ann0 ann1 ann2 ann3
 0    0    0    1
 1    1    1    1
 0    0    1    1
 0    0    0    1
 1    0    0    1
 1    1    1    1
 0   -1    1    1
```

`annotator_reliability` 返回约 `[0.57, 0.67, 0.57, 0.29]`，`flag_bad_annotators` 只标记标注者 3。
`aggregate_labels` 在完整矩阵上返回 `[0, 1, 0, 0, 0, 1, 1]`。

### Part 2 —— 过滤后重新训练

丢弃 Part 1 中被标记的标注者所在的列，用 `aggregate_labels` 对剩下的列重新聚合，再丢弃聚合后仍没有标签的行。
在剩下的 `(X_train, label)` 数据对上训练 `sklearn.linear_model.LogisticRegression(max_iter=2000)`，
在 `(X_test, y_test)` 上打分。把它与一个基线比较：基线用同样的方式训练，标签则是对全部六个标注者
（不做任何过滤）聚合得到的。

```py
def fit_and_score(X_train: np.ndarray, labels: np.ndarray, has_label: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray) -> float:
    """Fits LogisticRegression(max_iter=2000) on X_train[has_label], labels[has_label].
    Returns its accuracy on (X_test, y_test)."""
```

在上面的矩阵上，丢弃标注者 3 并对剩下三列重新聚合后，最后一个样本的标签从 `1` 变为 `0`。

### Part 3 —— 不丢样本的加权投票

丢掉一个标注者，也会丢掉每一个其获胜标签依赖于该标注者投票的样本——在 `d = 60` 维特征下，这可能让训练数据
变得太少。改用 Part 1 算出的可靠度分数：为每个标注者推导并实现一个权重，使得
`aggregate_labels(annotations, n_classes, weights=w)` 只降低不可靠标注者投票的权重，而不丢弃他们标注过的样本；
把它的测试准确率和有标签的训练样本数与 Part 2 比较。

```py
def reliability_weights(r: np.ndarray, n_classes: int) -> np.ndarray:
    """r: (A,), values in [0, 1]. Returns weights of shape (A,), each >= 0."""
```

在上面的矩阵上，`reliability_weights` 返回约 `[0.29, 0.69, 0.29, 0.0]`，用这些权重在完整的四列矩阵上聚合，
最后一个样本的预测仍然是 `0`——但并没有丢弃标注者 3 那一列。

## 参考解答

<details>
<summary>展开参考解答</summary>

有两点值得向面试官确认：标注者的可靠度该对照其余*全部*标注者的多数（本文的假设），还是只对照一个可信的子集；
被标记的标注者，其标签默认应该丢弃还是降权。

### Part 1

**(a)** 一次投票就是按类别对权重求和，标注过该样本的每个标注者贡献一项；预测的类别是权重和最大的那个，
`np.argmax` 本身就是按最小下标打破并列。`has_label` 要捕捉两种没有投票结果的情况：没有人标注过这个样本，
或者标注过它的标注者权重全是 `0`。

```python
def aggregate_labels(annotations, n_classes, weights=None):
    n, A = annotations.shape
    if weights is None:
        weights = np.ones(A)
    scores = np.zeros((n, n_classes))
    for j in range(A):
        labeled = annotations[:, j] != -1
        scores[labeled, annotations[labeled, j]] += weights[j]
    has_label = scores.sum(axis=1) > 0
    labels = np.argmax(scores, axis=1)               # NOTE: argmax keeps the FIRST max -> ties go to class 0
    return labels, has_label
```

**(b)** 一个标注者要对照*其余*标注者的多数，绝不能对照一个包含它自己投票的多数——在只有两个投票者的样本上，
如果把某个标注者自己的票也算进它的参照多数里，就等于让它“自己同意自己”，凭空抬高了分数。

```python
def annotator_reliability(annotations, n_classes):
    n, A = annotations.shape
    r = np.zeros(A)
    for j in range(A):
        peers = np.delete(annotations, j, axis=1)
        majority, has_majority = aggregate_labels(peers, n_classes)
        labeled_by_j = annotations[:, j] != -1
        mask = labeled_by_j & has_majority
        r[j] = np.mean(annotations[mask, j] == majority[mask]) if mask.any() else 0.0
    return r
```

**(c)** 固定阈值（比如 `0.5`）换一个类别数就要重新调；对照标注者群体自己的均值和离散程度则不用。

```python
def flag_bad_annotators(r):
    return r < r.mean() - r.std()
```

在 `seed=7` 时，`annotator_reliability` 返回约 `[0.67, 0.66, 0.66, 0.67, 0.35, 0.40]`，`flag_bad_annotators`
恰好标记出标注者 4 和 5——正是 `make_dataset` 里植入的那两个。下面检验过的每个种子都是如此。

### Part 2

```python
def fit_and_score(X_train, labels, has_label, X_test, y_test):
    clf = LogisticRegression(max_iter=2000)
    clf.fit(X_train[has_label], labels[has_label])
    return accuracy_score(y_test, clf.predict(X_test))
```

在 `seed=7` 时，基线（对全部六个标注者做多数投票）的测试准确率是 `0.72`；丢弃标注者 4、5 并重新聚合后，
过滤后的分类器达到 `0.86`，用的是 2000 个样本中的 1954 个——另外 46 个样本，在去掉被标记的列之后，
失去了它们全部的标注者。这次剪枝丢掉的标注者，无一例外正是植入的那两个不可靠标注者，所以没有任何有信息量的
投票被一并丢掉；准确率的提升只来自去掉噪声，而不是去掉信号。

### Part 3

把标注者 $j$ 建模成一个带噪声的信道：给定真实类别 $c$，它以概率 $r_j$ 报告 $c$，以概率
$(1 - r_j) / (K - 1)$ 报告其余每一个类别，其中 $K$ 是 `n_classes`——同一个 $r_j$ 就是 Part 1 估计的那个共享错误率，
代替了一整张混淆矩阵。对一个由 $V_i$ 中的标注者投票、候选真实类别为 $c$ 的样本，它收到的这些投票的对数似然是

$$L_i(c) = \sum_{j \in V_i} \Bigl( \mathbb{1}[\ell_{ij} = c] \log r_j
         + \mathbb{1}[\ell_{ij} \ne c] \log \frac{1 - r_j}{K - 1} \Bigr) .$$

利用 $\mathbb{1}[\ell_{ij} \ne c] = 1 - \mathbb{1}[\ell_{ij} = c]$，把它拆成一个不依赖 $c$ 的项和一个依赖 $c$ 的项：

$$L_i(c) = \sum_{j \in V_i} \log \frac{1 - r_j}{K - 1}
         + \sum_{j \in V_i} \mathbb{1}[\ell_{ij} = c] \Bigl( \log r_j - \log \frac{1 - r_j}{K - 1} \Bigr) .$$

第一项对每个 $c$ 都相同，求 arg max 时可以去掉，剩下的正好是 `aggregate_labels` 的加权投票，权重为

$$w_j = \log \frac{r_j (K - 1)}{1 - r_j} .$$

这正是 Dawid–Skene EM 算法背后同一个思路的一次、不迭代的版本：它直接复用 Part 1 已经估计出的 $r_j$，
而不是在混淆矩阵和软标签之间来回迭代。

```python
def reliability_weights(r, n_classes):
    r = np.clip(r, 1e-2, 1 - 1e-2)                    # NOTE: avoids log(0) at r == 0 or r == 1
    w = np.log(r * (n_classes - 1) / (1 - r))
    return np.clip(w, 0.0, None)                      # NOTE: chance-level or worse -> weight 0, not a negative vote
```

在 `seed=7` 时，权重约为 `[1.42, 1.34, 1.38, 1.42, 0.09, 0.28]`：标注者 4（均匀乱猜）几乎不值一提，
标注者 5（偏向类别 0）仍带有一个较小的正权重，因为固定回答同一个类别偶尔也会凭运气蒙对。用这些权重聚合后，
2000 个样本全部保留了标签——这里没有哪个样本的总权重被压到恰好 `0`——得到的分类器测试准确率为 `0.88`，
略高于 Part 2 的 `0.86`，而且没有丢掉任何训练数据。

### 追问

- 即便 Part 1 把标注者本身打分打得很准，多数投票在单个样本上仍可能失效：如果恰好标注了这个样本的那几个人
  大多不可靠，结果就会出错；覆盖的标注者越多，这种情况越少见，但永远无法排除。
- 把 Dawid–Skene 的 E/M 步骤迭代到收敛，而不是止步于这里的一次性版本，能让每个标注者拥有一整张混淆矩阵
  （不同真实类别下有不同的错误率），而不是共享同一个 $r_j$。
- 这里的可靠度分数把标注者当作互相独立处理；两个带有同一种偏差的标注者会彼此印证，而不是互相拆穿。
  逐对比较标注者之间的一致率（或者每对之间的 Cohen's kappa）能发现这种相关的错误，仅靠与多数票的一致率发现不了。

<details>
<summary>验证代码（可运行）</summary>

```python
toy = np.array([
    [0, 0, 0, 1],
    [1, 1, 1, 1],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
    [1, 1, 1, 1],
    [0, -1, 1, 1],
])
r_toy = annotator_reliability(toy, 2)
bad_toy = flag_bad_annotators(r_toy)
full_labels, _ = aggregate_labels(toy, 2)
filt_labels, _ = aggregate_labels(toy[:, ~bad_toy], 2)
w_toy = reliability_weights(r_toy, 2)
w_labels, _ = aggregate_labels(toy, 2, weights=w_toy)

assert np.round(r_toy, 2).tolist() == [0.57, 0.67, 0.57, 0.29]
assert bad_toy.tolist() == [False, False, False, True]
assert full_labels.tolist() == [0, 1, 0, 0, 0, 1, 1]         # at the last row, annotator 3 tips 1-1 into a 2-1 win
assert filt_labels.tolist() == [0, 1, 0, 0, 0, 1, 0]         # dropping annotator 3 flips it back to a 1-1 tie -> 0
assert np.round(w_toy, 2).tolist() == [0.29, 0.69, 0.29, 0.0]
assert w_labels.tolist() == filt_labels.tolist()             # weighting recovers the same fix, no rows dropped

for seed in range(10):
    X_train, y_train_true, X_test, y_test, annotations = make_dataset(seed=seed)
    r = annotator_reliability(annotations, N_CLASSES)
    bad = flag_bad_annotators(r)
    assert np.where(bad)[0].tolist() == [4, 5]                # the two implanted bad annotators, every seed

    base_labels, base_has = aggregate_labels(annotations, N_CLASSES)
    base_acc = fit_and_score(X_train, base_labels, base_has, X_test, y_test)

    filt_labels, filt_has = aggregate_labels(annotations[:, ~bad], N_CLASSES)
    filt_acc = fit_and_score(X_train, filt_labels, filt_has, X_test, y_test)

    w = reliability_weights(r, N_CLASSES)
    w_labels, w_has = aggregate_labels(annotations, N_CLASSES, weights=w)
    weighted_acc = fit_and_score(X_train, w_labels, w_has, X_test, y_test)

    assert filt_acc > base_acc                     # filtering beats the unfiltered baseline
    assert weighted_acc > base_acc                  # so does weighting
    assert filt_has.sum() < base_has.sum()          # filtering silently drops some samples
    assert w_has.sum() == base_has.sum() == N_TRAIN # weighting never drops a sample here
```

</details>

</details>
