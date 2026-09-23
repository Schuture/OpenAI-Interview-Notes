# 强化学习训练循环找 bug

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 调试 · PyTorch | ★☆☆☆☆ | 困难 | RS · RE · MLE | reinforcement-learning, policy-gradient, debugging, pytorch | 4 个 bug + 5 个追问 |
<!-- meta:end -->

## 题目

下面的文件 `gridworld_pg.py` 用*策略梯度*（policy gradient）在一个小网格世界上训练策略。训练能一路跑到底、不报错，
而智能体始终没有变好。

环境是一个 5 × 5 的网格，25 个格子按行优先编号。智能体从 0 号格子出发，每步在四个动作里选一个；会走出网格的动作让位置保持不变。
走到 24 号格子得到 1 的奖励，并结束这一*回合*（episode），即从起点格子走到目标为止的一次运行；随后环境立刻回到 0 号格子重新开始。
其余每一步的代价是 0.02。下一个格子只由当前格子和动作决定。

```text
格子编号              动作
 0  1  2  3  4        0 = 上（row - 1）
 5  6  7  8  9        1 = 下（row + 1）
10 11 12 13 14        2 = 左（col - 1）
15 16 17 18 19        3 = 右（col + 1）
20 21 22 23 24
```

一次*采样*（rollout）是在并行的 64 份环境副本里各走 20 步，每一步的动作都从当前策略抽样得到；因此一份副本在一次采样里可能走完
不止一个回合。从 0 号格子到 24 号格子最短要八步，所以最好的一次采样能两次到达目标，收集 $2 \cdot 1 - 18 \cdot 0.02 = 1.640$，
而一个从不到达目标的策略只收集 $20 \cdot (-0.02) = -0.400$。

`PolicyValue` 把一个格子映射成四个动作的 logits，以及一个*基线*（baseline）$V(s)$，也就是网络自己学出来的、
对这个格子能带来多少回报的估计。
每一轮训练采样一次，然后对下式做一步 Adam（学习率 0.02）：

$$
\mathcal{L} = -\overline{\log \pi(a_t \mid s_t) \cdot A_t} \; + \; 0.5 \cdot \overline{(G_t - V(s_t))^2} \; - \; 0.02 \cdot \overline{H_t}
$$

其中横线表示对一次采样的 $20 \times 64$ 步取平均，$G_t$ 是第 $t$ 步在它自己那一回合内的折扣*剩余回报*（reward-to-go），
折扣因子 $\gamma = 0.97$；*优势*（advantage）$A_t$ 是第 $t$ 步的实际结果比基线预测的好多少；$H_t$ 是 $s_t$ 处动作分布的熵，
把它作为奖励加进去，是为了不让策略在还没找到任何东西之前就变成确定性的。训练跑 120 轮，随后 `run_tests` 检查五件事：

1. 一次采样里的两份环境副本不会走出完全相同的轨迹；
2. 在一批回报高于基线的数据上走一步梯度之后，所采取的那个动作变得更可能，而不是更不可能；
3. `compute_returns` 能重现一段手写的四步数据的折扣剩余回报；
4. 基线没有偏差：最后十轮的平均优势与 0 的距离在 0.1 以内；
5. 最后十轮里智能体每次采样收集到的奖励超过 1.5。

### 找出并修复四个 bug

文件里有四行写错了：一行在 `rollout`，一行在 `compute_returns`，两行在 `surrogate`。把它们一一找出来，
说明每一行对梯度和对训练做了什么、为什么，然后改好。四行都改对之后，`python gridworld_pg.py` 的 120 轮
（CPU 上几秒钟）跑完时五个测试全部通过，并打印 `all tests passed`。环境、网络、测试和超参数都是对的，
这四行之外不需要改动任何东西。

