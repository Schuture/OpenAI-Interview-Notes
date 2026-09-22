# 只知道均值时的重启策略（Las Vegas）

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 口述数学题 · 概率，不写代码 | ★★★☆☆ | 困难 | RS · RE | probability, inequalities, algorithm-design | 6 个口述部分 |
<!-- meta:end -->

## 题目

一个 LLM 推理服务完成一次请求所需的时间 $T \ge 0$（单位：分钟）是随机变量。$T$ 的分布未知，只知道均值 $E[T] = 1$。

正在运行的请求可以放弃并*重启*（restart）。每次尝试的完成时间都是从同一分布中重新抽取的样本，与之前的各次尝试相互独立；
重启本身不花时间。*超时*（timeout）为 $t$ 的一次尝试最多运行 $t$ 分钟：如果它的完成时间满足 $T \le t$，这次尝试*成功*；
否则它在运行满 $t$ 分钟时被放弃。一个*方案*（schedule）是一列超时 $(t_1, \dots, t_m)$，满足 $t_1 + \dots + t_m = 10$，
10 分钟就是总的时间预算。第 $i$ 次尝试的超时为 $t_i$，在第 $i - 1$ 次尝试被放弃时开始。只要有一次尝试成功，方案就成功。

例子：方案 $(2, 3, 5)$，三次尝试抽到的完成时间依次为 2.6、3.4、4.1。

```text
第 1 次尝试：第 0 到 2 分钟     2.6 > 2，放弃
第 2 次尝试：第 2 到 5 分钟     3.4 > 3，放弃
第 3 次尝试：第 5 到 10 分钟    4.1 <= 5，在第 5 + 4.1 = 9.1 分钟成功
```

方案的*保证值*（guarantee）是满足下述条件的最大的数 $g$：对任何满足 $T \ge 0$、$E[T] = 1$ 的分布，方案成功的概率都不小于 $g$。

六个部分都要求给出推导，不需要写代码。

### Part 1 —— 尾概率的界

对所有这样的分布都成立的 $P(T > 5)$ 的最好上界是多少？是否存在使等号成立的分布？

### Part 2 —— 重启一次

求方案 $(5, 5)$ 的保证值，并与只尝试一次的方案 $(10)$ 比较。

### Part 3 —— 多次重启，预算均分

重启 $N$ 次共有 $N + 1$ 次尝试。预算平均分给各次尝试，所以每次的超时都是 $10 / (N + 1)$。对每个 $N \ge 0$ 求保证值。

### Part 4 —— 等长超时下最优的尝试次数

尝试次数 $m = N + 1$ 取多少时，Part 3 的方案保证值最大？这个保证值是多少？

### Part 5 —— 重启毫无影响的分布

这一问假设 $T$ 的分布已知。是否存在一个 $E[T] = 1$ 的分布，使得所有方案（包括只尝试一次的 $(10)$）的成功概率都相同？

### Part 6 —— 不等长的超时

分布重新变为未知，只知道 $E[T] = 1$；方案里各次尝试的超时可以不相等。是否存在保证值比 Part 4 的最优方案更大的方案？
求出两次尝试时的最优方案，再说明 $m$ 次尝试时的情况。最后说明分布已知时应当怎样选择方案。

## 参考解答

<details>
<summary>展开参考解答</summary>

先向面试官确认两点：各次尝试相互独立、重启没有开销；目标是在预算内完成的概率，而不是期望耗时。
回答里的每一个数都要说清楚它是哪一种：对所有分布成立的界、确切的最坏情况，还是某个已知分布下的精确值。

### Part 1

因为 $T \ge 0$，对任意 $a > 0$ 都有 $a \cdot \mathbf{1}[T \ge a] \le T$。两边取期望得到 Markov 不等式 $P(T \ge a) \le E[T] / a$，于是

$$P(T > 5) \le P(T \ge 5) \le \frac{1}{5}.$$

