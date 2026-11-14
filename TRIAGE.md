---
lab5_triage:
  image: ghcr.io/bloczektv/itsm-svcdesk@sha256:5884b9f509cf27b3f52fd9a4bddc0374dbca68e429e982fe909a3dba8c8b54e1
  sarif_receipt: 412
---
<!-- ai-generated: 70% - Claude Code read the CI logs and the receipted SARIF and drafted the rows; I checked each fix in the run that followed it -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which. The rows for the
reporting scanners cover every (tool, rule) outside `lab5-canary/` in the receipted SARIF (the canary run of
`lab5/canary`, commit 657e7dc, parent c13c3dd). `.trivyignore` and `.gitleaksignore` hold no entries: every finding
below was fixed, so there is nothing to ignore.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-76844 | fix | image gate, zlib1g 1:1.3.dfsg+really1.3.1-1+b1 in the python:3.13-slim base (HIGH, fixed in +deb13u1): `apt-get update && apt-get upgrade -y` added right after `FROM` in the Dockerfile (commit c13c3dd); the next image job was green |
| trivy | CVE-2026-85091 | fix | image gate, the second zlib1g HIGH (heap overflow in gz_vacate), same package and same fixed version; gone with the same `apt-get upgrade` line in the Dockerfile (c13c3dd) |
| trivy | CVE-2024-47081 | fix | requirements.txt line 4, requests 2.32.3 (MEDIUM, .netrc credential leak to other hosts; fixed in 2.32.4): pin raised to requests==2.33.0 (commit 10f9ebf), which also covers CVE-2026-25645 |
| trivy | CVE-2026-25645 | fix | requirements.txt line 4, requests 2.32.3 (MEDIUM, fixed in 2.33.0): pin raised to requests==2.33.0 in requirements.txt (10f9ebf); build-test still passes 14/14 |
| trivy | CVE-2025-71176 | fix | requirements.txt line 3, pytest 8.3.4 (MEDIUM, fixed in 9.0.3): pin raised to pytest==9.1.1, the version the course grader itself runs, in requirements.txt (10f9ebf); the 14 service tests pass on it |
| grype | GHSA-9hjg-9r4m-mvj7-requests | fix | /requirements.txt line 1 (Grype gives line 1 for every pin), requests 2.32.3, fix version 2.32.4 (the advisory Trivy names CVE-2024-47081); fixed by the requests==2.33.0 pin (10f9ebf) |
| grype | GHSA-gc5v-m9x4-r6x2-requests | fix | /requirements.txt, requests 2.32.3, fix version 2.33.0 (Trivy's CVE-2026-25645); fixed by the requests==2.33.0 pin in requirements.txt (10f9ebf) |
| grype | GHSA-6w46-j5rx-g56g-pytest | fix | /requirements.txt, pytest 8.3.4, fix version 9.0.3 (Trivy's CVE-2025-71176); fixed by the pytest==9.1.1 pin in requirements.txt (10f9ebf) |
| osv-scanner | CVE-2024-47081 | fix | /src/requirements.txt (OSV-Scanner's mount of the repository root, so my root requirements.txt), requests 2.32.3, reported twice; fixed by requests==2.33.0 (10f9ebf) |
| osv-scanner | CVE-2026-25645 | fix | the same requirements.txt, requests 2.32.3, reported twice; fixed by the requests==2.33.0 pin (10f9ebf) |
| osv-scanner | CVE-2025-71176 | fix | the same requirements.txt, pytest 8.3.4, reported twice; fixed by the pytest==9.1.1 pin (10f9ebf) |
| semgrep | semgrep.svcdesk-sql-not-literal | false-positive | my own rule (semgrep/rules.yml, Stretch 3), not in the receipted SARIF: src/svcdesk/store.py line 98, list_all(). The query is built only from constant fragments (" AND state = ?", " AND priority = ?") and every value is bound through params, so no request value reaches the SQL text; the rule stays as a guard against a future f-string query |
| semgrep | semgrep.svcdesk-upstream-url-fstring | false-positive | my own rule (semgrep/rules.yml, Stretch 3): src/svcdesk/kb.py line 37, _client.get(f"{KB_INDEX_URL}/search", ...). The base URL is read once from the environment at start-up and the path is constant; the user's q travels only in params=, so no request value can reach the host or path |
| semgrep | dockerfile.security.missing-user.missing-user | fix | Dockerfile line 23 (the CMD): the container ran as root. Added a system user svcdesk (uid 10001) that owns /data and `USER svcdesk` before the CMD (10f9ebf); compose-up and the 14 tests pass as that user |

Two decisions that left no finding behind, so no row of their own: pip is uninstalled at the end of the
`pip install` line, because pip vendors old copies of msgpack, urllib3 and setuptools' `pkg_resources` that no pip
release fixes yet and svcdesk never calls pip at run time; and gitleaks found nothing outside `lab5-canary/`.

## Bake-off

My canary set has 9 labelled defects: 4 in code (A03 path traversal, A09 deserialization, A11 injection through
`eval`, A16 SSRF), 3 hard-coded credentials (C01, C05, C06) and 2 vulnerable pins (D01 cryptography 3.2, D02
fastapi 0.65.1). The matrix, from `bakeoff.json` (receipt #412, canary run 43611823532), as TP/FP/FN, precision,
recall, F1:

- trivy 2/0/7, 1.0, 0.2222, 0.3636
- grype 2/0/7, 1.0, 0.2222, 0.3636
- osv-scanner 2/0/7, 1.0, 0.2222, 0.3636
- gitleaks 2/0/7, 1.0, 0.2222, 0.3636
- semgrep 3/2/6, 0.6, 0.3333, 0.4286

Read per class, the overall recall hides that each tool is a specialist. The three dependency scanners each found
both pins and nothing else: 2 of 2 in their class, but 13 (Trivy), 21 (Grype) and 27 (OSV-Scanner, which writes
almost every advisory twice) results collapse to the same two defects. gitleaks found 2 of 3 credentials (C01 in
`backup.sh`, C06 in `search.py`) with no false positive, and missed C05, the SMTP password in `mailer.py`: a
human-chosen password with no vendor prefix, which none of its rules matched. Semgrep is the only tool that saw code
defects - A09 (`rules_loader.py`) and A11 (`sla_formula.py`) - and it also caught C06 through a CWE-798 rule; but 2 of
its 5 results are decoys: SHA-1 in `etag.py` line 7, which computes an HTTP ETag (a content fingerprint, not a
security control), and an f-string `ORDER BY` in `columns.py` line 11, where the column comes from a fixed
allow-list and the value is bound. Both look exactly like real defects; only the key tells them apart, the same
trap as `fingerprint.py` in the practice set.

What surprised me: the three SCA tools are indistinguishable on this set, so running all three as gates would
triple the triage work for no extra defect; and Trivy, which also runs a secret scanner, reported none of the three
credentials that gitleaks and Semgrep saw.

Nothing found three defects: A03 (`attachment_read.py` 9-10, `os.path.join` with a file name from the request
path), A16 (`webhook_relay.py` 7, `requests.post` to a customer-supplied URL) and C05. They have the same thing in
common: the dangerous part is where the value comes from, not the call itself. `os.path.join` and a `requests.post`
with a timeout are innocent on their own, and pattern rules of `p/default` cannot know that `filename` or
`callback_url` are attacker-controlled. Finding them needs taint tracking or rules written for this service, like
the two in `semgrep/rules.yml`.

**What I would put in a gate.** Trivy on dependency files stays a gate: precision 1.0 and a 2-of-2 class recall,
and one SCA gate is enough; Grype and OSV-Scanner stay report-only, as a cross-check of a second advisory database
(they cost triage time and found nothing Trivy missed). gitleaks stays a gate: precision 1.0, and the cost of a
missed credential is higher than of a blocked push; its 2-of-3 recall on credentials is why a second secret check
(Semgrep's CWE-798 rules) is worth keeping as a report. Semgrep `p/default` does not become a gate: at precision
0.6, two of five alerts would have blocked correct code - an alert-fatigue generator. Its individual rules that
were right here (deserialization, `eval`) could be promoted one by one once they show no false positives on our
own code.

Two cautions. Every recall above is an upper bound: these are seeded defects, short modules written to be found,
and studies of injected defects find detection rates several times higher than on real ones. And precision is the
only place decoys appear - there is no true-negative cell - so a tool that is silent on the two decoy modules
earns nothing for it, while one that flags them pays in precision.