```py
import torch
import torch.nn as nn
from torch.distributions import Categorical

GRID, START, GOAL = 5, 0, 24                # states 0..24 of a 5x5 grid, row-major; 0 is top-left
HORIZON, STEP_COST, GAMMA = 20, 0.02, 0.97
VALUE_COEF, ENT_COEF = 0.5, 0.02


def env_step(pos, action):                  # pos, action: (B,) long
    """One step in every environment. Returns the next position, the reward and the done flag."""
    row, col = pos // GRID, pos % GRID
    row = (row + (action == 1).long() - (action == 0).long()).clamp(0, GRID - 1)   # 0 = up, 1 = down
    col = (col + (action == 3).long() - (action == 2).long()).clamp(0, GRID - 1)   # 2 = left, 3 = right
    moved = row * GRID + col
    done = moved == GOAL
    reward = torch.where(done, 1.0, -STEP_COST)
    return torch.where(done, torch.full_like(moved, START), moved), reward, done


class PolicyValue(nn.Module):
    def __init__(self, n_states=GRID * GRID, n_actions=4, hidden=64):
        super().__init__()
        self.trunk = nn.Sequential(nn.Embedding(n_states, hidden), nn.Tanh())
        self.policy = nn.Linear(hidden, n_actions)
        self.value = nn.Linear(hidden, 1)

    def forward(self, pos):                 # pos: (...,) long -> logits (..., n_actions), values (...,)
        hidden = self.trunk(pos)
        return self.policy(hidden), self.value(hidden).squeeze(-1)


@torch.no_grad()
def rollout(model, n_envs):
    """HORIZON steps in n_envs environments. Every returned tensor has shape (HORIZON, n_envs)."""
    pos = torch.full((n_envs,), START)
    states, actions, rewards, dones = [], [], [], []
    for _ in range(HORIZON):
        logits, _ = model(pos)
        action = logits.argmax(dim=-1)
        states.append(pos)
        actions.append(action)
        pos, reward, done = env_step(pos, action)
        rewards.append(reward)
        dones.append(done)
    return torch.stack(states), torch.stack(actions), torch.stack(rewards), torch.stack(dones)


def compute_returns(rewards, dones):        # rewards, dones: (T, B) -> (T, B)
    """returns[t] is the discounted reward-to-go of step t inside its own episode."""
    returns = torch.zeros_like(rewards)
    running = torch.zeros(rewards.shape[1])
    for t in range(rewards.shape[0]):
        running = rewards[t] + GAMMA * running * (~dones[t]).float()
        returns[t] = running
    return returns


def surrogate(model, states, actions, returns):
    """The loss whose gradient is the policy gradient, plus the baseline and entropy terms."""
    logits, values = model(states)
    dist = Categorical(logits=logits)
    advantages = values - returns
    policy_loss = -(dist.log_prob(actions) * advantages).mean()
    value_loss = advantages.pow(2).mean()
    entropy = dist.entropy().mean()
    loss = policy_loss + VALUE_COEF * value_loss - ENT_COEF * entropy
    return loss, {"value_loss": value_loss.item(), "entropy": entropy.item(),
                  "advantage": advantages.mean().item()}


def train(iters=120, n_envs=64, lr=0.02, seed=0):
    torch.manual_seed(seed)
    model = PolicyValue()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    history = []
    for it in range(iters):
        states, actions, rewards, dones = rollout(model, n_envs)
        returns = compute_returns(rewards, dones)
        loss, stats = surrogate(model, states, actions, returns)
        opt.zero_grad()
        loss.backward()
        opt.step()
        history.append({"reward": rewards.sum(0).mean().item(), **stats})
        if it % 20 == 0 or it == iters - 1:
            h = history[-1]
            print(f"iter {it:3d}  reward {h['reward']:+.3f}  entropy {h['entropy']:.3f}  "
                  f"value loss {h['value_loss']:.3f}  mean adv {h['advantage']:+.3f}")
    return model, history


def run_tests(model, history):
    _, actions, _, _ = rollout(model, 64)
    assert not (actions == actions[:, :1]).all(), "test 1: every environment ran the same trajectory"

    torch.manual_seed(7)
    probe = PolicyValue()
    states, taken = torch.full((1, 8), START), torch.zeros(1, 8, dtype=torch.long)
    returns = torch.full((1, 8), 5.0)       # far above anything the untrained value head predicts
    with torch.no_grad():
        before = Categorical(logits=probe(states)[0]).log_prob(taken).mean().item()
    opt = torch.optim.SGD(probe.parameters(), lr=0.1)
    loss, _ = surrogate(probe, states, taken, returns)
    opt.zero_grad()
    loss.backward()
    opt.step()
    with torch.no_grad():
        after = Categorical(logits=probe(states)[0]).log_prob(taken).mean().item()
    assert after > before, f"test 2: log pi of a rewarded action went {before:.3f} -> {after:.3f}"

    rewards = torch.tensor([[-0.02], [-0.02], [1.0], [-0.02]])
    dones = torch.tensor([[False], [False], [True], [False]])
    got = [round(x, 4) for x in compute_returns(rewards, dones).flatten().tolist()]
    assert got == [0.9015, 0.95, 1.0, -0.02], f"test 3: reward-to-go is {got}"

    bias = sum(h["advantage"] for h in history[-10:]) / 10
    assert abs(bias) < 0.1, f"test 4: the baseline is off by {bias:+.3f} on average"

    mean_reward = sum(h["reward"] for h in history[-10:]) / 10
    assert mean_reward > 1.5, f"test 5: the agent collects only {mean_reward:+.3f} per rollout"


if __name__ == "__main__":
    model, history = train()
    run_tests(model, history)
    print("all tests passed")
```

