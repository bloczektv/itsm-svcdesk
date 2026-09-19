---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 75% - Claude Code drafted all three decisions and their justifications from REQUIREMENTS.md and API.md; the author reviewed and approved the resolutions and wording before submission -->

# Decisions

## C1 - SLA clock for P1

**Decision:** Both SLA targets for P1 (acknowledge within 15 minutes, resolve within 4 hours) run on the
wall-clock, counting real elapsed time around the clock, including nights, weekends and outside business
hours.

**Rejected alternative:** Pausing the P1 clock outside business hours (Mon-Fri 08:00-16:00 Europe/Warsaw),
the same rule R-13 applies to every other priority.

**Reason:** R-14 states explicitly that a P1 raised on Friday evening is late 15 minutes later, not on
Monday morning; P1 means the whole organisation has stopped working, and a service desk that lets its most
severe incident sit unacknowledged over a weekend is not doing its job. Business-hours pausing is
appropriate for lower priorities where the impact is contained, not for organisation-wide outages.

**Service owner:** The IT operations manager, because they own the incident-response SLA and are the one
paged when a P1 breaches; they are best placed to judge whether 24/7 coverage for P1 is affordable against
the desk's staffing model.

**Customer outcome:** Whoever reports an organisation-stopping incident gets a guaranteed response within
15 minutes and a fix within 4 hours, any day, any hour, instead of discovering on Monday that their weekend
outage was never even acknowledged.

## C2 - Closed tickets and reopening

**Decision:** Reopening is only possible from a `resolved` ticket, within 7 days of `resolved_at`. A
`closed` ticket can never be reopened; the reporter opens a new ticket that references the old one via
`related_to`.

**Rejected alternative:** Allowing reopen from a `closed` ticket too, within 7 days of `closed_at`,
effectively letting a ticket that both the agent and the reporter had marked as done come back to life.

**Reason:** R-09 states plainly that "a closed ticket is immutable" and gives the intended alternative path
(a new, linked ticket) in the same sentence. Closed tickets are the historical record the Monday SLA report
is built from; if a closed ticket's state and timestamps can still change afterwards, every report
generated between the closure and the reopen was silently wrong, and nobody can tell which reports to
distrust.

**Service owner:** The service desk manager who is accountable for the weekly SLA report, because
immutability of closed records is what makes that report trustworthy in the first place.

**Customer outcome:** The reporter still gets their recurring issue handled promptly, just as a clearly
linked new ticket rather than a resurrected old one; the organisation gets SLA reports that never silently
change after the fact.

## C3 - VIP reporters and the priority matrix

**Decision:** After the impact/urgency matrix computes a priority, a VIP reporter's ticket is raised to at
least P2; a VIP ticket that the matrix would already rate P1 or P2 is unaffected.

**Rejected alternative:** Letting the matrix decide alone in every case, storing `reporter.vip` purely as
metadata with no effect on the computed priority, even for a VIP's cosmetic, one-person issue.

**Reason:** R-06 states its own business purpose directly: "so that executive issues are visible to the
desk immediately." A named-account or executive reporter whose minor request sits at P4 behind forty other
tickets is a relationship risk the desk cannot absorb; a floor at P2 guarantees visibility without letting
VIP status override genuinely critical, non-VIP incidents, which still reach P1 on their own merits.

**Service owner:** The service desk manager, because prioritising by who is asking rather than only what is
broken is a policy trade-off between fairness and stakeholder management that belongs to the desk's
leadership, not to the matrix alone.

**Customer outcome:** A VIP reporter's request is never left languishing at the bottom of the queue
regardless of its technical severity, while every other reporter's priority is still decided purely by
impact and urgency, unaffected by who they are.
