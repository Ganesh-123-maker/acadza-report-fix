# PRODUCT.md — Report → Fix

## Who loses the most when a question is broken

The student who got it *right*. A wrong answer key does not just teach the
wrong thing — it punishes the student who worked it out correctly, tells
them their method is broken, and teaches them to distrust their own
reasoning the week before JEE. That student is usually studying alone, at
night, with no teacher to overrule the screen. The second-biggest loser is
the student who meets a question that cannot be answered at all — a blank
option, a missing figure, two identical options — and burns twenty minutes
deciding whether they are stupid before concluding the app is. Both lose
quietly: they do not write angry emails, they just stop trusting the
platform, one question at a time.

The design follows from that. The queue is ordered by harm, not by arrival
date: answer-key errors first, then unanswerable questions, then missing
data, then wrong solutions, then filing, then cosmetic. A faculty member
opening the console at 10 PM should spend their first ten minutes on the
cases that are actively teaching 8 lakh students the wrong answer, not on
the oldest report. Every case shows the verdict and the before/after diff
*before* the full question, because "what changed and why" is the decision
and the question is the evidence. Every student reply is written for a
stressed 17-year-old, not for a ticket queue: if they were right, it says
so plainly; if they were wrong, it shows the one step they missed instead
of telling them they were wrong. And the console never lets the AI mark its
own homework — the solver never sees the key it is checking.

## What I would never let the AI auto-apply, and why

Anything that creates new content, and anything that changes a mark on
judgement rather than proof. Concretely: a new figure, a new distractor, a
rewritten solution, a re-filed chapter, a syllabus call, and any answer-key
change the independent solver does not agree with. A distractor is a
teaching decision — which wrong idea is worth planting — and a figure is a
piece of authorship; an AI that invents either is inventing curriculum.
A syllabus call is a policy decision about what lakhs of students should
study, and no confidence score makes it a computation. And an answer key is
the one number that decides a student's rank: changing it needs two
independent solves that agree, not one model's opinion. Everything in that
list goes to a human, with the evidence attached and the question left live
meanwhile — because taking a question down on suspicion hurts students
more than leaving a flagged one up for a day. The one deliberate exception
proves the rule: the missing option D in the centre-of-mass question is
filled with 14 m/s, the canonical misconception, and the console flags it
as a swappable proposal rather than a fact.

## One metric I would watch in week 1

**Re-report rate on fixed questions: of the questions we auto-fixed, what
fraction gets reported again within 7 days, and what fraction of those
re-reports are correct?** It is the only number that catches both failure
modes at once. If it is high, our fixes are wrong and we are shipping
defects faster. If it is zero, either the fixes are perfect or students
have stopped reporting — and the second is worse, because silence looks
exactly like success. I would split it by repair type (answer-key fixes
should re-report near zero; solution fixes will re-report more, because
students argue about working), and I would treat a rising re-report rate
as a stop-the-line signal, not a dashboard decoration. Vanity alternatives
— reports triaged per day, auto-apply rate — reward speed and automation
whether or not the fixes are right.

## One idea beyond this brief

**A "why was I wrong?" reply that teaches, not just verdicts.** Today a
student who reports a correct question gets a polite "you were wrong".
But the report itself is a diagnostic: the student told us exactly which
wrong idea they hold (mu = 0.4, n = 1, 22 V instead of 14 V, 3112.99
instead of 3113). That is a misconception with a name, a question attached,
and a student attached. The next step is to turn each closed `no_error`
report into a one-line targeted hint — "you used the potential at P, the
question asks for the difference" — shown the next time that student meets
a question testing the same idea, and to aggregate the misconceptions
across students into a weekly "most common wrong ideas" brief for faculty.
It converts the report queue from a cost centre (defects to fix) into the
cheapest misconception dataset Acadza owns, and it makes the student who
was wrong feel helped rather than dismissed. That is the student who comes
back tomorrow.
