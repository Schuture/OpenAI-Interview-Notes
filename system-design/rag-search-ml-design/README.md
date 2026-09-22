# Search & RAG ML Design (spoken)

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Spoken ML design | ★★☆☆☆ | — | RE · MLE | retrieval, contrastive-learning, ranking, evaluation | 60 min | Onsite |
<!-- meta:end -->

## Problem

This is a 60-minute oral "ML design" round with a search specialist. There is no architecture to
draw on a whiteboard: every question is about the machine learning underneath one system — how the
text embedding model is trained, how retrieval is put together, how results are ranked, and how
you would know any of it works.

The system: a document question-answering product built on an internal knowledge base of about
40 million passages (200-400 tokens each, already chunked). About 5 million queries arrive per day,
split roughly evenly between short keyword-style queries (2-5 tokens, like a classic search box)
and full natural-language questions. The team has a year of click logs (query, the ranked list
shown, which result was clicked and at what position) at that volume, plus about 20,000
human-graded `(query, passage, relevance grade 0-3)` judgments, to which an annotation vendor adds
a fresh batch every quarter. Target latency for retrieval plus ranking, end to end and excluding
any downstream answer generation, is under 150 ms at the median and under 350 ms at the 95th
percentile.

Out of scope for this round: the ingestion and chunking pipeline, per-document permissions and
multi-tenancy, answer generation and citation checking, and any hardware or capacity estimate.
Focus entirely on the models and the retrieval algorithms that turn a query into a ranked list of
passages.

Answer the following, moving from training to serving:

### (a) Training the embedding model

- A pretrained text encoder is to be turned into an embedding model for this retrieval task with
  contrastive learning. Why does that objective fit the task?
- Write out the loss function precisely. What does each term mean, and what is a typical value for
  the temperature?
- Where would positive pairs come from before any labeled data exists? Where would they come from
  once labeled data (say, natural-language-inference-style sentence pairs, or question-answer
  pairs) is available?
- How would negative examples be chosen, and how many per anchor?
- What role does batch size play in training quality? What happens to the loss if you double the
  batch size, and what changes if you add mined hard negatives on top of the in-batch ones?

### (b) Retrieval flow

- Given a trained embedding model, walk through the path from a raw query to a ranked shortlist of
  passages.
- Why not score every passage in the corpus against the query with a cross-encoder? What is the
  division of labor between a bi-encoder and a cross-encoder here?
- What kind of index would you search the embeddings with at this scale, and what is the main
  knob it exposes?
- Half the query volume behaves like keyword search. Is dense retrieval alone enough for that?
  How would you combine dense and lexical (sparse) retrieval, and how do you merge two ranked
  lists whose scores are not on the same scale?
- What is late interaction, as in ColBERT-style retrieval, how does it differ from both the
  bi-encoder and the cross-encoder, and what does it cost?

### (c) Ranking

- Once hybrid retrieval returns a shortlist, what does a separate ranking stage add? Why not just
  sort by the retrieval score?
- What kind of model would you use as the reranker, and how does its training data differ from the
  embedding model's?
- If the best passage for a query never enters the shortlist, can the reranker recover it? What
  does the answer imply about how you would divide effort between the retrieval stage and the
  reranker?
- How would you choose the size of the shortlist the reranker scores, and what does that choice
  trade off?

### (d) Evaluation and iteration

- What offline metrics would you report for the retrieval stage, and what would you report for the
  final ranked list? Why are they different — think in terms of recall@k, MRR, and nDCG.
- Given the labeled judgments and click logs described above, how would you build an evaluation
  query set for this product?
- Once this ships, what online signals would you track beyond the offline metrics?
- Months after launch, how would you notice that retrieval quality had quietly gotten worse?

## Reference solution

<details>
<summary>Show the reference solution</summary>

Worth confirming before answering: whether "labeled data" means sentence-pair labels
(entailment/contradiction) or query-passage judgments, since they feed the model differently. The
answer below covers both.

### (a) Training the embedding model

The objective is contrastive: pull a query's embedding toward a passage that answers it and push
it away from passages that do not. Serving ranks passages by embedding similarity to the query, so
this trains the very quantity nearest-neighbor search will sort by, rather than training a
classifier and only then comparing its embeddings.