## 参考解答

<details>
<summary>展开参考解答</summary>

先把脚本跑起来，把打印出来的四列当成四个仪表来读：`reward` 说明智能体有没有在变好，`entropy` 说明策略还在不在探索，
`value loss` 和 `mean adv` 说明基线靠不靠得住。损失的数值不在这几个仪表之列：它是一个代理量，尺度随优势一起变化，
看着它往下掉并不能说明策略在变好。每个 bug 都挡着下一个，而每一个都由一条不同的失败测试钉住。

### 四个 bug

| 已修复的 bug | `python gridworld_pg.py` 的输出 | 指向 |
| --- | --- | --- |
| 无 | 每一行打印出的 `reward` 都是 `-0.400`；`test 1: every environment ran the same trajectory` | bug 1，动作是怎么选的 |
| 1 | `reward` 再没高过第一轮的 -0.272，最后 50 轮死死钉在 -0.400；`test 2: log pi of a rewarded action went -1.671 -> -15.674` | bug 2，优势的符号 |
| 1、2 | `reward` 在全部 120 轮里都落在 -0.400 与 -0.209 之间；`test 3: reward-to-go is [-0.02, -0.0394, 1.0, 0.95]` | bug 3，循环的方向 |
| 1、2、3 | `reward` 涨到 +1.576；`test 4: the baseline is off by -0.545 on average` | bug 4，少了 `detach()` |
| 全部 | `reward` +1.640，`value loss` 0.077，`mean adv` +0.010；`all tests passed` | |

这四个 bug 分别落在训练循环的四个接缝上：数据是怎么采的（`rollout`）、采来的每一步拿到什么分数（`compute_returns`）、
分数怎么变成梯度（`surrogate` 里的符号）、梯度又沿哪些路径流回参数（`surrogate` 里的 `detach`）。每个接缝都可以不训练、
单独验证。

**Bug 1：`rollout` 里的 `action = logits.argmax(dim=-1)`。** 策略梯度是
$\nabla_\theta J = \mathbb{E}_{a \sim \pi}[\nabla_\theta \log \pi(a \mid s) \, A(s, a)]$，这里用的单样本形式，
只有当动作确实是从 $\pi$ 抽样得到时才是它的无偏估计。`argmax` 把行为变成确定性的，于是 64 份副本——同样的起点格子、
同样的转移规则——走的是同一条轨迹，一次采样的 1280 步携带的信息只相当于一条轨迹。这 120 轮里 reward 只取两个值：
119 轮是 -0.400，一轮是 +1.640，要么那条唯一的路径恰好穿过目标，要么整批一个也到不了。没有哪一步会去试别的动作，
而 $\nabla \log \pi(\arg\max)$ 只是把网络已有的偏好变得更尖锐。评估策略的时候用贪心选择是对的，这样一行代码通常也正是
从评估那里来的；但给梯度供数据的采样必须是抽样。