对 $P(T \ge 5)$，这个界可以取到：$T$ 以概率 $1/5$ 取 5、其余取 0，均值为 1。对 $P(T > 5)$ 则取不到，因为 $P(T > 5) = 1/5$ 会导致
$E[T] \ge E\bigl[T \cdot \mathbf{1}[T > 5]\bigr] > 5 \cdot \frac{1}{5} = 1$。但可以任意逼近：$T$ 以概率 $1/(5 + \varepsilon)$ 取
$5 + \varepsilon$、其余取 0，均值为 1，而 $P(T > 5) = 1/(5 + \varepsilon) \to 1/5$。所以 $1/5$ 是最好的界，它是上确界而不是最大值。
同理，*生存函数*（survival function）$S(t) = P(T > t)$ 对任意 $t \ge 1$ 满足 $\sup S(t) = 1/t$，
把 $1/t$ 的质量放在略大于 $t$ 的位置就能逼近它。

### Part 2

两次尝试相互独立，所以方案失败的概率是 $S(5)^2 \le 1/25$。两次尝试的超时相同，Part 1 的分布能让两个因子同时逼近 $1/5$，
因此保证值恰好是 $1 - 1/25 = 0.96$。只尝试一次的方案 $(10)$ 是 $1 - 1/10 = 0.9$。

### Part 3

共 $m = N + 1$ 次尝试，超时 $t = 10/m$，方案失败的概率是 $S(t)^m$；$S$ 已知时这就是精确答案。只知道均值时，由 Part 1，
$m \le 10$ 时 $S(t) \le 1/t = m/10$，而略大于 $t$ 处的质量同样能让 $m$ 个因子同时逼近这个界：

$$\text{保证值} = 1 - \left(\frac{m}{10}\right)^{m} = 1 - \left(\frac{N+1}{10}\right)^{N+1}, \qquad N + 1 \le 10.$$

$N + 1 \ge 10$ 时超时不超过 1，保证值为 0。耗时恒为 $T = 1$ 的请求永远无法在小于 1 的超时内完成；超时恰为 1 时，
取 $T$ 以概率 $1/(1 + \varepsilon)$ 等于 $1 + \varepsilon$、其余为 0，失败概率为 $(1 + \varepsilon)^{-10} \to 1$。

### Part 4

要使失败概率 $(m/10)^m$ 最小，取对数 $f(m) = m \ln(m/10)$，先对实数 $m$ 求极小：

$$f'(m) = \ln\frac{m}{10} + 1 = 0 \quad\Longrightarrow\quad m = \frac{10}{e} \approx 3.68 .$$

$f''(m) = 1/m > 0$，$f$ 是凸函数，所以最优的整数是 3 或 4。$0.3^3 = 0.027$，$0.4^4 = 0.0256$，因此最优方案是 4 次尝试、每次 2.5 分钟，
保证值为 $1 - 0.0256 = 0.9744$。作为对照，$m = 2$ 时是 $0.96$，$m = 5$ 时是 $0.9688$。由 Part 3，这些数是各方案确切的最坏情况，
而不只是一个界。其中的权衡是：多一次尝试，乘积里就多一个因子，但每个因子 $m/10$ 都更接近 1。实数最优解对应的超时是 $10/m = e$，
与预算无关，所以在这个标准下，一次尝试运行到均值的 $e \approx 2.7$ 倍左右就该放弃。

### Part 5

存在：速率为 1 的指数分布，$S(t) = e^{-t}$，均值为 1。任何方案的失败概率都是

$$\prod_{i=1}^{m} S(t_i) = e^{-(t_1 + \dots + t_m)} = e^{-10} \approx 4.5 \times 10^{-5}.$$

这就是*无记忆性*（memoryless property）$P(T > s + t \mid T > s) = P(T > t)$：一次已经运行了 $s$ 分钟的尝试，与一次全新的尝试完全等价。
反过来，如果所有方案的失败概率都相同，那么只要 $s + t \le 10$ 就有 $S(s + t) = S(s) S(t)$，它的单调不增的解只有
$S(t) = e^{-\lambda t}$，所以在预算范围内分布必须是指数形式。

