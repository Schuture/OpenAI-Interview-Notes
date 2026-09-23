# 灯塔光束与重尾分布

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| 题型 | 优先级 | 难度 | 岗位 | 考点 | 形式 |
| --- | --- | --- | --- | --- | --- |
| 口述数学题 · 概率 | ★☆☆☆☆ | 困难 | RS · RE | probability, heavy-tails, simulation, estimation | 4 个部分 |
<!-- meta:end -->

## 题目

一座灯塔立在海里，到一条笔直长岸线的垂直距离为 $d > 0$。在岸线上取一个坐标，记 $x_0$ 为岸上离灯塔最近那一点的坐标。
灯塔射出一束细光，光束方向用它与“灯塔到岸线的垂线”之间的夹角 $\Theta$ 来描述，$\Theta$ 在 $(-\pi/2,\; \pi/2)$ 上均匀分布，
因此光束总能打到岸上。岸上的探测器记录光束落点的坐标 $X$。各次闪光相互独立，每次的 $d$ 和 $x_0$ 都相同。

取 $d = 2$、$x_0 = -3$（单位：公里）的例子：

```text
theta =  0       光束垂直射向岸线     x = -3 + 2 *  0.00  =  -3.00
theta =  pi/4    tan(theta) =  1.00   x = -3 + 2 *  1.00  =  -1.00
theta = -1.45    tan(theta) = -8.24   x = -3 + 2 * -8.24  = -19.48
theta =  1.52    tan(theta) = 19.67   x = -3 + 2 * 19.67  =  36.34
```

四个部分都只要求推导，不需要写代码。

### Part 1 —— 一次闪光落在哪里

推导 $X$ 的分布函数 $F(x) = P(X \le x)$ 与密度 $f$。把 $X$ 写成 $x_0 + dZ$，其中 $Z$ 的分布与 $x_0$、$d$ 都无关；
给出 $Z$ 的密度，并说出这个分布族的名字。$X$ 的中位数和四分位数在哪里，$F$ 的尾部衰减有多快？

### Part 2 —— 对多次闪光取平均

$E[X]$ 存在吗？再设 $X_1, \dots, X_n$ 是 $n$ 次闪光的落点，对每个 $n$ 求样本均值 $\bar X_n = \frac1n \sum_{i=1}^{n} X_i$
的精确分布。这个结果对“用 $\bar X_n$ 定位灯塔”意味着什么？平时那套“取平均把误差缩小到 $1/\sqrt n$”的论证，是在哪一步失效的？

### Part 3 —— 真正会收敛的估计量

这一部分里 $d$ 已知、$x_0$ 未知，可用的数据只有记录下来的 $n$ 个落点，角度观测不到。如果一列估计量
$T_n = T_n(X_1, \dots, X_n)$ 依概率收敛到 $x_0$，就称它*相合*（consistent）；如果
$\sqrt n\;(T_n - x_0)$ 依分布收敛到 $N(0,\; v)$，就称它的*渐近方差*（asymptotic variance）是 $v$；
在相合的估计量之间，$v$ 越小越好。评价的基准是 $\theta = x_0$ 处的 *Fisher 信息*（Fisher information）
$I = E\bigl[(\partial_\theta \ln f(X; \theta))^{2}\bigr]$，其中 $f(\cdot\;; \theta)$ 就是 Part 1 的密度、把 $x_0$ 换成
$\theta$；渐近方差达到 $v = 1/I$ 的估计量称为*有效的*（efficient）。

给出 $x_0$ 的两个相合估计量，分别证明它们的相合性，算出 $I$ 和各自的渐近方差，并说明哪一个是有效的、另一个差多少。

### Part 4 —— 模拟要验证出什么