The loss is InfoNCE. For an anchor (here a query) $q$, its positive passage $p^+$, and $N$
negative passages $\lbrace p_1^-, \dots, p_N^- \rbrace$:

$$L_{\text{InfoNCE}} = -\log \frac{\exp(\mathrm{sim}(q, p^+) / \tau)}{\exp(\mathrm{sim}(q, p^+) / \tau) + \sum_{i=1}^{N} \exp(\mathrm{sim}(q, p_i^-) / \tau)}$$

`sim(·,·)` is cosine similarity between L2-normalized embeddings, bounded to $[-1, 1]$, so the
temperature $\tau$ carries the softmax's entire scale. The denominator sums the positive *and*
every negative, which makes the loss exactly an $(N+1)$-way cross-entropy over `sim / τ` with the
positive as the correct class.

In-batch negatives are close to free: each anchor's positive is already encoded to compute its own
term, so the other $B - 1$ positives in a batch of size $B$ double as negatives with no extra
encoder passes — only a $B \times B$ similarity matrix over embeddings that already exist. Each
anchor therefore gets $N = B - 1$ negatives, with $B$ as large as memory allows (hundreds to
thousands), plus a few mined hard negatives: DPR adds one per question, and every anchor is
contrasted with the whole batch's hard negatives, not just its own.

Doubling the batch size changes only the summation: $N$ grows from $B - 1$ to $2B - 1$ while the
positive term is untouched. The loss value itself goes up — a model that cannot tell the candidates
apart scores $\log(N + 1) = \log B$, so doubling $B$ adds $\log 2$ — so losses at different batch
sizes are not comparable. Quality improves because the in-batch sum is a sampled stand-in for a
softmax over the whole corpus: a larger sample approximates it better and is likelier to contain a
hard negative by chance. Mined hard negatives join the same summation, chosen for high similarity
rather than at random; softmax weights each negative by its own similarity, so one such term can
carry most of the negative-side gradient, and a few hard negatives teach more per step than many
easy ones.

The gradient with respect to a negative's similarity is its softmax probability divided by $\tau$,
so two negatives' gradients differ by a factor $\exp(\Delta\mathrm{sim} / \tau)$. As an
illustration, take a positive at cosine similarity 0.75 and negatives at 0.68, 0.40, 0.10 and
-0.10: at $\tau = 0.07$ the 0.68 negative alone holds 98.2% of the negative-side probability mass
and its gradient is about 69,000x the easiest negative's; at $\tau = 0.20$ its share is 75.7%, at
$\tau = 0.02$ effectively 100%. Too low a temperature makes the gradient ignore every negative but
the closest one, so training becomes highly sensitive to that one candidate being a false negative
(a relevant passage labeled as a negative); too high a temperature weights all negatives almost
equally, so the near-misses that most need separating get little more push than unrelated
passages. Fixed values between 0.01 and 0.1 are typical (SimCSE uses 0.05); $\tau$ can also be a
learned parameter, as in CLIP.

Positive pairs with no labels use SimCSE's trick: pass the same text through the encoder twice;
dropout is stochastic per forward pass, so the two embeddings differ slightly for identical input,
and that pair counts as positive — an augmentation that cannot change meaning, unlike paraphrasing.
With NLI-style sentence-pair labels, supervised SimCSE takes each premise's entailment hypothesis
as its positive and the contradiction hypothesis written for the same premise as a hard negative —
topically and lexically close but wrong, a signal random in-batch text rarely gives; neutral
hypotheses are left unused. With question-passage data, the positive is (question, passage
containing the answer), and DPR mines hard negatives by running BM25 on the question and keeping
top-ranked passages that match its words but do not contain the answer. In this product the click
logs are the largest source of such pairs: a clicked passage is a positive for its query, and
passages shown above it but skipped are hard-negative candidates.

False negatives arise among mined and in-batch negatives alike — a duplicate passage, or a second
document that also answers the question — and training against one pushes a correct answer away
from the query. Mitigations: drop mined candidates that score implausibly close to the labeled
positive; de-duplicate near-identical passages within a batch; and, once a reranker exists, drop
any mined negative that it also scores highly.

