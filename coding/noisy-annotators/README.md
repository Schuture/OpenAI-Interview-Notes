# Noisy Annotators

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| ML coding · Python | ★★★★☆ | Medium | MLE · RS · RE | data-cleaning, label-noise, evaluation, numpy | 3 parts |
<!-- meta:end -->

## Problem

`X_train` is a float array of shape `(2000, 60)`; its rows are training points in $\mathbb{R}^{60}$.
`X_test` and `y_test`, of shape `(1000, 60)` and `(1000,)`, are a held-out test set whose true class is
in `{0, 1, 2}`. The training points have no single trusted label. Instead, `annotations` is an integer
array of shape `(2000, 6)`: `annotations[i, j]` is the class that annotator `j` assigned to sample `i`,
or `-1` if annotator `j` did not label sample `i`. Every row has at least two entries that are not `-1`.
A minority of the 6 annotators are unreliable on the samples they labeled: some label close to randomly,
and some are systematically biased toward one class.

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

Build a pipeline that turns `annotations` into training labels and a classifier, in three parts.

### Part 1 — Aggregating votes and scoring annotators

**(a)** Implement `aggregate_labels(annotations, n_classes, weights=None)`. For each sample, sum the
weight of every annotator who labeled it into that annotator's chosen class (weight `1.0` for every
annotator when `weights` is `None`), and predict the class with the highest total. Break ties by the
smaller class index. A sample nobody labeled — or one where every annotator who labeled it has weight
`0` — has no prediction.

```py
def aggregate_labels(annotations: np.ndarray, n_classes: int,
                      weights: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """annotations: (n, A) int, -1 for missing. weights: (A,) or None (all-ones).
    Returns (labels, has_label): labels[i] is the predicted class (arbitrary if has_label[i] is False),
    has_label[i] is False iff sample i got no label with positive total weight."""
```

**(b)** Implement `annotator_reliability(annotations, n_classes)`: for annotator `j`, the *reliability
score* is the fraction of the samples it labeled on which its label agrees with `aggregate_labels` of
every *other* annotator (unweighted). A sample fewer than one other annotator labeled does not count
towards `j`'s score.

```py
def annotator_reliability(annotations: np.ndarray, n_classes: int) -> np.ndarray:
    """Returns r of shape (A,), each entry in [0, 1]."""
```

**(c)** Implement `flag_bad_annotators(r)`: flag annotator `j` when its score is more than one standard
deviation below the mean of all `A` scores.

```py
def flag_bad_annotators(r: np.ndarray) -> np.ndarray:
    """r: (A,). Returns a boolean array of shape (A,), True where the annotator is flagged."""
```

Example, `n_classes = 2`, 7 samples and 4 annotators (`-1` = not labeled):

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

`annotator_reliability` returns approximately `[0.57, 0.67, 0.57, 0.29]`, and `flag_bad_annotators`
flags only annotator 3. `aggregate_labels` on the full matrix returns `[0, 1, 0, 0, 0, 1, 1]`.

### Part 2 — Filter and retrain

Drop the columns of the annotators flagged in Part 1, aggregate the remaining columns with
`aggregate_labels`, and discard the rows left with no label. Train
`sklearn.linear_model.LogisticRegression(max_iter=2000)` on the surviving `(X_train, label)` pairs and
score it on `(X_test, y_test)`. Compare against a baseline trained the same way on the labels aggregated
from *all* six annotators, unfiltered.

```py
def fit_and_score(X_train: np.ndarray, labels: np.ndarray, has_label: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray) -> float:
    """Fits LogisticRegression(max_iter=2000) on X_train[has_label], labels[has_label].
    Returns its accuracy on (X_test, y_test)."""
```

On the matrix above, dropping annotator 3 and re-aggregating the remaining three columns changes the
label of the last sample from `1` to `0`.

### Part 3 — Weighted voting without dropping samples

Dropping an annotator also drops every sample whose winning label depended on that annotator's vote —
with `d = 60` features that can leave too little training data. Reuse the reliability scores of Part 1
instead: derive and implement a weight for each annotator so that
`aggregate_labels(annotations, n_classes, weights=w)` down-weights an unreliable annotator's vote rather
than discarding their samples, and compare its test accuracy and its number of labeled training samples
against Part 2.

```py
def reliability_weights(r: np.ndarray, n_classes: int) -> np.ndarray:
    """r: (A,), values in [0, 1]. Returns weights of shape (A,), each >= 0."""
```

On the matrix above, `reliability_weights` returns approximately `[0.29, 0.69, 0.29, 0.0]`, and
`aggregate_labels` with these weights on the full four-column matrix again predicts `0` for the last
sample — without dropping annotator 3's column.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Two points worth confirming with the interviewer: whether an annotator's reliability should be scored
against the majority of every other annotator (assumed here) or against a trusted subset, and whether a
flagged annotator's labels should be dropped by default or down-weighted by default.

### Part 1