假设现在用数值模拟来检验上面三个结论：抽角度，算落点。对其中每一个结论——$X$ 的分布、$\bar X_n$ 的分布、Part 3 的估计量的
收敛速度——说出你会测量哪个量，以及推导为这个量预言了什么数值。在 $R$ 次重复上算均方误差
$\frac1R \sum_{r=1}^{R} (T^{(r)} - x_0)^{2}$ 在这里是个糟糕的工具，说明为什么，并给出一个行得通的误差度量。

## 参考解答

<details>
<summary>展开参考解答</summary>

先向面试官确认两件事：均匀的是光束的*角度*，不是落点；Part 3 里未知的只有 $x_0$。
每个数都要说清是精确值、渐近极限还是模拟估计。

### Part 1

把岸线放在横轴上，灯塔在点 $x_0$ 正上方高度 $d$ 处。以角度 $\Theta$ 射出的光束竖直走 $d$、水平走 $d \tan\Theta$
后落到岸上，所以 $X = x_0 + d \tan\Theta$。正切函数在 $(-\pi/2,\; \pi/2)$ 上是到整条实轴的严格增双射，
而均匀分布的 $\Theta$ 满足 $P(\Theta \le a) = (a + \pi/2)/\pi$，于是

$$F(x) = P\left(\Theta \le \arctan\frac{x - x_0}{d}\right) = \frac{1}{2} + \frac{1}{\pi}\arctan\frac{x - x_0}{d}, \qquad f(x) = F'(x) = \frac{d}{\pi\left(d^{2} + (x - x_0)^{2}\right)} .$$

记 $Z = \tan\Theta$，上式就是 $X = x_0 + dZ$，而 $Z$ 的密度为 $1/(\pi(1 + z^{2}))$，即*标准柯西分布*（standard Cauchy
distribution），于是 $X \sim \mathrm{Cauchy}(x_0,\; d)$。$F$ 关于 $x_0$ 对称且
$F(x_0) = 1/2$，所以中位数是 $x_0$；又 $F(x_0 \pm d) = \frac12 \pm \frac{\arctan 1}{\pi} = \frac12 \pm \frac14$，
所以四分位数是 $x_0 - d$ 和 $x_0 + d$。但尾部很重：$x \to \infty$ 时
$1 - F(x) = \frac{1}{\pi}\arctan\frac{d}{x - x_0} \sim \frac{d}{\pi (x - x_0)}$，是 $1/x$ 的量级，
而不是正态分布的 $e^{-x^{2}/2}$：与岸线只差 $\varepsilon$ 就擦过去的光束概率只有 $2\varepsilon/\pi$，
落点却在 $d \cot\varepsilon \approx d/\varepsilon$ 以外。

### Part 2

**期望不存在。** 令 $z = x - x_0$，

$$E\bigl\lvert X - x_0 \bigr\rvert = \frac{d}{\pi}\int_{-\infty}^{\infty} \frac{\lvert z \rvert}{d^{2} + z^{2}}\;dz = \frac{2d}{\pi}\int_{0}^{\infty} \frac{z}{d^{2} + z^{2}}\;dz = \frac{d}{\pi}\Bigl[\ln (d^{2} + z^{2})\Bigr]_{0}^{\infty} = \infty .$$

正部与负部都发散，所以 $E[X]$ 不是 $\pm\infty$ 而是没有定义；对称性也救不了它：在 $x_0 - M$ 与 $x_0 + cM$ 处截断，
极限是 $x_0 + \frac{d}{\pi}\ln c$，取决于两侧尾巴各截到哪里。

**样本均值的分布。** 标准柯西变量 $Z$ 的*特征函数*（characteristic function）是
$\varphi_Z(t) = E\bigl[e^{itZ}\bigr] = e^{-\lvert t \rvert}$。从拉普拉斯密度 $g(x) = \frac12 e^{-\lvert x \rvert}$ 出发，
它的变换是初等的：$\int e^{isx} g(x)\;dx = \frac{1}{2}\bigl(\frac{1}{1 - is} + \frac{1}{1 + is}\bigr) = \frac{1}{1 + s^{2}}$。
它对 $s$ 可积，所以傅里叶反演成立：$\frac12 e^{-\lvert x \rvert} = \frac{1}{2\pi}\int e^{-isx}(1 + s^{2})^{-1}\;ds$；
取 $x = -t$ 再乘以 2，得到的正是要求的那个积分：