```py
action = Categorical(logits=logits).sample()        # was logits.argmax(dim=-1)
```

**Bug 2：`surrogate` 里的 `advantages = values - returns`。** 优势是回报减去基线。两者写反之后，`policy_loss` 变成
$+\overline{\log \pi \cdot (G - V)}$，对它做梯度下降就是对期望回报做下降：每一个比预测做得更好的步骤反而被压得更不可能。
测试 2 在八份同样的数据上走一步 SGD，这些数据的回报是 5.0，远高于未训练的基线能给出的任何值，而所采取动作的对数概率
从 -1.671 掉到了 -15.674。训练中智能体学会了躲开 24 号格子：reward 再没高过第一轮的 -0.272，最后停在 -0.400，也就是这个环境的下界——
20 步各 -0.02，奖励一次也没拿到。`value_loss` 取的是同一个差的平方，所以它不会有任何反应。

```py
advantages = returns - values                       # was values - returns
```

**Bug 3：`compute_returns` 里的 `for t in range(rewards.shape[0])`。** 剩余回报在一个回合内满足
$G_t = r_t + \gamma G_{t+1}$，所以这个递推必须从最后一步倒着展开；`dones` 那个因子的作用是不让它跨过回合的结尾。
正着跑，它算出来的是 $G_t = r_t + \gamma r_{t-1} + \gamma^2 r_{t-2} + \cdots$，即第 $t$ 步*之前*收集到的奖励的折扣和。
在测试 3 那段四步数据上，奖励是 $(-0.02, -0.02, 1, -0.02)$、第三步终止，正确答案是 `[0.9015, 0.95, 1.0, -0.02]`，
而这个循环给出 `[-0.02, -0.0394, 1.0, 0.95]`：目标奖励被记到了到达目标*之后*的那一步上，通往目标的那些步一分没得。
一步不可能造成它之前发生的事，所以这样的分数不含任何关于该动作的信号，reward 在全部 120 轮里都落在 -0.400 与 -0.209 之间。

```py
for t in reversed(range(rewards.shape[0])):         # was range(rewards.shape[0])
```

**Bug 4：`policy_loss` 里的 `advantages` 没有 detach。** 在 $\nabla \log \pi \cdot A$ 里，优势是一个系数——
一个说明该往哪个方向推、推多用力的数——而不是一个要对它求导的函数。不 detach 就等于从 `policy_loss` 又开了一条通往 `value` 的路，
于是两项在互相抵消的地方停下来。逐步来看，略去两个均值共同带来的 $1/N$，损失对 $V$ 的导数是
$\log \pi(a \mid s) + 2 \cdot 0.5 \cdot (V - G)$，它在

$$
G - V = \log \pi(a \mid s)
$$

处为零，也就是说基线最终停在它本该预测的回报之上一个*意外度*（surprisal）的位置；对一次采样取平均之后，
优势等于熵的相反数：第 119 轮的平均优势是 -0.586，而熵是 0.612，`value loss` 是 0.528 而不是 0.077。训练照样能进行，
因为 $-H(s)$ 只取决于状态、不取决于所采取的动作，而把基线平移一个只依赖状态的量并不会让策略梯度有偏——它只是增大了
方差：这次训练仍然摸到了最优的 +1.640。被毁掉的是价值估计本身，而自举的目标或者 KL 惩罚都要建立在它上面。
一个不用训练就能定案的检查：`torch.autograd.grad(policy_loss, model.value.weight, allow_unused=True)[0]`
必须是 `None`，不是的话就说明策略项在训练基线。

```py
policy_loss = -(dist.log_prob(actions) * advantages.detach()).mean()    # was advantages
```

### 追问