**(a)** A vote is a sum of weights per class, one addend per annotator who labeled the sample; the
predicted class is the one with the largest sum, and `np.argmax` already breaks ties by the smallest
index. `has_label` catches the two ways a sample can end up with no vote: nobody labeled it, or every
annotator who did has weight `0`.

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

**(b)** An annotator is compared against the majority of the *others*, never one that includes its own
vote — with as few as two voters on a sample, folding an annotator's vote into its own reference majority
would let it "agree with itself" and inflate the score.

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

**(c)** A fixed cutoff such as `0.5` would need retuning for a different number of classes; scoring
against the annotator pool's own mean and spread does not.

```python
def flag_bad_annotators(r):
    return r < r.mean() - r.std()
```

At `seed=7`, `annotator_reliability` returns approximately `[0.67, 0.66, 0.66, 0.67, 0.35, 0.40]` and
`flag_bad_annotators` flags exactly annotators 4 and 5 — the two built into `make_dataset` above. This
holds for every seed checked below.

### Part 2

```python
def fit_and_score(X_train, labels, has_label, X_test, y_test):
    clf = LogisticRegression(max_iter=2000)
    clf.fit(X_train[has_label], labels[has_label])
    return accuracy_score(y_test, clf.predict(X_test))
```

At `seed=7`, the baseline (majority vote over all six annotators) reaches `0.72` test accuracy; after
dropping annotators 4 and 5 and re-aggregating, the filtered classifier reaches `0.86`, trained on 1954
of the 2000 samples — the other 46 lost every one of their annotators once the flagged columns were
removed. Every one of the annotators dropped by that pruning genuinely was one of the two implanted as
unreliable, so no informative vote was thrown away with them; the improvement comes only from removing
noise, never from removing signal.

### Part 3

Model annotator $j$ as a noisy channel: given the true class $c$, it reports $c$ with probability $r_j$
and each other class with probability $(1 - r_j) / (K - 1)$, where $K$ is `n_classes` — the same one
shared error rate for annotator $j$ that Part 1 estimates, standing in for a full confusion matrix. For
a sample with voters $V_i$ and candidate true class $c$, the log-likelihood of the votes it received is

$$L_i(c) = \sum_{j \in V_i} \Bigl( \mathbb{1}[\ell_{ij} = c] \log r_j
         + \mathbb{1}[\ell_{ij} \ne c] \log \frac{1 - r_j}{K - 1} \Bigr) .$$

Writing $\mathbb{1}[\ell_{ij} \ne c] = 1 - \mathbb{1}[\ell_{ij} = c]$ splits this into a term that does
not depend on $c$ and one that does:

$$L_i(c) = \sum_{j \in V_i} \log \frac{1 - r_j}{K - 1}
         + \sum_{j \in V_i} \mathbb{1}[\ell_{ij} = c] \Bigl( \log r_j - \log \frac{1 - r_j}{K - 1} \Bigr) .$$

The first sum is the same for every $c$, so it drops out of the arg max, leaving exactly the weighted
vote of `aggregate_labels`, with

$$w_j = \log \frac{r_j (K - 1)}{1 - r_j} .$$

This is a single, non-iterative pass of the same idea behind the Dawid–Skene EM algorithm: it reuses the
$r_j$ that Part 1 already estimated instead of alternating between confusion matrices and soft labels.

```python
def reliability_weights(r, n_classes):
    r = np.clip(r, 1e-2, 1 - 1e-2)                    # NOTE: avoids log(0) at r == 0 or r == 1
    w = np.log(r * (n_classes - 1) / (1 - r))
    return np.clip(w, 0.0, None)                      # NOTE: chance-level or worse -> weight 0, not a negative vote
```

At `seed=7` the weights are approximately `[1.42, 1.34, 1.38, 1.42, 0.09, 0.28]`: annotator 4 (the
uniform guesser) is worth almost nothing, and annotator 5 (biased to class 0) still carries a small
positive weight, since one fixed answer is occasionally right by chance. Aggregating with these weights
keeps all 2000 samples labeled — no vote total is ever driven to exactly `0` here — and the resulting
classifier reaches `0.88` test accuracy, slightly above the `0.86` of Part 2, without giving up any
training data.

### Follow-ups

- Majority vote itself can fail on a single sample when most of the annotators who happened to label it
  are unreliable, independently of how well Part 1 scores the *annotators*; wider per-sample coverage
  makes this rarer but never rules it out.
- Running the E/M steps of Dawid–Skene to convergence, instead of stopping at this one-shot version,
  lets each annotator have a full confusion matrix (different error rates per true class) rather than a
  single shared $r_j$.
- The reliability score here treats annotators independently; two annotators who share the same bias
  reinforce rather than catch each other. A pairwise annotator-by-annotator agreement matrix (or Cohen's
  kappa between each pair) surfaces that kind of correlated error, which agreement-with-the-majority alone
  cannot.

<details>
<summary>Checks (runnable)</summary>

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