$$e^{-\lvert t \rvert} = \int_{-\infty}^{\infty} e^{ist}\;\frac{ds}{\pi (1 + s^{2})} = \varphi_Z(t).$$

由此 $\varphi_X(t) = e^{itx_0}\varphi_Z(dt) = \exp\bigl(itx_0 - d\lvert t \rvert\bigr)$，各次闪光独立，于是
$\varphi_{\bar X_n}(t) = \varphi_X(t/n)^{n} = \exp\bigl(itx_0 - d\lvert t \rvert\bigr) = \varphi_X(t)$。
特征函数唯一确定分布，因此对每个 $n$ 都有

$$\bar X_n \sim \mathrm{Cauchy}(x_0,\; d), \qquad P\bigl(\lvert \bar X_n - x_0 \rvert > 10 d\bigr) = 1 - \frac{2}{\pi}\arctan 10 \approx 6.3\% .$$

一百万次闪光的平均值，分布与一次闪光完全相同；$\bar X_n$ 不相合，给它配 $\sigma/\sqrt n$ 的误差棒没有意义。

失效的是第一步：$\mathrm{Var}(\bar X_n) = \sigma^{2}/n$ 和大数定律都要求 $E\lvert X \rvert$ 有限。
取而代之的图景是 $P(\lvert X - x_0 \rvert > nd) \approx \frac{2}{\pi n}$：不管 $n$ 多大，落在离 $x_0$ 超过 $nd$
处的闪光期望都有 $2/\pi$ 次左右，其中一次就能把 $\bar X_n$ 挪动 $d$ 的量级。柯西分布是指标为 1 的对称*稳定分布*
（stable law），指标 1 正是取平均既不集中也不发散的那个分界点。

### Part 3

下面两个估计量都是在解形如 $\sum_i \psi\bigl((X_i - \theta)/d\bigr) = 0$ 的方程，关键全在 $\psi$ 增长得有多快。
样本均值对应 $\psi(r) = r$：落在 $1000\;d$ 处的闪光，权重是落在 $d$ 处那次的一千倍，这就是 Part 2。

**样本中位数** $\hat m_n = X_{(\lceil n/2 \rceil)}$ 对应 $\psi(r) = \mathrm{sign}(r)$。

*相合性。* 固定 $\varepsilon > 0$，令 $\delta = \frac{1}{\pi}\arctan\frac{\varepsilon}{d} > 0$，于是
$p = 1 - F(x_0 + \varepsilon) = \frac12 - \delta$。若 $\hat m_n \ge x_0 + \varepsilon$，则至少一半的闪光落在
$x_0 + \varepsilon$ 或更远处，由 Hoeffding 不等式，
$P(\hat m_n \ge x_0 + \varepsilon) \le P\bigl(\mathrm{Bin}(n,\; p) \ge n/2\bigr) \le e^{-2n\delta^{2}}$，另一侧同理。
这个界对 $n$ 可求和，由 Borel–Cantelli 引理得 $\hat m_n \to x_0$ 几乎必然成立；整个推导只用到 $F$，不需要矩。

*渐近方差。* 记 $B_n$ 为满足 $X_i \le x_0 + u/\sqrt n$ 的闪光个数，则 $B_n \sim \mathrm{Bin}(n,\; q_n)$，其中
$q_n = F(x_0 + u/\sqrt n) = \frac12 + \frac{f(x_0) u}{\sqrt n} + o(n^{-1/2})$。此时 $\sqrt n (\hat m_n - x_0) > u$
当且仅当 $B_n < \lceil n/2 \rceil$，而 $q_n(1 - q_n) \to \frac14$，由二项分布的中心极限定理，

