<div align="center">

# OpenAI Interview Notes

**Practice problems modelled on OpenAI's coding, ML, system design and behavioral interviews.<br>
Full problem statements, worked solutions, and code that CI runs on every push.**

English · [中文](README.zh.md)

[![Check](https://github.com/Schuture/OpenAI-Interview-Notes/actions/workflows/check.yml/badge.svg)](https://github.com/Schuture/OpenAI-Interview-Notes/actions/workflows/check.yml)
![Problems](https://img.shields.io/badge/problems-52-blue)
![Languages](https://img.shields.io/badge/languages-English%20%7C%20%E4%B8%AD%E6%96%87-blue)
[![Text: CC BY-NC 4.0](https://img.shields.io/badge/text-CC%20BY--NC%204.0-lightgrey)](LICENSE)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE-CODE)
[![GitHub stars](https://img.shields.io/github/stars/Schuture/OpenAI-Interview-Notes?style=social)](https://github.com/Schuture/OpenAI-Interview-Notes/stargazers)

</div>

> [!NOTE]
> **Unofficial.** This project is not affiliated with, endorsed by or sponsored by OpenAI. The problems are
> reconstructed from second-hand accounts of past interviews and written up from scratch: statements, examples,
> solutions and code are all original. Interviews differ between teams and change over time, so treat each page
> as practice on the kind of problem you may meet, not as the exact question. If you believe something here
> should not be public, [open an issue](https://github.com/Schuture/OpenAI-Interview-Notes/issues) and it will be taken down.

## What is in it

| Section | Problems | What they cover |
| --- | ---: | --- |
| [Coding](#coding-30) | 30 | Data structures, simulation, concurrency, parsing, object-oriented design and refactoring, plus nine ML problems: NumPy and PyTorch from scratch, derivations, debugging, code reading and probability |
| [System design](#system-design-18) | 18 | Product and infrastructure systems (payments, chat, CI/CD, webhooks, video generation) and three ML system designs around retrieval and data mining |
| [Behavioral & other](#behavioral--other-4) | 4 | Recruiter screen, hiring-manager round, technical deep dive with slides, engineering management |

What sets the pages apart:

- **Complete statements.** Each problem is written out in full, with definitions, function signatures and worked
  examples, so you can attempt it without guessing what was meant. Most coding problems come in two to five parts
  that build on each other.
- **Solutions you can check.** Every coding and system-design solution ends with a collapsed block of runnable
  checks. For coding, these are asserts on the examples and, wherever one can be written, a brute force built
  independently from the statement; for system design, the back-of-the-envelope estimates recomputed in code.
  CI runs the code of all pages on every push.
- **Pitfalls where they happen.** Instead of a separate list of mistakes, `# NOTE:` comments sit on the line the
  mistake would be made.
- **Study tracks.** The [roadmap](ROADMAP.md) orders the problems for Research (RS / RE), MLE and SWE / Infra roles.
- **English and Chinese.** Every page exists in both languages with identical code.

## How to use it

### 1. Pick a track and a pace

Start from the track for your role in the [roadmap](ROADMAP.md). ★ shows how often a question comes up, from
★★★★★ (again and again) to ★☆☆☆☆ (rarely), and each track is sorted so that the top of the list pays off first.

| Time you have | [Research (RS / RE)](ROADMAP.md#research-track-rs--re) | [MLE](ROADMAP.md#mle-track) | [SWE / Infra](ROADMAP.md#swe--infra-track) |
| --- | --- | --- | --- |
| About a week | stages 1–3, and start the deep-dive and hiring-manager stories | everything rated ★★★★☆ or higher | everything rated ★★★★☆ or higher |
| Two to four weeks | all six stages | the whole track | the whole track |
| More than that | add the ★★★★☆ problems of the other tracks | add the Research stages you skipped | add the ML coding core if the team works close to models |

### 2. Practise one problem

**Coding.** Read only the **Problem** section. Before writing code, note what you would ask the interviewer
(edge cases, tie-breaking, input sizes), then compare with the first lines of the reference solution, which list
the points worth confirming. Give yourself a time limit for the whole problem and take the parts in order,
treating each new part as a change of requirements: extend your code instead of starting over. Run it on the
examples, then open the reference solution and compare approach, complexity and the `# NOTE:` comments. The
checks call the functions named in the statement, so if you keep the same names and signatures you can usually
run them against your own code.

**System design.** Give yourself about an hour (the page header shows the length of the round where it is known)
and work through the prompt out loud or on paper: requirements, estimates, API and data model, architecture, then
two or three deep dives. Then compare with the reference solution: which requirement you missed, where your
numbers differ, which failure you did not handle. The estimates are computed in the checks block, so you can
change an input and rerun them.

**Behavioral.** Each page lists what the round probes and how a strong answer is structured, and ends with an
outline to fill in with your own stories. Rehearse them aloud, and keep your filled-in version private.

### 3. Read a page

Every page starts with a table (type, priority, difficulty, roles, topics and, where known, format and round)
and has exactly two sections:

| Section | Coding | System design | Behavioral |
| --- | --- | --- | --- |
| **Problem** | definitions, then one block per part: task, signature, example | the system, its users, the numbers given, the scope | the round and its questions |
| **Reference solution** (collapsed) | per part: idea, derivation, code, with pitfalls as `# NOTE:` comments; then follow-ups and the checks | requirements, data model and API, architecture, deep dives, follow-ups | what is probed, how to structure the answer, an outline to fill in |

Roles: **RS** research scientist · **RE** research engineer · **MLE** machine-learning engineer ·
**SWE** software engineer · **Infra Eng** infrastructure engineer · **EM** engineering manager.

### 4. Run the code

```bash
git clone https://github.com/Schuture/OpenAI-Interview-Notes.git
cd OpenAI-Interview-Notes
pip install -r requirements.txt                    # NumPy, SciPy, scikit-learn, PyTorch, Pillow
python scripts/run_snippets.py coding/gpu-credits   # one page
python scripts/run_snippets.py --all                # every page
```

A page's ```` ```python ```` blocks run top to bottom as one script; ```` ```py ```` blocks are illustrative
(bare signatures, code that fails on purpose) and are not executed. CI uses Python 3.11.

## Problems

Sorted by priority within each section. A dash under Difficulty means it has not been rated.

<!-- index:begin -->
### Coding (30)

| # | Problem | Priority | Difficulty | Roles | Topics |
| ---: | --- | --- | --- | --- | --- |
| 1 | [Infection Spread (Grid Cellular Automaton)](coding/infection-spread/README.md) | ★★★★★ | Medium | SWE · MLE · RE · RS · EM | bfs, simulation, grid |
| 2 | [Follow Graph & Recommendations (Social Network)](coding/social-network/README.md) | ★★★★★ | Medium | SWE · RE | graph, hashmap, snapshot, binary-search |
| 3 | [Cluster Node Count & Topology (Tree Messaging)](coding/cluster-count-topology/README.md) | ★★★★☆ | Medium | SWE | tree, message-passing, distributed-systems, idempotency |
| 4 | [GPU Credits](coding/gpu-credits/README.md) | ★★★★☆ | Medium | SWE | data-structure, simulation, heap |
| 5 | [Prefix Matmul: Autograd, Manual Backward, Hillis–Steele Scan](coding/autograd-hillis-steele/README.md) | ★★★★☆ | Hard | RS · RE · MLE | autograd, linear-algebra, parallel-scan, pytorch |
| 6 | [NumPy 1-NN as an Affine Layer](coding/numpy-1nn-affine/README.md) | ★★★★☆ | Medium | MLE · RE | numpy, vectorization, broadcasting, linear-algebra |
| 7 | [Monster Battle](coding/monster-battle/README.md) | ★★★★☆ | Medium | SWE | oop-design, simulation |
| 8 | [Transformer Bug Hunt](coding/transformer-bug-hunt/README.md) | ★★★★☆ | Medium | MLE · RS · RE | transformer, debugging, kv-cache, pytorch |
| 9 | [Memory Allocator](coding/memory-allocator/README.md) | ★★★★☆ | Hard | SWE · MLE · RE | data-structure, intervals, balanced-bst |
| 10 | [Noisy Annotators](coding/noisy-annotators/README.md) | ★★★★☆ | Medium | MLE · RS · RE | data-cleaning, label-noise, evaluation, numpy |
| 11 | [Type Inference for a Toy Language](coding/type-inference/README.md) | ★★★★☆ | Medium | SWE · RE | recursion, unification, tree |
| 12 | [Data Labeling Task Scheduler](coding/labeling-task-scheduler/README.md) | ★★★★☆ | Medium | SWE · RE · MLE | scheduling, greedy, fairness |
| 13 | [Durable KV Store: Custom Serialization](coding/durable-kv-store/README.md) | ★★★☆☆ | Medium | SWE · Infra Eng | serialization, persistence, parsing, storage, fault-tolerance |
| 14 | [Streaming Entropy](coding/streaming-entropy/README.md) | ★★★☆☆ | Medium | RS · RE · MLE | numerical-stability, softmax, streaming |
| 15 | [Chat Bot Refactoring](coding/chat-bot-refactoring/README.md) | ★★★☆☆ | Medium | SWE | refactoring, oop-design, event-driven, testing |
| 16 | [IPv4 / CIDR Iterator](coding/ipv4-cidr-iterator/README.md) | ★★★☆☆ | Medium | SWE | bit-manipulation, iterator, string |
| 17 | [Shard Rebalancing with an Overlap Limit](coding/shard-rebalance/README.md) | ★★★☆☆ | Medium | SWE | intervals, greedy, heap, consistent-hashing |
| 18 | [Restart Strategies under a Known Mean (Las Vegas)](coding/restart-strategy-math/README.md) | ★★★☆☆ | Hard | RS · RE | probability, inequalities, algorithm-design |
| 19 | [Version Dependency](coding/version-dependency/README.md) | ★★★☆☆ | Medium | SWE · RE | binary-search, backtracking, topological-sort |
| 20 | [Fault-Tolerant Work Queue](coding/fault-tolerant-work-queue/README.md) | ★☆☆☆☆ | Medium | Infra Eng | queue, state-machine, retry |
| 21 | [Cross-Entropy Loss from Scratch](coding/cross-entropy-loss/README.md) | ★☆☆☆☆ | Medium | MLE · RE | numpy, numerical-stability, loss-functions, kl-divergence |
| 22 | [Best Grid Path with K Row Skips](coding/grid-path-limited-jumps/README.md) | ★☆☆☆☆ | Hard | SWE | dp, grid, counting |
| 23 | [cd Command / Path Resolution](coding/cd-command/README.md) | ★☆☆☆☆ | Medium | SWE | string-processing, stack, symlinks |
| 24 | [Spreadsheet with Cell Dependencies (OpenSheet)](coding/spreadsheet-dependencies/README.md) | ★☆☆☆☆ | Medium | SWE | graph, dfs, topological-sort, recursion |
| 25 | [ModalLock and FairModalLock](coding/modal-lock/README.md) | ★☆☆☆☆ | Hard | SWE · MLE | concurrency, threading, fairness |
| 26 | [Sharded Matmul: Forward, Backward, Bug Hunt](coding/sharded-matmul-backprop/README.md) | ★☆☆☆☆ | Hard | MLE · RE | linear-algebra, parallelism, autograd, numpy, pytorch, debugging |
| 27 | [Resumable Iterators (1D, 2D, Arbitrary Depth)](coding/resumable-iterator/README.md) | ★☆☆☆☆ | Medium | SWE | iterator, oop-design, state |
| 28 | [PyTorch Code Reading & Extension](coding/pytorch-code-reading/README.md) | ★☆☆☆☆ | — | RE · MLE | code-reading, pytorch, complexity |
| 29 | [In-Memory SQL-like Database](coding/in-memory-database/README.md) | ★☆☆☆☆ | Medium | SWE | data-structure, oop-design, sql |
| 30 | [Time-Travel Key-Value Store](coding/time-based-kv-store/README.md) | ★☆☆☆☆ | Medium | SWE | binary-search, testing, concurrency |

### System design (18)

| # | Problem | Priority | Difficulty | Roles | Topics |
| ---: | --- | --- | --- | --- | --- |
| 1 | [Payment System / Coffee-Shop Ordering](system-design/payment-coffee-shop/README.md) | ★★★★★ | Medium | SWE | payment, idempotency, ledger |
| 2 | [Online Chess Platform (Chess.com-style)](system-design/chess-platform/README.md) | ★★★★★ | — | SWE · Infra Eng | websocket, matchmaking, game-state, idempotency, consistent-hashing |
| 3 | [Video Generation Pipeline (Sora-style)](system-design/video-generation-pipeline/README.md) | ★★★★★ | Medium | SWE · Infra Eng · EM | gpu-scheduling, queueing, fault-tolerance |
| 4 | [Cloud IDE](system-design/cloud-ide/README.md) | ★★★☆☆ | Hard | SWE · Infra Eng · EM | sandbox, vm-lifecycle, websocket, streaming |
| 5 | [Image Sharing with Deduplication](system-design/image-dedup-sharing/README.md) | ★★☆☆☆ | Medium | SWE | storage, deduplication, consistency |
| 6 | [Distributed Crossword Solver](system-design/crossword-solver/README.md) | ★★☆☆☆ | — | SWE · Infra Eng | distributed-search, backtracking, job-system |
| 7 | [AI Chatbot Front End](system-design/ai-chatbot-frontend/README.md) | ★★☆☆☆ | — | SWE | frontend, streaming, client-state, auth |
| 8 | [Multi-Tenant CI/CD](system-design/multi-tenant-ci-cd/README.md) | ★★☆☆☆ | — | SWE · Infra Eng | scheduling, exactly-once, multi-tenancy |
| 9 | [Slack-style Messaging](system-design/slack/README.md) | ★★☆☆☆ | — | SWE · EM | messaging, pubsub, multi-device, multi-tenancy |
| 10 | [Search & RAG ML Design (spoken)](system-design/rag-search-ml-design/README.md) | ★★☆☆☆ | — | RE · MLE | retrieval, contrastive-learning, ranking, evaluation |
| 11 | [Calendar (Google Calendar-style)](system-design/google-calendar/README.md) | ★★☆☆☆ | — | SWE | schema-design, caching, sync |
| 12 | [URL Shortener](system-design/url-shortener/README.md) | ★★☆☆☆ | — | SWE | hashing, caching, scaling, database |
| 13 | [Webhook Delivery](system-design/webhook-delivery/README.md) | ★★☆☆☆ | — | SWE · Infra Eng | queueing, retry, idempotency, security |
| 14 | [Nearby Places (POI / Yelp-style)](system-design/nearby-poi/README.md) | ★★☆☆☆ | — | SWE | geospatial-index, sharding, caching |
| 15 | [Streaming AI Product Feature](system-design/realtime-ai-feature/README.md) | ★☆☆☆☆ | — | SWE | streaming, api-design, rate-limiting, fullstack |
| 16 | [Novel-Data Mining from an Unlabeled Corpus](system-design/mining-novel-data/README.md) | ★☆☆☆☆ | — | MLE | ml-system-design, data-mining, retrieval |
| 17 | [ChatGPT Enterprise: RAG over Company Data](system-design/chatgpt-enterprise-rag/README.md) | ★☆☆☆☆ | — | MLE · RE | rag, retrieval, access-control |
| 18 | [GPT-3 Playground (Full-Stack)](system-design/gpt3-playground/README.md) | ★☆☆☆☆ | — | SWE | fullstack, frontend, streaming, schema-design |

### Behavioral & other (4)

| # | Problem | Priority | Difficulty | Roles | Topics |
| ---: | --- | --- | --- | --- | --- |
| 1 | [Hiring Manager Round: Why OpenAI, Safety, AGI](behavioral/hiring-manager-why-openai/README.md) | ★★★★★ | — | All | behavioral, why-company, ai-safety, cross-functional |
| 2 | [Technical Deep Dive (with slides)](behavioral/technical-deep-dive/README.md) | ★★★★★ | — | SWE · MLE · RE · Infra Eng | presentation, project-deep-dive |
| 3 | [Recruiter / HR Screen](behavioral/recruiter-screen/README.md) | ★★★★☆ | — | All | behavioral, process, compensation |
| 4 | [Engineering Management Round](behavioral/engineering-management/README.md) | ★☆☆☆☆ | — | EM | leadership, hiring, mentorship, performance-management, team-composition |
<!-- index:end -->

## Contributing

Corrections, new variants and translations are welcome. Found a wrong answer, a missing edge case or a sentence
that does not make sense? [Open an issue](https://github.com/Schuture/OpenAI-Interview-Notes/issues). For pull requests, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

The text (prose, tables and diagrams) is licensed under [CC BY-NC 4.0](LICENSE); the code, both in the pages and
under `scripts/`, under the [MIT License](LICENSE-CODE).
