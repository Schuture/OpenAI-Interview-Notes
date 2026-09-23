<div align="center">

# OpenAI 面试题笔记

**按 OpenAI 编程、ML、系统设计和行为面整理的练习题。<br>
完整的题面、详细的参考解答，以及每次推送都由 CI 自动运行的代码。**

[English](README.md) · 中文

[![Check](https://github.com/Schuture/OpenAI-Interview-Notes/actions/workflows/check.yml/badge.svg)](https://github.com/Schuture/OpenAI-Interview-Notes/actions/workflows/check.yml)
![Problems](https://img.shields.io/badge/problems-63-blue)
![Languages](https://img.shields.io/badge/languages-English%20%7C%20%E4%B8%AD%E6%96%87-blue)
[![Text: CC BY-NC 4.0](https://img.shields.io/badge/text-CC%20BY--NC%204.0-lightgrey)](LICENSE)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE-CODE)
[![GitHub stars](https://img.shields.io/github/stars/Schuture/OpenAI-Interview-Notes?style=social)](https://github.com/Schuture/OpenAI-Interview-Notes/stargazers)

</div>

> [!NOTE]
> **非官方项目。** 本项目与 OpenAI 没有任何关联，未获其认可或赞助。题目根据二手的面试经历重建，题面、示例、解答和代码
> 全部重新撰写。不同团队的面试不一样，题目也会随时间变化，所以请把每一页当作对同类题目的练习，而不是原题。
> 如果你认为某些内容不应公开，请[提一个 issue](https://github.com/Schuture/OpenAI-Interview-Notes/issues)，相关内容会被下架。

## 内容概览

| 分类 | 题数 | 覆盖内容 |
| --- | ---: | --- |
| [编程](#题目) | 37 | 数据结构、模拟、并发、解析、面向对象设计与重构；另有 12 道 ML 与数学题：从零写 NumPy 和 PyTorch、数学推导、调试、强化学习和概率 |
| [系统设计](#题目) | 22 | 产品与基础设施系统（支付、即时通讯、CI/CD、Webhook、设备集群），以及 4 道 AI 系统：推理服务、视频生成、检索、Agent 评测 |
| [行为面与其他](#题目) | 4 | HR 初筛、用人经理面、带幻灯片的技术深挖、工程管理 |

除了题目，[面试流程](INTERVIEW-PROCESS.zh.md)汇总了公开反馈里一致的部分：怎么拿到面试、流程的形状、一轮里题目是怎么给的、
以及什么决定结果。

这些页面的特点：

- **完整的题面。** 每道题都写全了定义、函数签名和逐步演算的示例，拿来就能做，不用猜题意。大多数编程题分成两到五个
  逐步递进的部分。
- **可以验证的解答。** 每道编程题和系统设计题的解答末尾都有一个折叠的、可运行的检查块。编程题是针对示例的断言，
  以及只依据题面独立写出的暴力解（能写的都写了）；系统设计题是用代码重算的估算。每次推送，CI 都会运行全部页面的代码。
- **易错点写在出错的地方。** 不单列一张易错清单，而是在最容易写错的那一行加 `# NOTE:` 注释。
- **学习路线。** [学习路线](ROADMAP.zh.md)按研究方向（RS / RE）、MLE、SWE / Infra 三类岗位给题目排好了顺序。
- **中英双语。** 每一页都有中英文两个版本，代码完全一致。

## 怎么用

### 1. 选路线，定节奏

先把[面试流程](INTERVIEW-PROCESS.zh.md)读一遍，再从[学习路线](ROADMAP.zh.md)里和你岗位对应的那条开始。★ 表示题目出现的频率，从 ★★★★★（反复出现）到 ★☆☆☆☆（少见），
每条路线都按收益排好了序，越靠前越值得先做。

| 可用时间 | [研究方向（RS / RE）](ROADMAP.zh.md#研究方向rs--re) | [MLE](ROADMAP.zh.md#mle-方向) | [SWE / Infra](ROADMAP.zh.md#swe--infra-方向) |
| --- | --- | --- | --- |
| 一周左右 | 第 1–3 阶段，同时开始准备技术深挖和用人经理面的故事 | 所有 ★★★★☆ 及以上的题 | 所有 ★★★★☆ 及以上的题 |
| 两到四周 | 全部六个阶段 | 整条路线 | 整条路线 |
| 更长 | 加上其他路线里 ★★★★☆ 的题 | 加上研究方向路线里跳过的阶段 | 如果团队离模型比较近，加上研究方向路线的 ML 编程核心 |

### 2. 练一道题

**编程题。** 先只读**题目**一节。动手写代码之前，记下你会向面试官确认的问题（边界情况、并列时怎么处理、输入规模），
再和参考解答开头的几行对照，那里列出了值得确认的点。给整道题设一个时限，按顺序做各个部分，把每个新部分当作一次需求变更：
在已有代码上扩展，而不是推倒重来。先在示例上跑通，再展开参考解答，对照思路、复杂度和 `# NOTE:` 注释。
检查代码调用的是题面里给出的函数名，所以只要保持相同的函数名和签名，一般就能拿它来测你自己的实现。

**系统设计题。** 给自己一个小时左右（知道这一轮时长的，页头会写明），出声讲或在纸上写：需求、估算、API 与数据模型、
架构，然后选两三个点深入。再和参考解答对照：漏了哪条需求，哪里的数字对不上，哪种故障没处理。估算都在检查块里用代码
算过，可以改一个输入再跑一遍。

**行为面。** 每页列出这一轮考察什么、好的回答怎样组织，末尾有一份提纲，用你自己的经历填写。大声练几遍，
填好的版本自己保存，不要公开。

### 3. 一页的结构

每页开头是一张表（题型、优先级、难度、岗位、考点，已知的话还有形式和轮次），正文只有两节：

| 章节 | 编程题 | 系统设计题 | 行为面 |
| --- | --- | --- | --- |
| **题目** | 定义，然后每个部分一块：任务、函数签名、示例 | 要设计的系统、用户、给定的数字、范围 | 这一轮的形式和问题 |
| **参考解答**（折叠） | 按部分写思路、推导、代码，易错点是代码里的 `# NOTE:` 注释；最后是追问和检查代码 | 需求、数据模型与 API、架构、深入话题、追问 | 考察点、回答的结构、待填写的提纲 |

岗位缩写：**RS** 研究科学家 · **RE** 研究工程师 · **MLE** 机器学习工程师 · **SWE** 软件工程师 ·
**Infra Eng** 基础设施工程师 · **EM** 工程经理。

### 4. 运行代码

```bash
git clone https://github.com/Schuture/OpenAI-Interview-Notes.git
cd OpenAI-Interview-Notes
pip install -r requirements.txt                    # NumPy、SciPy、scikit-learn、PyTorch、Pillow
python scripts/run_snippets.py coding/gpu-credits   # 一页
python scripts/run_snippets.py --all                # 全部页面
```

一页里的 ```` ```python ```` 代码块按顺序作为一个脚本运行；```` ```py ```` 代码块只作示意（单独的函数签名、故意报错的代码），
不会执行。CI 使用 Python 3.11。

## 题目

每个分类内按优先级排序。难度一栏为 — 表示未评定。

<!-- index:begin -->
### 编程 (38)

| # | 题目 | 优先级 | 难度 | 岗位 | 考点 |
| ---: | --- | --- | --- | --- | --- |
| 1 | [感染扩散（网格元胞自动机）](coding/infection-spread/README.zh.md) | ★★★★★ | 中等 | SWE · MLE · RE · RS · EM | bfs, simulation, grid |
| 2 | [关注图与两跳推荐（社交网络）](coding/social-network/README.zh.md) | ★★★★★ | 中等 | SWE · RE | graph, hashmap, snapshot, binary-search |
| 3 | [集群节点计数与拓扑（树上消息传递）](coding/cluster-count-topology/README.zh.md) | ★★★★☆ | 中等 | SWE | tree, message-passing, distributed-systems, idempotency |
| 4 | [GPU 额度账本](coding/gpu-credits/README.zh.md) | ★★★★☆ | 中等 | SWE | data-structure, simulation, heap |
| 5 | [前缀矩阵连乘：Autograd、手写反向、Hillis–Steele 扫描](coding/autograd-hillis-steele/README.zh.md) | ★★★★☆ | 困难 | RS · RE · MLE | autograd, linear-algebra, parallel-scan, pytorch |
| 6 | [NumPy 1-NN 写成一层 Wx+b](coding/numpy-1nn-affine/README.zh.md) | ★★★★☆ | 中等 | MLE · RE | numpy, vectorization, broadcasting, linear-algebra |
| 7 | [怪兽对战](coding/monster-battle/README.zh.md) | ★★★★☆ | 中等 | SWE | oop-design, simulation |
| 8 | [Transformer 找 bug](coding/transformer-bug-hunt/README.zh.md) | ★★★★☆ | 中等 | MLE · RS · RE | transformer, debugging, kv-cache, pytorch |
| 9 | [内存分配器](coding/memory-allocator/README.zh.md) | ★★★★☆ | 困难 | SWE · MLE · RE | data-structure, intervals, balanced-bst |
| 10 | [含噪标注者](coding/noisy-annotators/README.zh.md) | ★★★★☆ | 中等 | MLE · RS · RE | data-cleaning, label-noise, evaluation, numpy |
| 11 | [玩具语言的类型推断](coding/type-inference/README.zh.md) | ★★★★☆ | 中等 | SWE · RE | recursion, unification, tree |
| 12 | [数据标注任务调度](coding/labeling-task-scheduler/README.zh.md) | ★★★★☆ | 中等 | SWE · RE · MLE | scheduling, greedy, fairness |
| 13 | [可持久化 KV 存储：自定义序列化](coding/durable-kv-store/README.zh.md) | ★★★☆☆ | 中等 | SWE · Infra Eng | serialization, persistence, parsing, storage, fault-tolerance |
| 14 | [流式熵计算](coding/streaming-entropy/README.zh.md) | ★★★☆☆ | 中等 | RS · RE · MLE | numerical-stability, softmax, streaming |
| 15 | [聊天机器人重构](coding/chat-bot-refactoring/README.zh.md) | ★★★☆☆ | 中等 | SWE | refactoring, oop-design, event-driven, testing |
| 16 | [IPv4 / CIDR 迭代器](coding/ipv4-cidr-iterator/README.zh.md) | ★★★☆☆ | 中等 | SWE | bit-manipulation, iterator, string |
| 17 | [带重叠上限的分片再平衡](coding/shard-rebalance/README.zh.md) | ★★★☆☆ | 中等 | SWE | intervals, greedy, heap, consistent-hashing |
| 18 | [只知道均值时的重启策略（Las Vegas）](coding/restart-strategy-math/README.zh.md) | ★★★☆☆ | 困难 | RS · RE | probability, inequalities, algorithm-design |
| 19 | [版本依赖](coding/version-dependency/README.zh.md) | ★★★☆☆ | 中等 | SWE · RE | binary-search, backtracking, topological-sort |
| 20 | [滑动窗口事件聚合](coding/event-window-aggregation/README.zh.md) | ★★★☆☆ | 中等 | SWE · Infra Eng | sliding-window, streaming, hashmap, heap |
| 21 | [三张牌的牌型与弃牌](coding/poker-hands/README.zh.md) | ★★★☆☆ | 中等 | SWE | simulation, sorting, rules-engine |
| 22 | [文本编辑器：缓冲区、撤销、补全](coding/text-editor/README.zh.md) | ★★★☆☆ | 中等 | SWE · RE | data-structure, stack, trie, collaboration |
| 23 | [容错工作队列](coding/fault-tolerant-work-queue/README.zh.md) | ★☆☆☆☆ | 中等 | Infra Eng | queue, state-machine, retry |
| 24 | [从零实现交叉熵损失](coding/cross-entropy-loss/README.zh.md) | ★☆☆☆☆ | 中等 | MLE · RE | numpy, numerical-stability, loss-functions, kl-divergence |
| 25 | [最多跳过 K 行的网格最优路径](coding/grid-path-limited-jumps/README.zh.md) | ★☆☆☆☆ | 困难 | SWE | dp, grid, counting |
| 26 | [cd 命令 / 路径解析](coding/cd-command/README.zh.md) | ★☆☆☆☆ | 中等 | SWE | string-processing, stack, symlinks |
| 27 | [带单元格依赖的电子表格（OpenSheet）](coding/spreadsheet-dependencies/README.zh.md) | ★☆☆☆☆ | 中等 | SWE | graph, dfs, topological-sort, recursion |
| 28 | [ModalLock 与 FairModalLock](coding/modal-lock/README.zh.md) | ★☆☆☆☆ | 困难 | SWE · MLE | concurrency, threading, fairness |
| 29 | [分片矩阵乘法：前向、反向与找 bug](coding/sharded-matmul-backprop/README.zh.md) | ★☆☆☆☆ | 困难 | MLE · RE | linear-algebra, parallelism, autograd, numpy, pytorch, debugging |
| 30 | [可恢复迭代器（一维、二维到任意深度）](coding/resumable-iterator/README.zh.md) | ★☆☆☆☆ | 中等 | SWE | iterator, oop-design, state |
| 31 | [PyTorch 读代码与扩展](coding/pytorch-code-reading/README.zh.md) | ★☆☆☆☆ | — | RE · MLE | code-reading, pytorch, complexity |
| 32 | [类 SQL 的内存数据库](coding/in-memory-database/README.zh.md) | ★☆☆☆☆ | 中等 | SWE | data-structure, oop-design, sql |
| 33 | [按时间点查询的 KV 存储](coding/time-based-kv-store/README.zh.md) | ★☆☆☆☆ | 中等 | SWE | binary-search, testing, concurrency |
| 34 | [灯塔光束与重尾分布](coding/cauchy-lighthouse/README.zh.md) | ★☆☆☆☆ | 困难 | RS · RE | probability, heavy-tails, simulation, estimation |
| 35 | [强化学习训练循环找 bug](coding/rl-training-debug/README.zh.md) | ★☆☆☆☆ | 困难 | RS · RE · MLE | reinforcement-learning, policy-gradient, debugging, pytorch |
| 36 | [限流器找 bug](coding/rate-limiter-debug/README.zh.md) | ★☆☆☆☆ | 中等 | SWE · Infra Eng | debugging, concurrency, sliding-window, testing |
| 37 | [带依赖的工具调用调度](coding/agent-tool-scheduler/README.zh.md) | ★☆☆☆☆ | 中等 | SWE · RE · Infra Eng | scheduling, dag, simulation, concurrency |
| 38 | [反馈延迟一轮的二分查找](coding/guess-number-delayed/README.zh.md) | ★☆☆☆☆ | 中等 | SWE · RE | binary-search, interaction, algorithm-design |

### 系统设计 (21)

| # | 题目 | 优先级 | 难度 | 岗位 | 考点 |
| ---: | --- | --- | --- | --- | --- |
| 1 | [支付系统 / 咖啡店点单](system-design/payment-coffee-shop/README.zh.md) | ★★★★★ | 中等 | SWE | payment, idempotency, ledger |
| 2 | [在线国际象棋平台（类 Chess.com）](system-design/chess-platform/README.zh.md) | ★★★★★ | — | SWE · Infra Eng | websocket, matchmaking, game-state, idempotency, consistent-hashing |
| 3 | [视频生成流水线（类 Sora）](system-design/video-generation-pipeline/README.zh.md) | ★★★★★ | 中等 | SWE · Infra Eng · EM | gpu-scheduling, queueing, fault-tolerance |
| 4 | [大模型推理服务](system-design/llm-inference-serving/README.zh.md) | ★★★★☆ | — | SWE · Infra Eng · MLE | gpu-scheduling, batching, streaming, rate-limiting, cost |
| 5 | [云端 IDE](system-design/cloud-ide/README.zh.md) | ★★★☆☆ | 困难 | SWE · Infra Eng · EM | sandbox, vm-lifecycle, websocket, streaming |
| 6 | [大规模设备监控与指令下发](system-design/device-fleet-monitoring/README.zh.md) | ★★★☆☆ | — | SWE · Infra Eng | iot, messaging, idempotency, reconciliation, telemetry |
| 7 | [带去重的图片分享](system-design/image-dedup-sharing/README.zh.md) | ★★☆☆☆ | 中等 | SWE | storage, deduplication, consistency |
| 8 | [分布式填字游戏求解器](system-design/crossword-solver/README.zh.md) | ★★☆☆☆ | — | SWE · Infra Eng | distributed-search, backtracking, job-system |
| 9 | [AI 聊天机器人前端](system-design/ai-chatbot-frontend/README.zh.md) | ★★☆☆☆ | — | SWE | frontend, streaming, client-state, auth |
| 10 | [多租户 CI/CD](system-design/multi-tenant-ci-cd/README.zh.md) | ★★☆☆☆ | — | SWE · Infra Eng | scheduling, exactly-once, multi-tenancy |
| 11 | [类 Slack 即时通讯](system-design/slack/README.zh.md) | ★★☆☆☆ | — | SWE · EM | messaging, pubsub, multi-device, multi-tenancy |
| 12 | [搜索与 RAG 的 ML 设计（口述）](system-design/rag-search-ml-design/README.zh.md) | ★★☆☆☆ | — | RE · MLE | retrieval, contrastive-learning, ranking, evaluation |
| 13 | [日历（类 Google Calendar）](system-design/google-calendar/README.zh.md) | ★★☆☆☆ | — | SWE | schema-design, caching, sync |
| 14 | [短链接服务](system-design/url-shortener/README.zh.md) | ★★☆☆☆ | — | SWE | hashing, caching, scaling, database |
| 15 | [Webhook 投递](system-design/webhook-delivery/README.zh.md) | ★★☆☆☆ | — | SWE · Infra Eng | queueing, retry, idempotency, security |
| 16 | [附近地点（POI / 类 Yelp）](system-design/nearby-poi/README.zh.md) | ★★☆☆☆ | — | SWE | geospatial-index, sharding, caching |
| 17 | [流式 AI 产品功能](system-design/realtime-ai-feature/README.zh.md) | ★☆☆☆☆ | — | SWE | streaming, api-design, rate-limiting, fullstack |
| 18 | [从无标注语料中挖掘新数据](system-design/mining-novel-data/README.zh.md) | ★☆☆☆☆ | — | MLE | ml-system-design, data-mining, retrieval |
| 19 | [ChatGPT Enterprise：基于企业数据的 RAG](system-design/chatgpt-enterprise-rag/README.zh.md) | ★☆☆☆☆ | — | MLE · RE | rag, retrieval, access-control |
| 20 | [GPT-3 Playground（全栈）](system-design/gpt3-playground/README.zh.md) | ★☆☆☆☆ | — | SWE | fullstack, frontend, streaming, schema-design |
| 21 | [Agent 执行框架与评测体系](system-design/agent-harness-eval/README.zh.md) | ★☆☆☆☆ | — | RE · MLE · RS | agent, evaluation, tooling, observability |

### 行为面与其他 (4)

| # | 题目 | 优先级 | 难度 | 岗位 | 考点 |
| ---: | --- | --- | --- | --- | --- |
| 1 | [用人经理轮：Why OpenAI、安全、AGI](behavioral/hiring-manager-why-openai/README.zh.md) | ★★★★★ | — | 全部 | behavioral, why-company, ai-safety, cross-functional |
| 2 | [技术深挖（带幻灯片）](behavioral/technical-deep-dive/README.zh.md) | ★★★★★ | — | SWE · MLE · RE · Infra Eng | presentation, project-deep-dive |
| 3 | [Recruiter / HR 初筛](behavioral/recruiter-screen/README.zh.md) | ★★★★☆ | — | 全部 | behavioral, process, compensation, ai-safety |
| 4 | [工程管理轮](behavioral/engineering-management/README.zh.md) | ★☆☆☆☆ | — | EM | leadership, hiring, mentorship, performance-management, team-composition |
<!-- index:end -->

## 参与贡献

欢迎勘误、补充变体和改进翻译。发现答案有错、漏了边界情况，或者有读不通的句子？请[提一个 issue](https://github.com/Schuture/OpenAI-Interview-Notes/issues)。
提交 pull request 之前请先看 [CONTRIBUTING.zh.md](CONTRIBUTING.zh.md)。

## 许可

文字（正文、表格和图示）采用 [CC BY-NC 4.0](LICENSE) 许可；代码（页面里的代码和 `scripts/` 下的脚本）采用
[MIT 许可](LICENSE-CODE)。