$$P\bigl(\sqrt n (\hat m_n - x_0) > u\bigr) = P\left(\frac{B_n - n q_n}{\sqrt{n q_n (1 - q_n)}} < -2 f(x_0) u + o(1)\right) \longrightarrow \Phi\bigl(-2 f(x_0) u\bigr),$$

即 $\sqrt n (\hat m_n - x_0) \Rightarrow N\bigl(0,\; 1/(4 f(x_0)^{2})\bigr)$。代入 $f(x_0) = 1/(\pi d)$ 得
$v_{\mathrm{med}} = \pi^{2} d^{2}/4$，$\sqrt{v_{\mathrm{med}}/n} = \pi d/(2\sqrt n) \approx 1.57\;d/\sqrt n$。

**最大似然估计** $\hat\theta_n$ 使下式取最大：

$$\ell(\theta) = -\sum_{i=1}^{n} \ln\left(d^{2} + (X_i - \theta)^{2}\right) + \text{常数}, \qquad \ell'(\theta) = \frac{1}{d}\sum_{i=1}^{n} \psi\left(\frac{X_i - \theta}{d}\right), \quad \psi(r) = \frac{2r}{1 + r^{2}} .$$

这里的 $\psi$ 不只是有界，还是*重下降*（redescending）的：$\lvert r \rvert \to \infty$ 时 $\psi(r) \to 0$，
所以 100 公里外的闪光，拉力比 2 公里外的还小。这不是临时加的稳健化手段，而是柯西尾部决定的最优做法。

*相合性。* 对数似然比 $\ln\frac{d^{2} + (X - \theta)^{2}}{d^{2} + (X - x_0)^{2}}$ 对固定的 $\theta$ 是 $X$ 的有界函数，
作为 $\theta$ 的函数又对任何样本都是 $1/d$-Lipschitz 的，所以大数定律不需要任何矩，且在紧集上一致收敛：

$$\frac{1}{n}\bigl[\ell(\theta) - \ell(x_0)\bigr] \longrightarrow -K(\theta) = -\ln\left(1 + \frac{(\theta - x_0)^{2}}{4 d^{2}}\right) \quad \text{几乎必然},$$

其中 $K$ 是两个分布之间的 Kullback–Leibler 散度，除 $\theta = x_0$ 外恒正。远处不需要一致性：若 $\theta > \hat m_n$，
则至少一半的闪光离 $\theta$ 有 $\theta - \hat m_n$ 那么远，于是
$\frac1n \ell(\theta) \le -\frac12 \ln\bigl(d^{2} + (\theta - \hat m_n)^{2}\bigr) - \ln d$，而
$\frac1n \ell(x_0) \to -\ln (4d^{2})$（因为 $E \ln(1 + Z^{2}) = 2 \ln 2$ 有限），所以 $x_0 \pm 8d$ 之外的
$\theta$ 最终都被 $x_0$ 比下去。于是 $\hat\theta_n \to x_0$ 几乎必然成立。

*渐近方差。* 把得分函数在 $x_0$ 处展开：$0 = \ell'(\hat\theta_n) = \ell'(x_0) + \ell''(x_0)(\hat\theta_n - x_0) + \dots$。
$\ell'(x_0)$ 的各项有界，所以尽管 $X$ 一个矩都没有，普通的中心极限定理照样适用；由对称性各项均值为零，方差就是 Fisher 信息

$$I = \mathrm{Var}\left(\frac{\psi(Z)}{d}\right) = \frac{4}{\pi d^{2}}\int_{-\infty}^{\infty} \frac{z^{2}}{(1 + z^{2})^{3}}\;dz = \frac{4}{\pi d^{2}} \cdot \frac{\pi}{8} = \frac{1}{2 d^{2}} ,$$