### Part 6

答案取决于用什么标准评价一个方案。

**按 Markov 界的乘积。** 对每个因子分别取界：当所有 $t_i \ge 1$ 时 $\prod_i S(t_i) \le 1/(t_1 \cdots t_m)$（小于 1 的超时只贡献因子 1）；
由均值不等式（AM–GM），和固定时各因子相等乘积最大。按这个界来评价，不等长的超时永远没有好处，Part 4 就是最终答案：$(2.5, 7.5)$ 的界是
$1/(2.5 \cdot 7.5) \approx 0.053$，比 $(5, 5)$ 的 $0.04$ 还差。

**按真正的最坏情况。** 超时不相等时，乘积界并不是保证值。要让因子 $S(t_i)$ 逼近 $1/t_i$，必须把 $1/t_i$ 的质量放在略大于 $t_i$ 的位置，
这已经把均值全部用完。各次尝试服从的是同一个分布，而一个分布无法在两个不同的超时上同时做到这一点。
下面把这个分布看作由一个知道方案的*对手*（adversary）来选。

*两次尝试。* 设超时为 $a \le b$，$a + b = 10$，记 $s_1 = S(a)$、$s_2 = S(b)$，于是 $s_1 \ge s_2$。
由 $E[T] = \int_0^\infty S(t)\;dt$ 以及 $S$ 单调不增，

$$1 = E[T] \ge \int_0^a S(t)\;dt + \int_a^b S(t)\;dt \ge a s_1 + (b - a) s_2 .$$

反过来，任何满足这个不等式的 $1 \ge s_1 \ge s_2 \ge 0$ 都能被均值为 1 的分布逼近：在略大于 $b$ 处放质量 $s_2$，
在略大于 $a$ 处放质量 $s_1 - s_2$，其余放在 0（均值不足 1 时，把任意小的一点质量移到很远处补足）。
所以对手要做的是在这些约束下最大化 $s_1 s_2$。由 AM–GM，

$$a s_1 \cdot (b - a) s_2 \le \left(\frac{a s_1 + (b - a) s_2}{2}\right)^{2} \le \frac{1}{4}, \qquad\text{所以}\qquad s_1 s_2 \le \frac{1}{4a(b - a)} = \frac{1}{4a(10 - 2a)},$$

等号在 $s_1 = 1/(2a)$、$s_2 = 1/(2(10 - 2a))$ 时成立。这一对值满足 $s_2 \le s_1 \le 1$ 当且仅当 $1/2 \le a \le 10/3$，
此时最坏情况的失败概率就是 $1/(4a(10 - 2a))$。它在 $a(10 - 2a)$ 最大处最小，即 $a = 2.5$：

$$\text{方案 } (2.5,\; 7.5), \qquad \text{最坏情况的失败概率 } \frac{1}{4 \cdot 2.5 \cdot 5} = \frac{1}{50}, \qquad \text{保证值 } 0.98 .$$

在这个范围之外有一条约束起作用：$a > 10/3$ 时最大值在 $s_1 = s_2 = 1/b$ 处，失败概率为 $1/(10 - a)^2 > 9/400$；
$a < 1/2$ 时最大值在 $s_1 = 1$ 处，失败概率为 $(1 - a)/(10 - 2a) > 1/18$。两者都大于 $1/50$，所以 $(2.5, 7.5)$ 是两次尝试时的最优方案。
它的保证值 $0.98$ 高于 $(5, 5)$ 的 $0.96$，也高于四次等长尝试的 $0.9744$。对手用来对付它的分布是：略大于 $2.5$ 处质量 $0.1$，
略大于 $7.5$ 处质量 $0.1$，0 处质量 $0.8$。

*一般的 $m$ 次尝试。* 把超时排序，$t_1 \le \dots \le t_m$，记 $d_i = t_i - t_{i-1}$（$t_0 = 0$）、$s_i = S(t_i)$。同样的积分论证给出：
任何分布都满足 $\sum_i d_i s_i \le 1$；预算约束则可以写成 $\sum_i (m - i + 1) d_i = \sum_i t_i = 10$。$m \le 10$ 的情形由下面两点完全确定：

