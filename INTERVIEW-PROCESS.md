# How the Loop Runs

[English](INTERVIEW-PROCESS.md) · [中文](INTERVIEW-PROCESS.zh.md)

> [!NOTE]
> This page collects the patterns that recur across publicly shared interview accounts. It is not an official
> description of any hiring process, nothing here is guaranteed, and teams differ from one another. Treat it as
> a map of what to expect, and let your recruiter's own instructions override anything written here.
> Last reviewed against community reports from September 2026.

## Getting an interview

Most accounts start one of four ways, in rough order of how often they come up: a recruiter reaches out (often
on LinkedIn); a referral from someone inside, including people met at events rather than old colleagues; an
outside recruiting agency; or an ordinary application through the careers site. An online assessment is rarely
mentioned — the recruiter conversation usually leads straight to the technical rounds.

Two practical notes. Candidates who rescheduled several times report the process being dropped, so treat the
first slot you accept as the one you will take. And the recruiter conversation is a good moment to ask which
level your background is being calibrated at; people who asked got an answer, and level mismatches are a common
reason a loop ends late rather than early.

## The shape of the loop

| Stage | Typical shape |
| --- | --- |
| Recruiter screen | About half an hour. Background, why this company, which kind of work you want, compensation expectations, timeline, location. A few people report being turned down at this stage. |
| Phone screens | Two rounds of about an hour, one coding and one system design, most often back to back on the same day. Some loops split them across two days; a few report a single 75-minute coding round instead. |
| Virtual onsite | Four to five rounds: coding, system design, behavioral, a technical deep dive presented from your own slides, and a hiring-manager conversation. ML-leaning roles add a 60–75 minute ML coding round, sometimes in a notebook. |
| Team match | Where the loop was not run by one specific team, a hiring-manager conversation decides the team afterwards. Loops opened by a single team usually skip this. |
| References | Commonly one peer and one manager, and they may be former colleagues. Usually requested after the technical rounds, not before. |
| Offer | Level is decided at the end, and several accounts describe it being set by the behavioral and deep-dive rounds rather than by the coding ones. |

Waiting times vary widely. Results after a phone screen are often back within one to four working days — a few
people heard the same evening — but two-week gaps also happen. The step most likely to stall is the one between
passing the phone screens and being scheduled for the onsite, where headcount decisions can add weeks.

Two variations show up often enough to plan for. Since around August 2026, a number of candidates were asked for
**one extra round after the onsite**, described only as an additional coding or architecture interview. And some
loops insert the **hiring-manager behavioral round before the onsite**, as a gate rather than as a closing
conversation.

## What each round asks for

| Round | Usual length | What it is looking for | Where to practise here |
| --- | --- | --- | --- |
| Coding | 60 min, sometimes 75 | Working code, quickly, on a problem with several parts that build on each other. Speed and correctness count for more than polish. | The [coding problems](README.md#problems) |
| ML coding | 60–75 min | Implementing or debugging practical ML code, plus the reasoning behind it: shapes, gradients, numerical stability, data quality. | The ML-flavoured coding problems |
| System design | 60 min | Requirements, estimates, data model and API, an architecture, then two or three deep dives. Recent loops lean towards AI infrastructure and towards device or job scheduling. | The [system design problems](README.md#problems) |
| Technical deep dive | Usually 60 min, 45 in some research orgs | One past project of yours, presented from slides, with the interviewer pushing on decisions, trade-offs and measured impact. | [Technical deep dive](behavioral/technical-deep-dive/README.md) |
| Behavioral / hiring manager | 30–60 min | Ownership, conflict, cross-functional work, why this company, and your views on AGI and safety. | [Hiring manager round](behavioral/hiring-manager-why-openai/README.md) |

## How problems are handed out

Several conventions come up in report after report, and they change how you should practise.

**Parts are released one at a time.** A coding problem arrives as a first part only; the next part appears once
the current one passes its tests, and your code carries over. Finishing the early parts quickly is what buys
time for the later ones, and reworking your design halfway through is expensive.

**Tests may or may not be provided.** Some problems come with hidden or visible test cases that your code has to
pass; others come with nothing and you are expected to write your own, or to walk through your code out loud.
Both happen often enough that you should be ready for either.

**The environment is a shared editor plus a video call**, most often CoderPad and Google Meet, with a
whiteboard tool such as Excalidraw for design rounds. Output and logs land at the bottom of the editor pane,
which is easy to miss while debugging. Any language is usually allowed, and Python is the common choice; people
who used more verbose languages report running out of time. AI coding assistants are not allowed, and at least
one loop asked for editor autocomplete to be turned off.

**The prompt you get in advance varies.** Some recruiters send a detailed note (one named the Python threading
primitives worth reviewing, and said the standard library documentation would be available during the
interview), some send a generic description, and some send nothing. A few people report a prompt that did not
match the problem they were given. Prepare for the round type, not for the prompt.

## What gets you through

Across accounts, the same few things separate the people who pass from the people who do not.

Finish the early parts fast and correctly; a small bug in part one costs the follow-ups. State the ambiguities
you see before coding, and pick a rule rather than waiting to be told. Watch for constraints stated once and
never repeated — one candidate was failed for state that grew with the number of keys seen, which the problem
statement had mentioned in a single sentence. In design rounds, the failure mode is usually being drawn deep
into one topic and running out of time for the rest, so keep an eye on the clock yourself. And prepare the
non-technical rounds as seriously as the technical ones: they are the rounds most often described as deciding
the level of the offer.

Not every outcome is about you. Several accounts describe a loop that went well ending in no offer because the
team lost its headcount, or because the match with the team was wrong from the start.

## If it does not work out

The most commonly reported cooling-off period is about twelve months, though not every account agrees — one
candidate was told there was no cooling-off period and to apply to a different team, and another was told the
limit was on how many roles you may apply to in a window. Ask your recruiter rather than relying on any of this.

## Preparing with this repository

Pick the track for your role in the [roadmap](ROADMAP.md) and work down it. Practise coding problems part by
part under a timer, since that is how they arrive. For design rounds, talk through the whole prompt in an hour
before opening the reference solution. Start the deep-dive slides and the behavioral stories early: they take
longer to get right than any single coding problem, and they are worth the most at the end.