同样地 $-\frac1n \ell''(x_0) \to I$。于是 $\sqrt n (\hat\theta_n - x_0) \Rightarrow N(0,\; 1/I)$，
$v_{\mathrm{mle}} = 2 d^{2}$，$\sqrt{v_{\mathrm{mle}}/n} = \sqrt 2\;d/\sqrt n$：它达到了 $1/I$，是有效的。
中位数的效率是 $v_{\mathrm{mle}} / v_{\mathrm{med}} = 8/\pi^{2} \approx 0.81$：同样的精度要多 23% 的闪光。

*怎么算出来。* 去掉分母后 $\ell'(\theta) = 0$ 是 $2n - 1$ 次多项式方程，根未必唯一：$n = 25$ 时约有四分之一的样本
会让 $\ell$ 有两个以上的局部极大，所以这个估计量是全局最大值点，而不是得分方程的“那个”根；常用做法是从
$\hat m_n$ 出发跑牛顿法。

### Part 4

**$X$ 的分布。** 抽角度，算出 $X_i = x_0 + d \tan\Theta_i$，再测经验分布函数与推导出的 $F$ 之间的 Kolmogorov–Smirnov 距离
$D_n = \sup_x \lvert F_n(x) - F(x) \rvert$。它的预言与 $F$ 是什么无关：只要 $F$ 是对的，$\sqrt n D_n$ 就收敛到 Kolmogorov
分布，其均值为 $\sqrt{\pi/2}\;\ln 2 \approx 0.869$，95% 分位点为 $1.358$。尺度若写错 30%，$D_n$ 就稳定在一个正数上，
$\sqrt n D_n$ 按 $\sqrt n$ 增长。

**$\bar X_n$ 的分布。** 均方误差是用错了工具：$E[(X - x_0)^{2}] = \infty$，所以 $\frac1R \sum_r (\bar X_n^{(r)} - x_0)^{2}$
关于 $R$ 没有极限——它由 $R$ 次重复中最大的那一次决定，重复得越多越往上漂。改用只需要一个分位数的
*中位绝对误差*（median absolute error）$\mathrm{med}_r \lvert \bar X_n^{(r)} - x_0 \rvert$；由
$P(\lvert X - x_0 \rvert \le d) = \frac{2}{\pi}\arctan 1 = \frac12$，它对每个 $n$ 都恰好等于 $d$。

**Part 3 的速度。** 同一个误差度量，在几个 $n$ 上测。由 $\sqrt n (T_n - x_0) \Rightarrow N(0,\; v)$ 和
$\Phi^{-1}(3/4) \approx 0.6745$，它约为 $0.6745 \sqrt{v/n}$，即中位数 $1.06\;d/\sqrt n$、最大似然估计 $0.954\;d/\sqrt n$，
而样本均值是不随 $n$ 变的 $d$。把 $n$ 乘以 16，前两者必须缩小到四分之一，第三个原地不动：这一次对比就把三个结论分开了。

### 追问

- 如果 $d$ 也未知，由 $Q_1 = x_0 - d$、$Q_3 = x_0 + d$ 直接给出 $\hat x_0 = (\hat Q_1 + \hat Q_3)/2$ 和
  $\hat d = (\hat Q_3 - \hat Q_1)/2$，排一次序即可；两参数的信息矩阵是 $\frac{1}{2 d^{2}}$ 乘单位阵，
  渐近地看两个参数互不干扰。
- 记 $\hat\varphi_n(t) = \frac1n \sum_j e^{itX_j}$，由 $\varphi_X(t) = \exp(itx_0 - d\lvert t \rvert)$，
  $-\ln\lvert \hat\varphi_n(t) \rvert / \lvert t \rvert$ 对任何固定的 $t \neq 0$ 都相合于 $d$；辐角只取到
  $(-\pi,\; \pi]$ 里，所以 $\arg \hat\varphi_n(t) / t$ 要 $\lvert t x_0 \rvert < \pi$ 才相合于 $x_0$。
  扫一遍数据就够，连排序都不用。
- 两个独立标准正态变量之比 $N_1/N_2$ 就是标准柯西分布：凡是比值形式的统计量都要当心，
  分母接近零会产生同样的 $1/x$ 尾巴，多跑几次取平均治不好。

