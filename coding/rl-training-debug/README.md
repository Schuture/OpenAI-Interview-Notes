# RL Training Loop Bug Hunt

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format |
| --- | --- | --- | --- | --- | --- |
| Debugging · PyTorch | ★☆☆☆☆ | Hard | RS · RE · MLE | reinforcement-learning, policy-gradient, debugging, pytorch | 4 bugs + 5 follow-ups |
<!-- meta:end -->

## Problem

The file `gridworld_pg.py` below trains a policy on a small grid world with a policy gradient. Training
runs to the end without an error, and the agent never gets better.

The environment is a 5 by 5 grid whose 25 squares are numbered row-major. The agent starts on square 0
and picks one of four actions; a move that would leave the grid leaves the position unchanged. Reaching
square 24 pays a reward of 1 and ends the *episode*, one run from the start square until the goal is
reached; the environment restarts on square 0 at once. Every other step costs 0.02. The next square is a
function of the current square and the action alone.

```text
square ids           actions
 0  1  2  3  4       0 = up      (row - 1)
 5  6  7  8  9       1 = down    (row + 1)
10 11 12 13 14       2 = left    (col - 1)
15 16 17 18 19       3 = right   (col + 1)
20 21 22 23 24
```

One *rollout* is 20 steps in each of 64 copies of the environment, run in parallel, with the action at
every step drawn from the current policy; a copy can therefore finish more than one episode in a
rollout. The shortest path from square 0 to square 24 is eight moves, so the best possible rollout
reaches the goal twice and collects $2 \cdot 1 - 18 \cdot 0.02 = 1.640$, while a policy that never
reaches the goal collects $20 \cdot (-0.02) = -0.400$.

`PolicyValue` maps a square to the logits of the four actions and to a *baseline* $V(s)$, a learned
estimate of the return that square is worth. One training iteration draws a rollout and takes a single
Adam step (learning rate 0.02) on

$$
\mathcal{L} = -\overline{\log \pi(a_t \mid s_t) \cdot A_t} \; + \; 0.5 \cdot \overline{(G_t - V(s_t))^2} \; - \; 0.02 \cdot \overline{H_t}
$$

where the bar is the mean over the $20 \times 64$ steps of the rollout, $G_t$ is the discounted
reward-to-go of step $t$ inside its own episode with $\gamma = 0.97$, the *advantage* $A_t$ is how much
better step $t$ turned out than the baseline predicted, and $H_t$ is the entropy of the action
distribution at $s_t$, whose bonus keeps the policy from turning deterministic before it has found
anything. Training runs for 120 iterations. `run_tests` then checks five things:

1. two copies of the environment in one rollout do not follow the same trajectory;
2. one gradient step on a batch whose return beats the baseline makes the action that was taken more
   likely, not less;
3. `compute_returns` reproduces the discounted reward-to-go of a hand-written four-step stretch;
4. the baseline is unbiased: the mean advantage over the last ten iterations is within 0.1 of zero;
5. over the last ten iterations the agent collects more than 1.5 per rollout.

### Find and fix the four bugs

Four lines of the file are wrong: one in `rollout`, one in `compute_returns`, and two in `surrogate`.
Locate each of them, say what it does to the gradient and to training and why, and repair it. Once all
four are right, the 120 iterations of `python gridworld_pg.py` (a few seconds on a CPU) end with every
test passing and the line `all tests passed`. The environment, the network, the tests and the
hyperparameters are all correct; nothing outside those four lines needs changing.

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

## Reference solution

<details>
<summary>Show the reference solution</summary>

Start by running the script and reading its four printed columns as four instruments: `reward` says
whether the agent is getting better, `entropy` whether the policy still explores, `value loss` and
`mean adv` whether the baseline is any good. The value of the loss is not one of the instruments: it is
a surrogate whose scale moves with the advantages, and watching it fall is no evidence that the policy
is improving. Each bug hides the next one, and each is pinned down by a different failing test.

### The four bugs

| Bugs fixed so far | Output of `python gridworld_pg.py` | Points to |
| --- | --- | --- |
| none | `reward` is `-0.400` at every printed iteration; `test 1: every environment ran the same trajectory` | bug 1, how the action is picked |
| 1 | `reward` never gets above the -0.272 of the first iteration and is pinned at -0.400 over the last 50; `test 2: log pi of a rewarded action went -1.671 -> -15.674` | bug 2, the sign of the advantage |
| 1, 2 | `reward` stays between -0.400 and -0.209 for all 120 iterations; `test 3: reward-to-go is [-0.02, -0.0394, 1.0, 0.95]` | bug 3, the direction of the loop |
| 1, 2, 3 | `reward` climbs to +1.576; `test 4: the baseline is off by -0.545 on average` | bug 4, the missing `detach()` |
| all | `reward` +1.640, `value loss` 0.077, `mean adv` +0.010; `all tests passed` | |

The four bugs sit at four joints of the loop: how the data is collected (`rollout`), how each step in it
is scored (`compute_returns`), how a score turns into a gradient (the sign in `surrogate`), and which
paths that gradient takes back into the parameters (the `detach` in `surrogate`). Each joint can be
checked on its own, without training anything.

