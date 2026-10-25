---
lab4_comms:
  awareness: 2026-10-12T07:12:00Z       # NIS2: the on-call judged the incident significant
  detection: 2026-10-12T07:09:19Z       # KSC: the detecting alert ShopCheckoutErrors started firing
  classification: 2026-10-12T08:00:00Z  # DORA: classified as a major ICT-related incident
  nis2:
    early_warning_due: 2026-10-13T07:12:00Z   # awareness + 24 h
    notification_due: 2026-10-15T07:12:00Z    # awareness + 72 h
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z    # one calendar month after notification_sent
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z   # detection + 24 h
    notification_due: 2026-10-15T07:09:19Z    # detection + 72 h
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z    # one calendar month after notification_sent
  dora:
    initial_due: 2026-10-12T12:00:00Z         # classification + 4 h, earlier than awareness + 24 h
    initial_sent: 2026-10-12T11:00:00Z
    intermediate_due: 2026-10-15T11:00:00Z    # initial_sent + 72 h
    intermediate_sent: 2026-10-14T10:00:00Z
    final_due: 2026-11-14T10:00:00Z           # one calendar month after intermediate_sent
  log:
    - {at: 2026-10-12T11:00:00Z, to: "the financial supervisor (KNF)", what: "DORA initial notification of a major ICT-related incident"}
    - {at: 2026-10-12T15:00:00Z, to: "the CSIRT", what: "NIS2 and KSC early warning: significant incident, not suspected to be malicious"}
    - {at: 2026-10-13T09:00:00Z, to: "the CSIRT", what: "NIS2 and KSC incident notification with impact, root cause and workaround"}
    - {at: 2026-10-14T10:00:00Z, to: "the financial supervisor (KNF)", what: "DORA intermediate report"}
---
<!-- ai-generated: 60% - Claude Code computed the deadlines with a script and drafted the prose; I chose the three instants and when each report goes out -->

# Communications log: the regulators' clocks

The incident is the recording lab4-rec-3 of Monday 12 October 2026 (ticket `1224ad8d-06a8-4ae3-865a-da2015a4ddb5`).
The shop is assumed to fall under NIS2, the Polish KSC act and DORA at once, and the incident to be significant under
the first two and major under the third. Every instant is in UTC; the deadlines are elapsed hours, and a month is the
same day and time of the next month on the UTC calendar.

## The three instants you defend

**Detection (KSC), 07:09:19Z.** KSC counts "od momentu jego wykrycia", from the moment of detection. The earliest
moment the organisation detected anything is when the P1 alert `ShopCheckoutErrors` started firing in Prometheus
(the `detection` of the postmortem); the page reached the on-call's phone seconds later. Anything later, such as the
acknowledgement at 07:10:07Z, would be the on-call reacting, not the system detecting.

**Awareness (NIS2), 07:12:00Z.** NIS2 counts from "becoming aware" of a *significant* incident, which is a judgement,
not an alert. At 07:10:07Z the on-call acknowledged the ticket knowing only that checkout errors had paged. By
07:12:00Z the error ratio of checkout's PlaceOrder had stayed above 6 % for three minutes, the storefront's p99 was
near 900 ms and product-catalog was failing one GetProduct call in thirteen: customers could not complete orders,
which is the impact that makes it significant. Choosing the earlier instant would also be defensible; choosing a
later one would only shorten the clock artificially.

**Classification (DORA), 08:00:00Z.** DORA's classification as major needs the criteria of the technical standard
(clients affected, duration, service criticality, economic impact) to be assessed. Service was restored at 07:12:19Z
and the last seeded flag was off by 07:13Z; at 08:00:00Z, with the full impact window known (about seven minutes of
failed and slow orders on a critical service), the incident manager classifies it as major. The DORA initial
deadline is then 12:00:00Z (classification + 4 h), which is earlier than awareness + 24 h.

## The log

| when (UTC) | to | what | clock it answers |
|---|---|---|---|
| 2026-10-12 11:00 | the financial supervisor (KNF) | DORA initial notification | DORA initial, due 12:00 |
| 2026-10-12 15:00 | the CSIRT | NIS2 and KSC early warning | NIS2 due 2026-10-13 07:12, KSC due 2026-10-13 07:09:19 |
| 2026-10-13 09:00 | the CSIRT | NIS2 and KSC incident notification | NIS2 due 2026-10-15 07:12, KSC due 2026-10-15 07:09:19 |
| 2026-10-14 10:00 | the financial supervisor (KNF) | DORA intermediate report | due 2026-10-15 11:00 |

The final reports follow from the instants above: NIS2 and KSC by 2026-11-13 09:00 (a month after the notification),
DORA by 2026-11-14 10:00 (a month after the intermediate report). Each report is sent with margin rather than at the
deadline, and the early warning goes out the same day so the CSIRT hears it before the notification, not with it.