- 把一次采样用于多步梯度更新会破坏这个估计量，因为从第二步起，对数概率来自一个并没有采集这批数据的策略。
  PPO 和 GRPO 用重要性比值 $\pi_\theta(a \mid s) / \pi_{\mathrm{old}}(a \mid s)$ 来修正，并把它裁剪到
  $[1 - \epsilon, 1 + \epsilon]$，这样一旦一次更新把某个动作沿它优势所指的方向推过了裁剪边界，
  它就不再贡献梯度。
- 对参考策略的 KL 惩罚约束的是整个分布的漂移，这是裁剪比值做不到的：裁剪只管得住出现在这批数据里的那些动作。
  在 RLHF 里参考策略是进入 RL 阶段之前的那个策略，这一项惩罚正是让模型不至于坍塌到奖励模型打分最高的那类输出上。
- 用优势而不是原始回报，是因为对任何不依赖动作的 $b$ 都有
  $\mathbb{E}_{a \sim \pi}[\nabla \log \pi(a \mid s) \, b(s)] = 0$：减去一个基线不改变任何期望，只改变方差。
  只用回报的话，在一个好状态里采取的每个动作都会被强化，包括其中差的那些。
- GRPO 干脆去掉价值网络：它对同一个提示采样一组 $K$ 个回答，用这一组自己的平均回报当基线。这样就没有一个学出来的估计
  可供 bug 4 去污染，代价是每个提示要采样 $K$ 次，而且基线只在这一组回答之间做比较。
- 一次采样走满 20 步就停，不管回合结束没有，而 `compute_returns` 把这个截断当成回合结束来处理，于是最后几步丢掉了
  截断之后的那一段。通常的补法是：只要一份副本不是刚好终止，就给它停下来的那个格子补上 $\gamma V(s)$，
  这就要求掩码里把“回合结束”和“采样步数用完”分开。

<details>
<summary>修复后的完整文件与验证代码（可运行）</summary>