**Bug 1: `action = logits.argmax(dim=-1)` in `rollout`.** The policy gradient is
$\nabla_\theta J = \mathbb{E}_{a \sim \pi}[\nabla_\theta \log \pi(a \mid s) \, A(s, a)]$, and the
one-sample form used here estimates it only when the action really was drawn from $\pi$. `argmax` makes
the behaviour deterministic, so all 64 copies — same start square, same transition rule — run the very
same trajectory, and the 1280 steps of a rollout carry one trajectory's worth of information. Over the
120 iterations the
reward takes exactly two values, -0.400 on 119 of them and +1.640 once: either that single path happens
to cross the goal or no copy reaches it at all. Nothing ever tries a different move, and
$\nabla \log \pi(\arg\max)$ only sharpens the preference the network already has. Greedy selection is the
right thing when the policy is being evaluated, which is where such a line usually comes from; the
rollout that feeds the gradient has to sample.

```py
action = Categorical(logits=logits).sample()        # was logits.argmax(dim=-1)
```

**Bug 2: `advantages = values - returns` in `surrogate`.** The advantage is the return minus the
baseline. Swapped, `policy_loss` becomes $+\overline{\log \pi \cdot (G - V)}$, and descending it descends
the expected return: every step that did better than predicted is made *less* likely. Test 2 takes one
SGD step on eight copies of a step whose return, 5.0, is far above anything the untrained baseline
predicts, and the log-probability of the action taken drops from -1.671 to -15.674. In training the
agent learns to stay away from square 24: the reward never gets above the -0.272 of the first iteration
and settles on -0.400, the floor of this environment, 20 steps at -0.02 with the reward never collected. `value_loss` squares the same difference, so it never
complains.

```py
advantages = returns - values                       # was values - returns
```

**Bug 3: `for t in range(rewards.shape[0])` in `compute_returns`.** Reward-to-go obeys
$G_t = r_t + \gamma G_{t+1}$ inside an episode, so the recursion has to be unrolled from the last step
backwards; the `dones` factor is what stops it from reaching across the end of an episode. Run forwards
it computes $G_t = r_t + \gamma r_{t-1} + \gamma^2 r_{t-2} + \cdots$ instead, a discounted sum of the
rewards collected *before* step $t$. On the four-step stretch of test 3, rewards
$(-0.02, -0.02, 1, -0.02)$ with the third step terminal, the correct answer is
`[0.9015, 0.95, 1.0, -0.02]` and the loop gives `[-0.02, -0.0394, 1.0, 0.95]`: the goal reward goes to the step
*after* the goal and withheld from the steps that led to it. A step cannot have caused what happened
before it, so these scores carry no signal about the action, and the reward stays between -0.400 and
-0.209 for all 120 iterations.

```py
for t in reversed(range(rewards.shape[0])):         # was range(rewards.shape[0])
```

**Bug 4: `advantages` is not detached inside `policy_loss`.** In $\nabla \log \pi \cdot A$ the advantage
is a coefficient — a number saying how hard to push — not something to differentiate through. Left
attached it opens a second path from `policy_loss` into `value`, and the two terms settle where they
cancel. Per step, up to the $1/N$ that both means contribute, the derivative of the loss with respect to
$V$ is $\log \pi(a \mid s) + 2 \cdot 0.5 \cdot (V - G)$, which vanishes at

$$
G - V = \log \pi(a \mid s),
$$

so the baseline comes to rest one surprisal above the return it is meant to predict, and averaged over a
rollout the advantage equals minus the entropy: -0.586 against an entropy of 0.612 at iteration 119, with
`value loss` at 0.528 instead of 0.077. Training still works, because $-H(s)$ depends on the state and
not on the action, and shifting a baseline by a function of the state leaves the policy gradient
unbiased — it only adds variance, and this run does reach the optimal +1.640. What it destroys is the
value estimate itself, which is the thing a bootstrapped target or a KL penalty would be built on. The check that settles it
needs no training: `torch.autograd.grad(policy_loss, model.value.weight, allow_unused=True)[0]` has to
be `None`, and anything else means the policy term is training the baseline.

```py
policy_loss = -(dist.log_prob(actions) * advantages.detach()).mean()    # was advantages
```

### Follow-ups

- Reusing one rollout for several gradient steps breaks the estimator, because from the second step on
  the log-probabilities come from a policy that did not collect the data. PPO and GRPO repair it with
  the importance ratio $\pi_\theta(a \mid s) / \pi_{\mathrm{old}}(a \mid s)$ and clip it to
  $[1 - \epsilon, 1 + \epsilon]$, so that once an update has pushed an action past the clip in the
  direction its advantage favours, that action contributes no further gradient.
- A KL penalty against a reference policy bounds the drift of the whole distribution, which the clipped
  ratio does not: clipping only limits the actions that appear in the batch. In RLHF the reference is
  the policy before the RL stage, and the penalty is what keeps the model from collapsing onto whatever
  the reward model scores highest.
- The advantage rather than the raw return, because
  $\mathbb{E}_{a \sim \pi}[\nabla \log \pi(a \mid s) \, b(s)] = 0$ for any $b$ that does not depend on
  the action: subtracting a baseline changes no expectation, only the variance. With returns alone every
  action taken in a good state is reinforced, the bad ones included.
- GRPO removes the value network: it samples a group of $K$ answers to the same prompt and uses the
  group's own mean return as the baseline. There is then no learned estimate for bug 4 to corrupt, at
  the price of $K$ rollouts per prompt and of a baseline that only compares answers to one another.
- A rollout stops after 20 steps whether or not the episode is over, and `compute_returns` treats that
  cut like the end of an episode, so the last steps lose whatever came after it. The usual repair is to
  add $\gamma V(s)$ for the square a copy stopped in unless it had just terminated, which means keeping
  "the episode ended" and "the rollout ran out of steps" apart in the mask.

<details>
<summary>The complete file after the four fixes, and the checks (runnable)</summary>

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