- 取间隔 $d_i = \frac{10}{m (m - i + 1)}$。对 $d_i s_i$ 这 $m$ 项用 AM–GM 得 $\prod_i d_i s_i \le m^{-m}$，
  所以对任何分布都有 $\prod_i s_i \le 1 / (m^m \prod_i d_i) = m!/10^m$。
- 无论方案是什么，对手都可以在略大于每个超时的位置各放 $1/10$ 的质量，其余放在 0。此时均值为 $\sum_i t_i / 10 = 1$，
  且 $S(t_i) \ge (m - i + 1)/10$，所以失败概率可以逼近一个不小于 $m!/10^m$ 的值。

因此 $m \le 10$ 次尝试时最好的保证值恰好是 $1 - m!/10^m$：$m = 2$ 时为 $0.98$；$m = 3$ 时为 $0.994$，超时为
$(10/9,\; 25/9,\; 55/9) \approx (1.11,\; 2.78,\; 6.11)$；$m = 4$ 时为 $0.9976$。每多一次尝试，失败概率就乘上 $(m + 1)/10$，
所以它一直下降到 $m = 9$，此时 $9!/10^9 = 10!/10^{10} \approx 3.6 \times 10^{-4}$。尝试超过 10 次时，对手对最大的 10 个超时照此办理，
所以无论多长的方案，保证值都不会超过 $1 - 9!/10^9 \approx 0.9996$。

*分布已知时。* 失败概率 $\prod_i S(t_i)$ 是精确值，起决定作用的是*风险率*（hazard rate）$h(t) = f(t)/S(t)$，其中 $f$ 是 $T$ 的密度。
由 $\ln S(t) = -\int_0^t h(u)\;du$，$h$ 递减时 $S(s + t) \ge S(s) S(t)$，所以把一次尝试拆成两次会降低失败概率；
$h$ 递增时不等号反向，只尝试一次的 $(10)$ 最好；$h$ 为常数就是 Part 5 的指数分布。

### 追问

- 分布已知，目标改为成功之前的期望总耗时（没有预算）：固定截断 $\tau$ 时 $E = E[\min(T, \tau)] + S(\tau) E$，即
  $E = E[\min(T, \tau)] / P(T \le \tau)$。最优策略是每次尝试都用使这个比值最小的截断 $\tau^{\ast}$（Luby、Sinclair 与 Zuckerman）。
- 目标相同但分布未知：依次用 Luby 通用序列 $1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8, \dots$ 作为截断，期望耗时为
  $O(T_{\mathrm{opt}} \log T_{\mathrm{opt}})$，其中 $T_{\mathrm{opt}}$ 是使用 $\tau^{\ast}$ 时的期望耗时。任何不依赖分布的策略至多比它好一个常数因子。
- 如果还知道方差 $\sigma^2$，可以用 Cantelli 不等式 $P(T \ge 1 + \lambda) \le \sigma^2 / (\sigma^2 + \lambda^2)$ 代替 Markov 不等式。
  $\sigma = 1$ 时得到 $P(T \ge 5) \le 1/17$，等号在 $T$ 以概率 $1/17$ 取 5、其余取 $0.75$ 时成立。
- 如果每次重启要花 $c$ 分钟，$m$ 次尝试留给各个超时的时间是 $10 - (m - 1)c$ 分钟，所有公式里的 10 都换成这个数。
  $c = 0.5$ 时，最优的尝试次数在等长超时下从 4 降到 3，在不等长超时下从 9 降到 5。
- 真实的服务里各次尝试并不独立：因为请求本身很长、或者因为某个副本负载高而变慢的请求，重启之后仍然慢。
  常用的办法是对冲请求（hedged request）：延迟一段时间后向另一个副本再发一份，谁先返回就用谁的结果。

<details>
<summary>验证代码（可运行）</summary>

