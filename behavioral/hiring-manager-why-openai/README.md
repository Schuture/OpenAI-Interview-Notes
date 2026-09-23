# Hiring Manager Round: Why OpenAI, Safety, AGI

[English](README.md) · [中文](README.zh.md)

<!-- meta:begin -->
| Type | Priority | Difficulty | Roles | Topics | Format | Round |
| --- | --- | --- | --- | --- | --- | --- |
| Behavioral | ★★★★★ | — | All | behavioral, why-company, ai-safety, cross-functional | 60 min | Onsite |
<!-- meta:end -->

## Problem

This is a 60-minute, one-on-one conversation with a hiring manager, held after the technical rounds.
Nothing is submitted in advance. What you need to bring is a prepared answer to "why OpenAI" that fits
the team the interviewer is from, a position of your own on AGI and AI safety, and stories from your own
experience covering a project you drove, a technical disagreement, a failure, a time you held your
ground under pressure, and work with a non-engineering partner. The questions fall into five groups.

### Motivation

- Why OpenAI specifically, as opposed to another company working on similar problems?
- Why this team, and why this particular research or product direction, rather than a different team at
  the same company?
- Why leave your current role now — what changed?
- For every past job change, what was the actual reason you moved?

### Views on AGI and safety

- What is your own view on AGI — what would a system need to be able to do, and on what timeframe, for
  you to call it that?
- What does AI safety concretely mean to you, in the context of your own work?
- How do you think about AI democratization — making these systems more broadly available? What do you
  see as the biggest risks in doing so (cost of access, bias in the training data, safety, privacy,
  uneven availability across regions, potential for misuse)?
- How do you balance shipping quickly against the time it takes to validate quality and safety?

### A hypothetical dilemma

- Your manager tells you to ship a model feature without the safety testing it was supposed to go
  through, because a deadline is at risk. What do you do?
- Same situation, except the deadline comes from an external partner launch rather than an internal
  target, and only part of the test suite would be skipped. Does that change your answer?
- Same situation, except it's a peer on another team asking you to skip a review step they own, not your
  manager. Does that change what you do?

### Past experience

- Tell me about a project you drove yourself, end to end, and shipped.
- Tell me about a project you built all the way to completion but ultimately decided not to ship. Why?
- Describe a technical disagreement you had with a colleague and how it was resolved.
- What is the hardest technical or collaboration problem you've faced, and how did you work through it?
- Tell me about a time you failed at something you cared about.
- Tell me about a time you pushed back on a decision, or held your ground under pressure, and what
  happened.

### Cross-functional collaboration

- Describe a project where you worked closely with a product manager or another non-engineering
  partner.
- Tell me about a time you had to explain a technical trade-off to a non-technical audience so they
  could make a decision.
- Tell me about a disagreement with a cross-functional partner about scope or priority, and how it was
  resolved.

## Reference solution

<details>
<summary>Show the reference solution</summary>

Before the round, confirm with your recruiter which team the hiring manager is from and whether it is
the team you would join: that decides which version of "why OpenAI" you bring and how specific your
"why this team" answer should get.

### Motivation

This tests whether your answer is tied to something specific about you and about the company, rather
than a sentence that would work for any employer.

Skeleton for "why OpenAI" / "why this team": connect three things — your own research or engineering
direction, a specific opinion you hold about one product line or one piece of public research (not just
that you admire it), and what this particular role lets you do that you couldn't do elsewhere. Prepare
two or three versions ahead of time — weighted toward research, toward safety, or toward product and
infrastructure — and pick the one that matches the interviewer's team before you walk in. For example:
your research or engineering direction is [direction A]; your specific take on [a named product line or
a piece of public research] is [your actual opinion, not just praise]; this role lets you do [a kind of
work you name], which you couldn't do in your current role.

Skeleton for "why leave now" / past job changes: give one sentence per job that names what you were
moving toward — a bigger class of problem, a different stack, more scope — rather than what you disliked
about the place you left. For "why now", name the change that makes this the moment — a project that
shipped, a scope that stopped growing — as a fact, not a grievance. The reasons across jobs should read
as one consistent line, not a different justification each time that contradicts the last.

The common way to lose points is a generic answer that fits any AI company ("the mission", "AGI is
exciting"), preparing only one version regardless of which team is interviewing you, or turning a
past-job answer into a complaint about a former manager or company. Before the round, read the
company's recent public releases and safety publications and pick one point you actually hold a view
on; then write down the version for this team and the one-line reasons rather than improvising them.

### Views on AGI and safety

This tests whether you've actually thought about these questions and can name a concrete risk and a
concrete mitigation, not whether you land on a particular side.

Skeleton: state your own working definition (what you mean by "AGI", what class of problem you mean by
"safety"), give your timeframe as a range together with the assumption it rests on rather than as a
single year, name one or two specific risks you consider important — not an abstract "loss of
control" — connect them to your own line of work and what you'd do about them, and say plainly where
you're still uncertain.

For AI democratization, break "wider access" into the specific risk categories rather than giving one
verdict on whether it's good: cost (who can actually afford to build on it), data bias (whose language
and behavior the training data represents, and who ends up served worse), safety (a more capable system
reaching more people also reaches more bad actors), privacy (more of people's own data flowing through
the system as it's used more widely), regional variation (language coverage, regulation, which places
get access at all), and misuse — one concrete sentence per category, ending on which one you'd prioritize
mitigating first.

For balancing iteration speed against quality and safety, name one concrete decision point from your own
experience — a situation where you'd argue for slowing a release down, and a signal that would tell you
it's fine to proceed on schedule — rather than saying both matter in the abstract.