```python
import torch
import torch.nn as nn
from torch.distributions import Categorical

GRID, START, GOAL = 5, 0, 24                # states 0..24 of a 5x5 grid, row-major; 0 is top-left
HORIZON, STEP_COST, GAMMA = 20, 0.02, 0.97
VALUE_COEF, ENT_COEF = 0.5, 0.02


def env_step(pos, action):                  # pos, action: (B,) long
    """One step in every environment. Returns the next position, the reward and the done flag."""
    row, col = pos // GRID, pos % GRID
    row = (row + (action == 1).long() - (action == 0).long()).clamp(0, GRID - 1)   # 0 = up, 1 = down
    col = (col + (action == 3).long() - (action == 2).long()).clamp(0, GRID - 1)   # 2 = left, 3 = right
    moved = row * GRID + col
    done = moved == GOAL
    reward = torch.where(done, 1.0, -STEP_COST)
    return torch.where(done, torch.full_like(moved, START), moved), reward, done


class PolicyValue(nn.Module):
    def __init__(self, n_states=GRID * GRID, n_actions=4, hidden=64):
        super().__init__()
        self.trunk = nn.Sequential(nn.Embedding(n_states, hidden), nn.Tanh())
        self.policy = nn.Linear(hidden, n_actions)
        self.value = nn.Linear(hidden, 1)

    def forward(self, pos):                 # pos: (...,) long -> logits (..., n_actions), values (...,)
        hidden = self.trunk(pos)
        return self.policy(hidden), self.value(hidden).squeeze(-1)


@torch.no_grad()
def rollout(model, n_envs):
    """HORIZON steps in n_envs environments. Every returned tensor has shape (HORIZON, n_envs)."""
    pos = torch.full((n_envs,), START)
    states, actions, rewards, dones = [], [], [], []
    for _ in range(HORIZON):
        logits, _ = model(pos)
        action = Categorical(logits=logits).sample()        # bug 1: was logits.argmax(dim=-1)
        states.append(pos)                                  # NOTE: the square the action was chosen in
        actions.append(action)
        pos, reward, done = env_step(pos, action)
        rewards.append(reward)
        dones.append(done)
    return torch.stack(states), torch.stack(actions), torch.stack(rewards), torch.stack(dones)


def compute_returns(rewards, dones):        # rewards, dones: (T, B) -> (T, B)
    """returns[t] is the discounted reward-to-go of step t inside its own episode."""
    returns = torch.zeros_like(rewards)
    running = torch.zeros(rewards.shape[1])
    for t in reversed(range(rewards.shape[0])):             # bug 3: was range(rewards.shape[0])
        # NOTE: a terminal step cuts the chain, so no reward of the next episode leaks into this one
        running = rewards[t] + GAMMA * running * (~dones[t]).float()
        returns[t] = running
    return returns


def surrogate(model, states, actions, returns):
    """The loss whose gradient is the policy gradient, plus the baseline and entropy terms."""
    logits, values = model(states)
    dist = Categorical(logits=logits)
    advantages = returns - values                           # bug 2: was values - returns
    # NOTE: detach, or the policy term trains the baseline to sit one surprisal above the return
    policy_loss = -(dist.log_prob(actions) * advantages.detach()).mean()    # bug 4: was advantages
    value_loss = advantages.pow(2).mean()
    entropy = dist.entropy().mean()
    loss = policy_loss + VALUE_COEF * value_loss - ENT_COEF * entropy
    return loss, {"value_loss": value_loss.item(), "entropy": entropy.item(),
                  "advantage": advantages.mean().item()}


def train(iters=120, n_envs=64, lr=0.02, seed=0):
    torch.manual_seed(seed)
    model = PolicyValue()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    history = []
    for it in range(iters):
        states, actions, rewards, dones = rollout(model, n_envs)
        returns = compute_returns(rewards, dones)
        loss, stats = surrogate(model, states, actions, returns)
        opt.zero_grad()
        loss.backward()
        opt.step()
        history.append({"reward": rewards.sum(0).mean().item(), **stats})
        if it % 20 == 0 or it == iters - 1:
            h = history[-1]
            print(f"iter {it:3d}  reward {h['reward']:+.3f}  entropy {h['entropy']:.3f}  "
                  f"value loss {h['value_loss']:.3f}  mean adv {h['advantage']:+.3f}")
    return model, history


def run_tests(model, history):
    _, actions, _, _ = rollout(model, 64)
    assert not (actions == actions[:, :1]).all(), "test 1: every environment ran the same trajectory"

    torch.manual_seed(7)
    probe = PolicyValue()
    states, taken = torch.full((1, 8), START), torch.zeros(1, 8, dtype=torch.long)
    returns = torch.full((1, 8), 5.0)       # far above anything the untrained value head predicts
    with torch.no_grad():
        before = Categorical(logits=probe(states)[0]).log_prob(taken).mean().item()
    opt = torch.optim.SGD(probe.parameters(), lr=0.1)
    loss, _ = surrogate(probe, states, taken, returns)
    opt.zero_grad()
    loss.backward()
    opt.step()
    with torch.no_grad():
        after = Categorical(logits=probe(states)[0]).log_prob(taken).mean().item()
    assert after > before, f"test 2: log pi of a rewarded action went {before:.3f} -> {after:.3f}"

    rewards = torch.tensor([[-0.02], [-0.02], [1.0], [-0.02]])
    dones = torch.tensor([[False], [False], [True], [False]])
    got = [round(x, 4) for x in compute_returns(rewards, dones).flatten().tolist()]
    assert got == [0.9015, 0.95, 1.0, -0.02], f"test 3: reward-to-go is {got}"

    bias = sum(h["advantage"] for h in history[-10:]) / 10
    assert abs(bias) < 0.1, f"test 4: the baseline is off by {bias:+.3f} on average"

    mean_reward = sum(h["reward"] for h in history[-10:]) / 10
    assert mean_reward > 1.5, f"test 5: the agent collects only {mean_reward:+.3f} per rollout"


if __name__ == "__main__":
    model, history = train()
    run_tests(model, history)
    print("all tests passed")
```