```python
import itertools
import math

import numpy as np
from scipy.optimize import minimize
from scipy.stats import expon, weibull_min

BUDGET = 10.0
rng = np.random.default_rng(0)


class Discrete:
    """A distribution on finitely many points, evaluated exactly."""

    def __init__(self, values, probs):
        self.values, self.probs = np.asarray(values, dtype=float), np.asarray(probs, dtype=float)
        assert np.all(self.values >= 0) and np.all(self.probs >= 0) and math.isclose(self.probs.sum(), 1.0)

    def mean(self):
        return float(self.values @ self.probs)

    def sf(self, t):                                    # NOTE: strict, P(T > t): an attempt with T == t succeeds
        return float(self.probs[self.values > t].sum())


def failure_probability(sf, timeouts):
    """P(every attempt is abandoned) for independent attempts; sf(t) = P(T > t)."""
    return math.prod(sf(t) for t in timeouts)


def atoms_above(timeouts, masses, eps):
    """Mass masses[i] / (1 + eps) at timeouts[i] * (1 + eps), the rest at 0: the mean does not depend on eps."""
    masses = np.asarray(masses, dtype=float) / (1 + eps)
    return Discrete(np.append(np.asarray(timeouts) * (1 + eps), 0.0), np.append(masses, 1.0 - masses.sum()))


# ---- Part 1: Markov's bound is attained for P(T >= 5), and only approached for P(T > 5)
two_point = Discrete([0.0, 5.0], [0.8, 0.2])
assert math.isclose(two_point.mean(), 1.0)
assert math.isclose(two_point.probs[two_point.values >= 5].sum(), 0.2) and two_point.sf(5) == 0.0
for eps in (1e-2, 1e-4, 1e-6):
    dist = atoms_above([5.0], [1 / 5], eps)
    assert math.isclose(dist.mean(), 1.0) and 0.2 / (1 + eps) <= dist.sf(5) < 0.2

# ---- Parts 2-4: equal timeouts; the two-point distribution approaches the product of Markov bounds
equal_bound = {m: (m / BUDGET) ** m for m in range(1, 11)}
assert math.isclose(1 - equal_bound[2], 24 / 25)
assert min(equal_bound, key=equal_bound.get) == 4 and math.isclose(1 - equal_bound[4], 0.9744)
assert 3 < BUDGET / math.e < 4 and equal_bound[3] > equal_bound[4] < equal_bound[5]
for m in range(1, 11):
    t = BUDGET / m
    dist = atoms_above([t], [1 / t], 1e-9)
    assert math.isclose(dist.mean(), 1.0)
    assert math.isclose(failure_probability(dist.sf, [t] * m), equal_bound[m], rel_tol=1e-7)
assert failure_probability(Discrete([1.0], [1.0]).sf, [BUDGET / 11] * 11) == 1.0   # timeout < 1: T = 1 always fails

# ---- Part 5: for the exponential distribution every schedule fails with probability e^-10
for m in (1, 2, 5, 40):
    schedule = rng.dirichlet(np.ones(m)) * BUDGET
    assert math.isclose(failure_probability(expon.sf, schedule), math.exp(-BUDGET), rel_tol=1e-9)


def simulate_failure(sample, timeouts, runs=400_000):
    """Monte Carlo version of failure_probability; sample(shape) draws independent completion times."""
    draws = sample((runs, len(timeouts)))
    return float(np.mean(np.all(draws > np.asarray(timeouts), axis=1)))


for schedule in ([3.0], [1.0, 2.0], [0.5, 0.5, 2.0]):       # a budget of 3, so that e^-3 is visible in a simulation
    assert abs(simulate_failure(lambda shape: rng.exponential(size=shape), schedule) - math.exp(-3)) < 1.5e-3


# ---- Part 6: the adversary's problem, solved numerically
def worst_case_failure(timeouts):
    """sup of prod_i S(t_i) over all distributions with T >= 0 and E[T] = 1. With s_i = S(t_i) for the
    sorted timeouts and the gaps d_i = t_i - t_(i-1): maximise sum_i log s_i (concave) subject to
    sum_i d_i s_i <= 1 and 1 >= s_1 >= ... >= s_m (linear)."""
    t = np.sort(np.asarray(timeouts, dtype=float))
    d = np.diff(t, prepend=0.0)
    m = len(t)
    order = np.eye(m)[:-1] - np.eye(m)[1:]              # row i: s_i - s_(i+1) >= 0
    constraints = [{"type": "ineq", "fun": lambda s: 1.0 - d @ s, "jac": lambda s: -d},
                   {"type": "ineq", "fun": lambda s: order @ s, "jac": lambda s: order}]
    start = np.full(m, min(1.0, 0.5 / t[-1]))           # feasible: 0.5 * sum(d) / t_m = 0.5
    result = minimize(lambda s: -np.log(s).sum(), start, jac=lambda s: -1.0 / s, method="SLSQP",
                      bounds=[(1e-9, 1.0)] * m, constraints=constraints, options={"ftol": 1e-12, "maxiter": 1000})
    return math.exp(-result.fun), result.x


def best_schedule(m):
    gaps = [BUDGET / (m * (m - i)) for i in range(m)]   # d_i = 10 / (m (m - i + 1)) for i = 1..m
    return np.cumsum(gaps)


# m = 2: the solver reproduces the piecewise closed form of the worst case of (a, 10 - a)
for a in np.arange(0.05, 5.0001, 0.05):
    if a < 0.5:
        closed_form = (1 - a) / (BUDGET - 2 * a)
    elif a <= BUDGET / 3:
        closed_form = 1 / (4 * a * (BUDGET - 2 * a))
    else:
        closed_form = 1 / (BUDGET - a) ** 2
    assert math.isclose(worst_case_failure([a, BUDGET - a])[0], closed_form, rel_tol=1e-6)


def minimax(m, step):
    """Designer: grid search over schedules with m attempts, then Nelder-Mead from the best grid point."""
    n = round(BUDGET / step)
    grid = [np.diff((0,) + cuts + (n,)) * step for cuts in itertools.combinations(range(1, n), m - 1)]
    grid = [t for t in grid if np.all(np.diff(t) >= 0)]                        # sorted schedules only
    start = min(grid, key=lambda t: worst_case_failure(t)[0])

    def objective(z):                                   # z = log-weights, so every schedule sums to the budget
        w = np.exp(z - z.max())
        return worst_case_failure(w / w.sum() * BUDGET)[0]

    result = minimize(objective, np.log(start), method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-13})
    w = np.exp(result.x - result.x.max())
    return result.fun, np.sort(w / w.sum() * BUDGET)


for m, step in ((2, 0.1), (3, 0.5)):
    value, schedule = minimax(m, step)
    assert math.isclose(value, math.factorial(m) / BUDGET ** m, rel_tol=1e-5)
    assert np.allclose(schedule, best_schedule(m), atol=2e-3)
assert np.allclose(best_schedule(2), [2.5, 7.5]) and np.allclose(best_schedule(3), [10 / 9, 25 / 9, 55 / 9])

# the closed-form schedule attains m! / 10^m, and the solver's s_i are (m - i + 1) / 10
for m in range(1, 11):
    value, s = worst_case_failure(best_schedule(m))
    assert math.isclose(value, math.factorial(m) / BUDGET ** m, rel_tol=1e-6)
    assert np.allclose(s, np.arange(m, 0, -1) / BUDGET, atol=1e-4)
assert math.isclose(math.factorial(9) / 1e9, math.factorial(10) / 1e10) and round(math.factorial(9) / 1e9, 6) == 0.000363

# no schedule beats it: mass 1/10 just above each of the (at most 10) largest timeouts has mean <= 1
for _ in range(200):
    m = int(rng.integers(1, 15))
    schedule = np.sort(rng.dirichlet(np.ones(m)) * BUDGET)
    k = min(m, 10)
    dist = atoms_above(schedule[-k:], [1 / BUDGET] * k, 1e-9)
    assert dist.mean() <= 1 + 1e-12
    floor = math.factorial(k) / BUDGET ** k
    assert failure_probability(dist.sf, schedule) >= floor * (1 - 1e-7)
    assert worst_case_failure(schedule)[0] >= floor * (1 - 1e-6)

# every distribution obeys sum_i d_i S(t_i) <= E[T], the one inequality behind the adversary's problem
for _ in range(2000):
    size = int(rng.integers(1, 7))
    dist = Discrete(rng.uniform(0, 12, size), rng.dirichlet(np.ones(size)))
    schedule = np.sort(rng.dirichlet(np.ones(3)) * BUDGET)
    gaps = np.diff(schedule, prepend=0.0)
    assert gaps @ [dist.sf(t) for t in schedule] <= dist.mean() + 1e-12

# (2.5, 7.5) against its own worst case, exactly and by simulation, and against the worst case of (5, 5)
dist = atoms_above([2.5, 7.5], [0.1, 0.1], 1e-9)
assert math.isclose(dist.mean(), 1.0)
assert math.isclose(failure_probability(dist.sf, [2.5, 7.5]), 0.02, rel_tol=1e-7)
assert math.isclose(failure_probability(dist.sf, [5.0, 5.0]), 0.01, rel_tol=1e-7)
assert abs(simulate_failure(lambda shape: rng.choice(dist.values, shape, p=dist.probs), [2.5, 7.5]) - 0.02) < 1e-3
assert failure_probability(atoms_above([5.0], [0.2], 1e-9).sf, [2.5, 7.5]) == 0.0

# known distribution: a decreasing hazard rate favours splitting, an increasing one favours a single attempt
for shape, splitting_helps in ((0.5, True), (2.0, False)):
    sf = weibull_min(shape, scale=1 / math.gamma(1 + 1 / shape)).sf                # scaled to mean 1
    assert (failure_probability(sf, [5.0, 5.0]) < failure_probability(sf, [10.0])) == splitting_helps


# ---- Follow-ups
def expected_time_with_cutoff(dist, cutoff):
    return float(np.minimum(dist.values, cutoff) @ dist.probs) / (1.0 - dist.sf(cutoff))


bimodal = Discrete([0.5, 5.5], [0.9, 0.1])                                         # mean 1
assert math.isclose(expected_time_with_cutoff(bimodal, 0.5), 0.5 / 0.9)
assert math.isclose(expected_time_with_cutoff(bimodal, 5.5), 1.0)
total = np.zeros(200_000)
running = np.ones(total.shape, dtype=bool)
while running.any():                                                               # simulate the cutoff 0.5
    draws = rng.choice(bimodal.values, int(running.sum()), p=bimodal.probs)
    total[running] += np.minimum(draws, 0.5)
    running[running] = draws > 0.5
assert abs(total.mean() - 0.5 / 0.9) < 2e-3


def luby(i):
    """i-th term (i >= 1) of Luby's universal sequence."""
    k = i.bit_length()
    return 1 << (k - 1) if i == (1 << k) - 1 else luby(i - (1 << (k - 1)) + 1)


assert [luby(i) for i in range(1, 16)] == [1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8]

cantelli = Discrete([0.75, 5.0], [16 / 17, 1 / 17])                                # mean 1, variance 1
variance = float((cantelli.values - 1.0) ** 2 @ cantelli.probs)
assert math.isclose(cantelli.mean(), 1.0) and math.isclose(variance, 1.0)
assert math.isclose(cantelli.probs[cantelli.values >= 5].sum(), 1 / (1 + 4 ** 2))

for overhead, best_equal, best_unequal in ((0.0, 4, 9), (0.5, 3, 5), (1.0, 2, 4)):   # each restart costs `overhead` minutes
    left = {m: BUDGET - (m - 1) * overhead for m in range(1, 11)}
    left = {m: b for m, b in left.items() if b >= m}
    assert min(left, key=lambda m: (m / left[m]) ** m) == best_equal
    assert min(left, key=lambda m: math.factorial(m) / left[m] ** m) == best_unequal
```

</details>

</details>