The common way to lose points is staying entirely at the level of distant, existential risk with no
connection to your own work, or the opposite — only naming today's product bugs and never engaging with
the risks that come from more capable systems — or an answer with no uncertainty in it at all, which
reads as a rehearsed position rather than your own thinking.

### A hypothetical dilemma

This tests whether you comply unconditionally, push back without first understanding the constraints, or
clarify the situation and look for an option that respects both the deadline and the risk before
escalating.

Skeleton: first, ask what you'd need to know — what the specific risk is, which part of the testing is
missing, where the deadline actually comes from, and whether it can move or be partially met. Second,
propose an option that serves both constraints, worked out with whoever owns the tests rather than
decided by you alone: a smaller release (internal only, or a small traffic percentage); splitting the
test suite into what's load-bearing and what isn't and running the critical part now; or shipping with
added monitoring and a fast rollback path, which only fits a risk whose harm would show up quickly and
can be undone. Third, if you're still asked to cross a line you consider unacceptable, escalate through
a real channel — the safety lead, a written risk review — tell your manager that you are doing so, and
leave a written record of the decision and its reasoning, rather than complying quietly or blocking the
launch on your own. The aim of escalating is that whoever is accountable for the risk makes the call
with the facts in front of them, not that you win the argument. A workable template for that record:
"known risk is [x], the missing test is [y], the proposed alternative is [z]; if we still ship without
completing [y], we need written sign-off from [the owner of that risk]."

The two variants use the same skeleton; what changes is which facts to clarify first. With an external
deadline: whether the date is really immovable or the partner could launch with a reduced scope, and
whether the skipped part of the suite covers the risks this feature actually carries. With a peer:
whether the person who runs a review also has the authority to waive it; if not, the question goes to
whoever does, and your own manager hears about it from you. The order — clarify, propose, escalate —
doesn't change.

The common way to lose points is one of two extremes: unconditional compliance ("my manager decided, so
I ship it"), or objecting on safety grounds immediately without first finding out what the risk and the
deadline actually are. A strong answer opens with at least one clarifying question before it gets to a
plan.

### Past experience

This tests what you personally did, whether the result has a number attached, and whether you changed
anything afterward.

Skeleton: standard STAR — situation, task, action (described with "I", naming your own part even when
the project was a team effort), result (a number or an observable change you can point to). For the
negative questions (failure, disagreement, pushback), add one sentence on what you changed about how you
work because of it. For the project you decided not to ship, add the bar you were judging against —
missing data, a result short of a stated threshold, risk outweighing the benefit — and make it a bar you
set yourself, not one someone else handed you after the fact.

The common way to lose points on the negative questions is picking an example with no real stakes ("we
disagreed about a variable name once") or attributing the failure to someone else's mistake instead of
your own decision. Pick a story that had a real cost — rework, a missed deadline, a wrong call you
owned — and be specific about your own role in the action step and the number in the result.

| Story | The failure mode specific to it |
| --- | --- |
| Drove and shipped | Can't separate "I" from "the team"; no number in the result |
| Decided not to ship | Blames the non-release on an external cause (requirements changed, ran out of time) instead of naming the bar you judged it against |
| Technical disagreement | Only states your own position, skips the other side's reasoning and how you converged |
| Hardest problem | Equates "hard" with "took a long time"; can't name the specific step it got stuck on |
| Failure | Picks a low-stakes example, or blames someone else |
| Pushback / held your ground | Only claims you were "right"; skips what evidence you had and what you did afterward |

### Cross-functional collaboration

This tests whether you can work with a non-engineering partner and translate a technical trade-off into
terms they can act on.

Skeleton: name the specific collaboration (which role, what project), the specific point of
disagreement or trade-off, how you translated the technical side into what the other person cared about
(time, cost, user experience — not implementation detail), and the outcome. For a disagreement about
scope or priority, also state the partner's constraint the way they would put it, and who made the
final call. For example: a model change cut inference latency from [X ms] to [Y ms] using [a
technique]; the sentence that got a product manager to prioritize it was about how much faster the page
opens for users, not about the technique itself.

The common way to lose points is a content-free claim ("we communicated well") with no actual example,
or repeating the technical detail instead of translating it into something the partner could decide on.

### When the interviewer says little

If the questions are short and your answers get no follow-ups, don't settle into waiting for the next
question. End each answer with one sentence connecting it to this specific team or role, and prepare
two or three questions you actually want answered — how the team prioritizes, what the next six months
look like for this direction — to ask whenever the conversation leaves a natural opening.

### Prep outline

Copy this into `my/` and fill it in with your own answers.

```text
Three versions of "why OpenAI" (one line each):
  Research-leaning:
  Safety-leaning:
  Product / infra-leaning:

Reason for each past job change (one line each, name what you moved toward):
  Job 1 -> Job 2:
  Job 2 -> Job 3:
  Job 3 -> current:

Your view on AGI and safety:
  Working definition of AGI / safety:
  Timeframe (a range + the assumption behind it):
  Risk 1:
  Risk 2:
  How this connects to your own work / what you'd do about it:
  Where you're still uncertain:
  AI democratization: which risk category you'd prioritize mitigating first:

The dilemma (the clarifying questions you'd ask first):
  1.
  2.
  3.

Six STAR stories (title + one number each):
  Drove and shipped:
  Decided not to ship:
  Technical disagreement:
  Hardest technical/collaboration problem:
  Failure:
  Pushback / held your ground:

Cross-functional story (the partner's role + the one sentence that translated the trade-off):

Three questions to ask the interviewer:
  1.
  2.
  3.
```

</details>