### (b) Retrieval flow

The path: encode the query once with the bi-encoder, take the top few hundred passages from an
approximate nearest-neighbor index while BM25 runs in parallel over the same passages, fuse the two
lists by rank, and pass the top K — the shortlist — to a reranker.

A bi-encoder encodes queries and passages independently, so every passage embedding is computed
once, offline. A cross-encoder concatenates query and passage and runs them jointly so every layer
attends across the pair — more accurate, but nothing is precomputable, and scoring the corpus would
take $4 \times 10^7$ forward passes per query. Hence the split: the bi-encoder for recall at corpus
scale, the cross-encoder for precision at shortlist scale.

Exact search touches all $4 \times 10^7$ vectors for every query; an approximate index visits a
small fraction of them at a small, tunable recall loss. Standard choices: IVF (coarse clusters,
search only the nearest few), usually paired with product quantization, and graph indexes such as
HNSW (each vector a node with edges to nearby vectors, search walking edges toward the query). HNSW
is the better default: a strong recall/latency curve without retraining cluster centroids as
passages keep arriving, at the cost of more memory per vector (graph edges plus near-full-precision
vectors) than IVF+PQ's compressed codes. The main knob is search breadth — `efSearch`, the size of
HNSW's candidate queue (`nprobe`, the number of clusters probed, plays the same role for IVF): it
trades recall for latency at query time without a rebuild, and is set by measuring recall against
exact search on a sample of queries.

Dense retrieval generalizes across paraphrase but struggles with exact tokens such as an acronym, a
version number, or an identifier that a keyword query names directly; sparse (BM25) retrieval is
the reverse. With half this traffic behaving like keyword search, dense retrieval alone is not
enough: running both on every query and merging their lists covers both failure modes.

The two scores live on different scales — cosine is bounded, BM25 is unbounded and
length-dependent — so reciprocal rank fusion uses only rank, not score:

$$\text{score}(x) = \sum_{r \in \lbrace \text{dense}, \text{sparse} \rbrace} \frac{1}{k_0 + \text{rank}_r(x)}$$

where rank 1 is the best and a passage missing from a list contributes nothing for it. The constant
($k_0 = 60$ in the original paper) flattens the top of each list so that agreement outweighs one
retriever's favorite: a passage ranked 10th by both scores $2/70$, more than the $1/61$ of one
ranked 1st by a single retriever, whereas with $k_0 = 0$ it would lose, 0.2 to 1. A weighted sum
of per-query normalized scores keeps the actual score gaps and can do better when tuned, but its
weight needs retuning whenever the query mix or either retriever changes, so rank fusion is the
default.

Late interaction, as in ColBERT, keeps one embedding per token (query and passage alike) instead of
one pooled vector, and scores a pair by MaxSim — for every query token, its best match among the
passage's tokens, summed:

$$\text{score}(q, p) = \sum_{i} \max_{j} \; u_i \cdot v_j$$

where $u_i$ are the query's token embeddings and $v_j$ the passage's, normalized so each dot
product is a cosine. Unlike the cross-encoder, passage-side token embeddings are still computed
offline; unlike the bi-encoder, each query token is matched to whichever passage token fits it
best, catching a phrase or entity a single pooled vector can average away. The cost is storage —
about 300 vectors per passage here, $1.2 \times 10^{10}$ in all instead of $4 \times 10^7$, which
is why ColBERT uses a small per-token dimension (128) and ColBERTv2 compresses the token vectors
further — and a two-step search: a nearest-neighbor lookup per query token over all token vectors
to collect candidate passages, then exact MaxSim over each candidate's tokens. It is worth that
infrastructure only when fine-grained phrase matching matters, not as a default replacement for
the bi-encoder.

### (c) Ranking

Retrieval scores come from models cheap enough to run over the whole corpus, hence coarser than a
model that reads query and passage jointly; reranking spends that costlier model only on the
shortlist, where it is affordable.