<details>
<summary>验证代码（可运行）</summary>

```python
import math

import numpy as np
from scipy import integrate, stats

X0, D = -3.0, 2.0                    # the example: x0 = -3 km along the shore, d = 2 km out to sea
rng = np.random.default_rng(2026)


def cdf(x, loc=X0, scale=D):
    return 0.5 + np.arctan((np.asarray(x, dtype=float) - loc) / scale) / math.pi


def pdf(x, loc=X0, scale=D):
    return scale / (math.pi * (scale ** 2 + (np.asarray(x, dtype=float) - loc) ** 2))


def flashes(shape):
    """The physical model only: uniform angles through tan, with no Cauchy sampler involved."""
    return X0 + D * np.tan(rng.uniform(-math.pi / 2, math.pi / 2, shape))


# ---- Part 1: the derived F and f, against quadrature, against the library, and against the simulation
probe = np.array([-60.0, -9.0, X0 - D, X0, X0 + D, 4.0, 31.0])
assert np.allclose([integrate.quad(pdf, -np.inf, x)[0] for x in probe], cdf(probe), atol=1e-10)
assert np.allclose(cdf(probe), stats.cauchy(loc=X0, scale=D).cdf(probe))
assert np.allclose(pdf(probe), stats.cauchy(loc=X0, scale=D).pdf(probe))
assert cdf(X0) == 0.5 and math.isclose(cdf(X0 - D), 0.25) and math.isclose(cdf(X0 + D), 0.75)

n, reps = 2_000, 400
scaled_ks = np.array([math.sqrt(n) * stats.kstest(flashes(n), cdf).statistic for _ in range(reps)])
assert abs(scaled_ks.mean() - math.sqrt(math.pi / 2) * math.log(2)) < 0.05     # the Kolmogorov limit law
assert abs(np.mean(scaled_ks > stats.kstwobign.ppf(0.95)) - 0.05) < 0.03
big = 50_000                                                                   # NOTE: negative control
wrong = math.sqrt(big) * stats.kstest(flashes(big), lambda x: cdf(x, scale=1.3 * D)).statistic
assert math.isclose(wrong / math.sqrt(big), 2 * math.atan(math.sqrt(1.3)) / math.pi - 0.5, rel_tol=0.2)
assert wrong > 3 * scaled_ks.max()

# ---- Part 2: no expectation, the characteristic function, and the law of the sample mean
for cut in (1e3, 1e6, 1e9):                    # E|X - x0| diverges logarithmically
    tail = integrate.quad(lambda z: z * pdf(z, loc=0.0), 0.0, cut, points=[D])[0]
    assert math.isclose(tail, (D / (2 * math.pi)) * math.log1p(cut ** 2 / D ** 2), rel_tol=1e-9)
    assert abs(tail - (D / math.pi) * math.log(cut / D)) < 1e-5
for c in (1.0, 2.0, 9.0):                      # cutting at x0 - M and x0 + c M leaves x0 + (d / pi) ln c
    off = integrate.quad(lambda z: z * pdf(z, loc=0.0), -1e5, c * 1e5, points=[-D, D])[0]
    assert math.isclose(off, (D / math.pi) * math.log(c), abs_tol=1e-6)

for t in (0.35, 1.0, 4.0):                     # phi(t) = exp(i x0 t - d |t|), by oscillatory quadrature
    even = integrate.quad(lambda z: 2 * pdf(z, loc=0.0), 0, np.inf, weight="cos", wvar=t)[0]
    assert math.isclose(even, math.exp(-D * t), rel_tol=1e-6)
for y in (-14.0, 2 * X0, 5.0):                 # X1 + X2 is Cauchy(2 x0, 2 d), by convolution
    conv = integrate.quad(lambda u: pdf(u) * pdf(y - u), -np.inf, np.inf, limit=300)[0]
    assert math.isclose(conv, float(pdf(y, loc=2 * X0, scale=2 * D)), rel_tol=1e-8)
for size in (2, 32, 512):                      # so the sample mean has exactly the law of one flash
    assert stats.kstest(flashes((20_000, size)).mean(axis=1), cdf).pvalue > 1e-3
assert math.isclose(1 - 2 * math.atan(10.0) / math.pi, 0.0635, abs_tol=5e-5)   # P(|mean - x0| > 10 d)

# ---- Part 3: Fisher information, Kullback-Leibler divergence, and the two estimators
def derivative(x):                   # f'(x)
    return -2 * D * (x - X0) / (math.pi * (D ** 2 + (x - X0) ** 2) ** 2)


assert math.isclose(integrate.quad(lambda x: derivative(x) ** 2 / pdf(x), -np.inf, np.inf)[0],
                    1 / (2 * D ** 2), rel_tol=1e-6)
assert math.isclose(integrate.quad(lambda z: math.log1p(z * z) * pdf(z, loc=0.0, scale=1.0),
                                   -np.inf, np.inf)[0], 2 * math.log(2), rel_tol=1e-9)
for delta in (0.4, 3.0, 11.0):
    kl = integrate.quad(lambda x: pdf(x) * math.log(pdf(x) / pdf(x, loc=X0 + delta)), -np.inf, np.inf, limit=300)[0]
    assert math.isclose(kl, math.log1p(delta ** 2 / (4 * D ** 2)), rel_tol=1e-7)


def neg_log_likelihood(sample, theta):
    """-l(theta) up to a constant, straight from the density; one row of theta values per row of sample."""
    return np.log(D ** 2 + (sample[:, :, None] - theta[:, None, :]) ** 2).sum(axis=1)


def newton_mle(sample, theta, steps=12):
    """Newton on the score, started at theta (the sample median); one estimate per row."""
    for _ in range(steps):
        r = (sample - theta[:, None]) / D
        u = 1.0 + r * r
        score = (2 * r / u).sum(axis=1) / D                                   # l'(theta)
        curvature = (2 * (1 - r * r) / (u * u)).sum(axis=1) / D ** 2          # -l''(theta)
        step = np.where(curvature > 0, score / np.maximum(curvature, 1e-12), np.sign(score) * D)
        theta = theta + np.clip(step, -4 * D, 4 * D)       # NOTE: -l'' turns negative far from the root
    return theta


def brute_mle(sample, rounds=4, points=400):
    """The global maximiser by nested grid search on -l itself: no score, no Hessian, no Newton."""
    lo, hi = sample.min(axis=1), sample.max(axis=1)        # l' > 0 below the smallest flash, < 0 above the largest
    for _ in range(rounds):
        grid = lo[:, None] + (hi - lo)[:, None] * np.linspace(0.0, 1.0, points)
        best = grid[np.arange(len(sample)), neg_log_likelihood(sample, grid).argmin(axis=1)]
        width = (hi - lo) / (points - 1)
        lo, hi = best - width, best + width
    return (lo + hi) / 2


one_run, h = flashes(40)[None, :], 1e-3                    # score and curvature against finite differences
for theta in X0 + np.array([-1.7, -0.3, 0.0, 0.6, 2.2]):
    r = (one_run[0] - theta) / D
    left, here, right = neg_log_likelihood(one_run, np.array([[theta - h, theta, theta + h]]))[0]
    assert np.isclose((2 * r / (1 + r * r)).sum() / D, -(right - left) / (2 * h), rtol=1e-5, atol=1e-4)
    assert np.isclose((2 * (1 - r * r) / (1 + r * r) ** 2).sum() / D ** 2,
                      (right - 2 * here + left) / h ** 2, rtol=1e-4, atol=1e-3)

small = flashes((400, 25))                                 # Newton from the median against the grid search
middle = np.median(small, axis=1)
newton, brute = newton_mle(small, middle.copy()), brute_mle(small)
column = lambda v: neg_log_likelihood(small, v[:, None])[:, 0]
assert np.all(column(brute) <= column(newton) + 1e-6)
assert np.mean(np.abs(newton - brute) < 1e-3) > 0.97       # Newton lands on the global maximum
assert np.allclose(newton, newton_mle(small, middle.copy(), steps=30))          # 12 steps are enough

few = small[:200]                                                              # several roots of l' = 0
grid = np.linspace(few.min(axis=1), few.max(axis=1), 3000).T
r = (few[:, :, None] - grid[:, None, :]) / D
signs = np.sign((2 * r / (1 + r * r)).sum(axis=1))
maxima = ((signs[:, :-1] > 0) & (signs[:, 1:] < 0)).sum(axis=1)
assert 0.15 < np.mean(maxima > 1) < 0.42 and maxima.max() >= 3

# ---- Parts 3 and 4: how the error of the three estimators moves with n
COEF = stats.norm.ppf(0.75)                                # median of |N(0, v)| is 0.6745 sqrt(v)
table = {}
for size, reps in ((15, 20_000), (255, 8_000), (4095, 4_000)):
    draws = flashes((reps, size))
    centre = np.median(draws, axis=1)
    guesses = {"mean": draws.mean(axis=1), "median": centre, "mle": newton_mle(draws, centre.copy())}
    table[size] = {name: float(np.median(np.abs(g - X0))) for name, g in guesses.items()}

for size in table:                                         # the sample mean: median absolute error d, at every n
    assert math.isclose(table[size]["mean"], D, rel_tol=0.1)
    assert math.isclose(table[size]["median"], COEF * math.pi * D / 2 / math.sqrt(size), rel_tol=0.08)
    assert math.isclose(table[size]["mle"], COEF * math.sqrt(2) * D / math.sqrt(size), rel_tol=0.08)
    assert table[size]["mle"] < table[size]["median"] < table[size]["mean"]
assert 0.9 < table[4095]["mean"] / table[15]["mean"] < 1.1                      # flat in n
for name in ("median", "mle"):                                                 # and falling like 1 / sqrt(n)
    assert math.isclose(table[4095][name] / table[15][name], math.sqrt(15 / 4095), rel_tol=0.1)
assert math.isclose(table[4095]["mle"] / table[4095]["median"], 2 * math.sqrt(2) / math.pi, rel_tol=0.07)

# ---- Follow-ups
quartiles = np.percentile(flashes((2_000, 4095)), [25, 75], axis=1)
assert abs(np.median(quartiles.mean(axis=0)) - X0) < 0.05
assert abs(np.median((quartiles[1] - quartiles[0]) / 2) - D) < 0.05
phi = np.exp(0.5j * flashes((2_000, 4095))).mean(axis=1)   # empirical characteristic function at t = 1/2
assert abs(np.median(2 * np.angle(phi)) - X0) < 0.05 and abs(np.median(-2 * np.log(np.abs(phi))) - D) < 0.05
ratio = rng.standard_normal(200_000) / rng.standard_normal(200_000)            # N(0,1) / N(0,1) is standard Cauchy
assert stats.kstest(ratio, lambda x: cdf(x, loc=0.0, scale=1.0)).pvalue > 1e-3

step = 1e-5                                                # the two-parameter information matrix is diag(1, 1) / (2 d^2)
gradient = [lambda x: (np.log(pdf(x, loc=X0 + step)) - np.log(pdf(x, loc=X0 - step))) / (2 * step),
            lambda x: (np.log(pdf(x, scale=D + step)) - np.log(pdf(x, scale=D - step))) / (2 * step)]
for a, first in enumerate(gradient):
    for b, second in enumerate(gradient):
        entry = integrate.quad(lambda x: first(x) * second(x) * pdf(x), -np.inf, np.inf, limit=400)[0]
        assert abs(entry - (1 / (2 * D ** 2) if a == b else 0.0)) < 1e-8
```

</details>

</details>
