# elicit / method — how to run the question set

**Interview the material, not the coordinators.**

Every question in `questions.yml` names its `sources` before it names anyone, and the order is
deliberate. The documents and the timestamps answer most of these better than people can, because
people report the rule they believe and the record carries the rule that operated. Where those
differ, the difference is the finding — and you will lose it if you asked a person first and then
went looking for confirmation.

This file is short on purpose. If you read nothing else: **the answers are already in your
building, and the fastest way to get them wrong is to convene a meeting.**

---

## The order of resort

1. **The controlled document.** The agreement, the SOP, the processor contract. If it states a
   number, that number is your answer *and* your obligation, whether or not anyone works to it.
2. **The record's own timestamps.** Pull the last two quarters and look at the distribution, not
   the mean. The check you are about to write will fire on the tail.
3. **The person who does the work.** Last, and with the first two in hand. Not to be corrected —
   to explain the gap between them, which is the part no document holds.

When 1 and 2 disagree, encode 1 and let the floor show you 2. That is the entire proposition: the
gap becomes visible per case, at entry, instead of arriving as an aggregate months later.

## What "site-variant" does not mean

An L0/L2 answer sets *your number under a mandated duty*. It does not let you relax the duty. Each
such question carries a `mandated_floor` line naming the clause the duty comes from, and the
check's crosswalk mapping pins that clause byte-for-byte. If your answer would put you outside the
floor, the answer is wrong and the mapping is how you find out.

## Three failure modes, named so you can watch for them

**The aspirational number.** Someone gives you the target rather than the practice. A clock nobody
meets teaches people to ignore clocks, and the first month of alarms will train exactly that. If
the honest answer is "when we get to it", encode a longer interval and tighten it deliberately
later — from a baseline you can see.

**The number with no field behind it.** "Fresh tissue gets ten days" is only encodable if *fresh*
is a value the record carries. Half the answers here fail not on the number but on the modelling:
the check ends up abstaining on every case, which reads on a board as silence and is actually a
gap. `floor/FIELDS.md` lists every path the encoded checks read; if your answer needs a field that
is not there, that is the real deliverable of the conversation.

**The remembered exception.** Every cadence and every deadline has a legitimate suspension —
unstable donor, hospital OR unavailable, lab down. If the exception is not *logged with a
reference*, the floor cannot tell a justified pause from a forgotten case and will alarm on both,
and within a month somebody will switch the check off. Ask for the exception at the same time as
the rule, every time.

## What you produce

One `floor/checks/SV-xxx.check.yml` per answer, and a fixture that fails. The refusals in
`examples/worked/REFUSED.md` are the ones to read first: they show what the gates say when a check
is well-formed and still wrong, which is the interesting case and the one a model produces most
confidently.

## What this kit will not do for you

It will not author an L0 or L1 element. If a completion would require inventing mandated policy or
a quality-science invariant, the kit refuses and says so — `examples/worked/REFUSED.md` §04 is that
refusal, run against the real gate. The mandated half ships identical to everyone; the half that is
yours is completed here, in your building, and mounted only under your signature.