The reranker is a cross-encoder, scored pointwise — one independent forward pass per (query,
candidate) pair, batchable and linear in the shortlist size; the cost is that a pointwise score
cannot see or penalize redundancy across candidates the way scoring the whole shortlist in one pass
could. A workable split of the 150 ms median is about 10 ms to encode the query, 30 ms for the two
retrievers in parallel plus fusion, and 10 ms of network overhead, leaving up to 90 ms for the
reranker — on the order of 100 candidates for a small cross-encoder on a GPU, a figure to measure
rather than assume; the 350 ms 95th-percentile target absorbs queueing and slow index shards.

Its training data differs from the embedding model's: the embedding model only ever sees a positive
against negatives with no notion of "how much better," while the reranker trains on graded labels —
the human judgments not held out for evaluation, and click logs corrected for position bias: a
click at rank 5 is stronger evidence than one at rank 1, since far fewer users look that far down,
so raw click rate is divided by an estimate of how often each position is examined before it
counts as a relevance label.

The reranker can only reorder what it is given: if the best passage never enters the shortlist, no
reranking recovers it. Its ceiling is the retrieval stage's recall@K at the shortlist size K, which
is why hybrid retrieval and a generous K matter more than sharpening an already-accurate reranker,
and why recall@K on the shortlist is tracked separately from the reranker's own metrics.

K comes from the curve of recall@K against K on the evaluation set: take the point where it
flattens, capped by what the reranker's latency, roughly linear in K, allows. Too small and
relevant passages never reach the reranker; too large and latency is spent on candidates that add
no recall.

### (d) Evaluation and iteration

Retrieval and the final list are graded differently. Recall@k — the fraction of a query's relevant
passages that appear in the top k, averaged over queries — suits retrieval because it ignores order
within the top k, and the reranker will reorder the shortlist anyway. MRR (the reciprocal rank of
the first relevant result, averaged over queries) and nDCG@k are order-sensitive and belong to the
list actually shown, since where the best result lands is what the user experiences. nDCG uses the
0-3 grade $g_i$ of the result at position $i$ rather than a binary label, in the common exponential
form $\text{DCG@}k = \sum_{i=1}^{k} (2^{g_i} - 1) / \log_2(i + 1)$, divided by the DCG of the
ideal ordering so that a perfect list scores 1.

The roughly 20,000 human judgments are the small, unbiased anchor. They are split by query: a fixed
share of the queries, covering keyword-style and natural-language queries alike, becomes the frozen
evaluation set, kept out of every training and hard-negative-mining pipeline and re-run on every
model or index change; the rest can train the reranker. Click logs supply a far larger but noisier
second set: queries sampled from real traffic, labels from clicks corrected for the position bias
above, with the examination estimate coming from a small slice of traffic shown in randomized
order.

Online, the signals that matter are click-through rate at the top position, a same-session
reformulation rate (an immediate related query signals the first answer failed), and a zero-result
or no-click rate. None of these confirms that the clicked passage answered the question, only that
it looked promising, so they supplement rather than replace the offline judgments.

Aggregate metrics can hide a regression in one segment offset by an improvement elsewhere, so
metrics are tracked split by query type and corpus area. The frozen evaluation set is re-run
nightly against the production index and model rather than only at deploy time, which catches a
regression no model change caused — an index rebuild silently dropping a shard — before it shows up
as slow drift in the online signals. A frozen set cannot see the queries themselves changing, so
each quarterly annotation round samples fresh queries from recent traffic, and a widening gap
between the metrics on that fresh slice and on the frozen set is the sign of drift.

### Follow-ups

- Triplet loss, $\max(0, m + \mathrm{sim}(q, p^-) - \mathrm{sim}(q, p^+))$ with a fixed margin $m$,
  sees one negative at a time: its gradient with respect to the two similarities is a constant
  $\pm 1$ while the margin is violated and zero otherwise, and each triplet ignores the rest of the
  batch. InfoNCE's softmax instead gives every negative in the batch a gradient that grows with
  its similarity.
- Distilling a cross-encoder's scores into the bi-encoder — the reranker as teacher, its scores as
  soft labels for extra training pairs — sharpens retrieval itself without touching serving
  latency.