```python
model, history = train()                                    # the fixed file
run_tests(model, history)
fixed_reward = sum(h["reward"] for h in history[-10:]) / 10


@torch.no_grad()
def given_rollout(model, n_envs):                           # bug 1 back in place
    pos = torch.full((n_envs,), START)
    states, actions, rewards, dones = [], [], [], []
    for _ in range(HORIZON):
        logits, _ = model(pos)
        action = logits.argmax(dim=-1)
        states.append(pos)
        actions.append(action)
        pos, reward, done = env_step(pos, action)
        rewards.append(reward)
        dones.append(done)
    return torch.stack(states), torch.stack(actions), torch.stack(rewards), torch.stack(dones)


def given_returns(rewards, dones):                          # bug 3 back in place
    returns = torch.zeros_like(rewards)
    running = torch.zeros(rewards.shape[1])
    for t in range(rewards.shape[0]):
        running = rewards[t] + GAMMA * running * (~dones[t]).float()
        returns[t] = running
    return returns


def make_surrogate(flip_sign):                              # bugs 2 and 4 back in place
    def given_surrogate(model, states, actions, returns):
        logits, values = model(states)
        dist = Categorical(logits=logits)
        advantages = (values - returns) if flip_sign else (returns - values)
        policy_loss = -(dist.log_prob(actions) * advantages).mean()
        value_loss = advantages.pow(2).mean()
        entropy = dist.entropy().mean()
        loss = policy_loss + VALUE_COEF * value_loss - ENT_COEF * entropy
        return loss, {"value_loss": value_loss.item(), "entropy": entropy.item(),
                      "advantage": advantages.mean().item()}
    return given_surrogate


fixed_functions = (rollout, compute_returns, surrogate)     # train() reads the three as globals
rollout, compute_returns, surrogate = given_rollout, given_returns, make_surrogate(True)
_, given_history = train()
given_reward = sum(h["reward"] for h in given_history[-10:]) / 10
assert {round(h["reward"], 3) for h in given_history} == {-0.4, 1.64}    # bug 1: one trajectory per rollout,
assert sum(1 for h in given_history if h["reward"] > 0) == 1            # crossing the goal on 1 of 120
assert abs(given_reward + 0.4) < 1e-6 and fixed_reward > 1.5            # the floor against near-optimal

rollout, compute_returns = fixed_functions[:2]              # only bug 4 left: the baseline drifts up
surrogate = make_surrogate(False)
model4, history4 = train()
vloss = lambda hs: sum(h["value_loss"] for h in hs[-10:])     # learns, but the baseline is ruined
assert sum(h["reward"] for h in history4[-10:]) / 10 > 1.5 and vloss(history4) > 2 * vloss(history)
states, actions, rewards, dones = rollout(model4, 256)
with torch.no_grad():
    dist, values = Categorical(logits=model4(states)[0]), model4(states)[1]
    mean_adv = (compute_returns(rewards, dones) - values).mean().item()
    assert abs(mean_adv - dist.log_prob(actions).mean().item()) < 0.05      # G - V settles at log pi
    assert abs(mean_adv + dist.entropy().mean().item()) < 0.05              # so its mean is -H
surrogate = fixed_functions[2]

torch.manual_seed(3)                                        # the gradient path the detach() closes
probe = PolicyValue()
s, a, g = torch.randint(0, 25, (4, 16)), torch.randint(0, 4, (4, 16)), torch.randn(4, 16)
logits, values = probe(s)
logp = Categorical(logits=logits).log_prob(a)
attached = -(logp * (g - values)).mean()
assert torch.autograd.grad(attached, probe.value.weight, retain_graph=True, allow_unused=True)[0] is not None
detached = -(logp * (g - values).detach()).mean()
assert torch.autograd.grad(detached, probe.value.weight, allow_unused=True)[0] is None

# bug 3: forwards, the reward-to-go of a step is a discounted sum of the rewards collected before it
r, d = torch.tensor([[-0.02], [-0.02], [1.0], [-0.02]]), torch.tensor([[False], [False], [True], [False]])
assert [round(x, 4) for x in given_returns(r, d).flatten().tolist()] == [-0.02, -0.0394, 1.0, 0.95]
```

</details>

</details>