- Gradient accumulation does not substitute for a larger batch here: negatives come only from
  examples encoded together, so each micro-batch still contrasts against its own few. Gathering
  embeddings across devices before computing the loss does enlarge the negative pool.

<details>
<summary>Checks (runnable)</summary>

```python
import math

import torch
import torch.nn.functional as F

torch.manual_seed(0)

# One anchor's similarities to its positive (index 0) and four negatives, ordered from a close,
# hard negative down to an easy, unrelated one.
sims = torch.tensor([0.75, 0.68, 0.40, 0.10, -0.10], requires_grad=True)
tau = 0.07
target = torch.tensor([0])

logits = sims / tau
loss = -F.log_softmax(logits, dim=0)[0]
loss_xent = F.cross_entropy(logits.unsqueeze(0), target)
assert torch.allclose(loss, loss_xent, atol=1e-6)          # InfoNCE == (N+1)-way cross-entropy

loss.backward()
with torch.no_grad():
    probs = F.softmax(logits, dim=0)
    onehot = torch.zeros_like(probs)
    onehot[0] = 1.0
    grad_formula = (probs - onehot) / tau
assert torch.allclose(sims.grad, grad_formula, atol=1e-6)  # d(loss)/d(sim_j) = (softmax_j - onehot_j) / tau

neg_grad = sims.grad[1:]
assert neg_grad[0] > neg_grad[1] > neg_grad[2] > neg_grad[3] > 0   # hardest negative gets the largest gradient
ratio = (neg_grad[0] / neg_grad[3]).item()
assert math.isclose(ratio, math.exp((0.68 - (-0.10)) / tau), rel_tol=1e-3)   # exp(delta_sim / tau)
print(f"loss = {loss.item():.4f}, p(positive) = {probs[0].item():.4f}, p(hard negative) = {probs[1].item():.4f}")
print(f"hardest/easiest negative gradient ratio = {ratio:,.0f}x")

# temperature sweep: share of the total negative softmax mass carried by the hardest negative
shares = {}
for t in (0.20, 0.07, 0.02):
    p = F.softmax(sims.detach() / t, dim=0)[1:]
    shares[t] = (p[0] / p.sum()).item()
    print(f"tau={t:.2f}: hardest negative carries {shares[t]:.1%} of the negative-side softmax mass")
assert shares[0.02] > shares[0.07] > shares[0.20]           # lower temperature concentrates the gradient further

# a model that cannot tell the candidates apart scores log(N + 1) = log B; doubling B adds log 2
flat = {B: F.cross_entropy(torch.zeros(1, B) / tau, target).item() for B in (128, 256)}
assert math.isclose(flat[128], math.log(128), rel_tol=1e-5)
assert math.isclose(flat[256] - flat[128], math.log(2), rel_tol=1e-4)


# triplet loss: the gradient w.r.t. (sim_pos, sim_neg) is (-1, +1) while the margin is violated, else 0
def triplet_grad(sim_pos, sim_neg, m=0.2):
    s = torch.tensor([sim_pos, sim_neg], requires_grad=True)
    torch.clamp(m + s[1] - s[0], min=0).backward()
    return tuple(s.grad.tolist())


assert triplet_grad(0.75, 0.74) == triplet_grad(0.30, 0.74) == (-1.0, 1.0)
assert triplet_grad(0.75, 0.10) == (0.0, 0.0)


# reciprocal rank fusion: with k0 = 60, 10th place in both lists beats 1st place in only one
def rrf(ranks, k0):
    return sum(1 / (k0 + r) for r in ranks)


assert math.isclose(rrf([10, 10], 60), 2 / 70) and math.isclose(rrf([1], 60), 1 / 61)
assert rrf([10, 10], 60) > rrf([1], 60)
assert math.isclose(rrf([10, 10], 0), 0.2) and rrf([10, 10], 0) < rrf([1], 0) == 1.0

# late interaction keeps one vector per token: 40M passages of about 300 tokens
assert 40_000_000 * 300 == 1.2e10

# median latency budget in ms: query encoding, parallel retrieval + fusion, network, reranker
assert 10 + 30 + 10 + 90 <= 150
```

</details>

</details>
