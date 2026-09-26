# ai-generated: 85% - Claude Code drafted the implementation against METRIC-SPEC.md sections 1-6, reviewed by the author

"""POST /dora/metrics: a pure function of its request body (METRIC-SPEC.md section 6).

Parses and validates a JSON Lines-shaped event log, applies the window (R-02) and the six edge-case
rules (R-06 to R-13), and returns the five DORA metrics plus counts, anomalies and ground truth.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from .exceptions import ValidationFailed
from .timeutil import fmt_instant, parse_instant

SPEC_VERSION = "1.0.0"


@dataclass
class _Commit:
    sha: str
    branch: str
    change_id: Optional[str]
    reverts: Optional[str]
    at: datetime


@dataclass
class _Deployment:
    deployment_id: str
    environment: str
    outcome: str
    commits: list
    unplanned: bool
    caused_by: Optional[str]
    at: datetime


@dataclass
class _Incident:
    incident_id: str
    phase: str
    deployment_ids: list
    at: datetime


def _round(value: float, ndigits: int):
    q = Decimal(1).scaleb(-ndigits)
    d = Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if ndigits == 0 else float(d)


def _median(values: list) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _clamped_seconds(later: datetime, earlier: datetime) -> tuple:
    """R-03: a negative duration is clamped to zero. Returns (seconds, was_negative)."""
    delta = (later - earlier).total_seconds()
    if delta < 0:
        return 0.0, True
    return delta, False


def _parse_window(payload: dict) -> tuple:
    window = payload.get("window")
    if not isinstance(window, dict) or "from" not in window or "to" not in window:
        raise ValidationFailed("window is required with from and to")
    try:
        start = parse_instant(window["from"])
        end = parse_instant(window["to"])
    except (ValueError, TypeError):
        raise ValidationFailed("window.from and window.to must be RFC 3339 instants")
    if not end > start:
        raise ValidationFailed("window.to must be after window.from")
    return start, end


def _require_str(raw: dict, key: str, event_id) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationFailed(f"event {event_id!r}: {key} must be a non-empty string")
    return value


def _parse_commit(raw: dict, at: datetime, event_id: str) -> _Commit:
    sha = _require_str(raw, "sha", event_id)
    branch = raw.get("branch")
    if not isinstance(branch, str):
        raise ValidationFailed(f"event {event_id!r}: branch must be a string")
    change_id = raw.get("change_id")
    reverts = raw.get("reverts")
    if reverts is not None and not isinstance(reverts, str):
        raise ValidationFailed(f"event {event_id!r}: reverts must be a sha or null")
    if reverts is None:
        if not isinstance(change_id, str) or not change_id:
            raise ValidationFailed(f"event {event_id!r}: change_id is required when reverts is null")
    elif change_id is not None:
        raise ValidationFailed(f"event {event_id!r}: change_id must be null when reverts is set")
    return _Commit(sha=sha, branch=branch, change_id=change_id, reverts=reverts, at=at)


def _parse_deployment(raw: dict, at: datetime, event_id: str) -> _Deployment:
    deployment_id = _require_str(raw, "deployment_id", event_id)
    environment = raw.get("environment")
    if not isinstance(environment, str):
        raise ValidationFailed(f"event {event_id!r}: environment must be a string")
    outcome = raw.get("outcome")
    if outcome not in ("success", "failure"):
        raise ValidationFailed(f"event {event_id!r}: outcome must be success or failure")
    commits = raw.get("commits")
    if not isinstance(commits, list) or not all(isinstance(s, str) for s in commits):
        raise ValidationFailed(f"event {event_id!r}: commits must be an array of shas")
    unplanned = raw.get("unplanned")
    if not isinstance(unplanned, bool):
        raise ValidationFailed(f"event {event_id!r}: unplanned must be a boolean")
    caused_by = raw.get("caused_by")
    if caused_by is not None and not isinstance(caused_by, str):
        raise ValidationFailed(f"event {event_id!r}: caused_by must be an incident_id or null")
    return _Deployment(
        deployment_id=deployment_id, environment=environment, outcome=outcome,
        commits=commits, unplanned=unplanned, caused_by=caused_by, at=at,
    )


def _parse_incident(raw: dict, at: datetime, event_id: str) -> _Incident:
    incident_id = _require_str(raw, "incident_id", event_id)
    phase = raw.get("phase")
    if phase not in ("opened", "resolved"):
        raise ValidationFailed(f"event {event_id!r}: phase must be opened or resolved")
    deployment_ids = raw.get("deployments")
    if not isinstance(deployment_ids, list) or not all(isinstance(s, str) for s in deployment_ids):
        raise ValidationFailed(f"event {event_id!r}: deployments must be an array of deployment_ids")
    return _Incident(incident_id=incident_id, phase=phase, deployment_ids=deployment_ids, at=at)


def _parse_events(payload: dict) -> tuple:
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValidationFailed("events must be an array")
    commits, deployments, incidents = [], [], []
    seen_ids = set()
    for raw in events:
        if not isinstance(raw, dict):
            raise ValidationFailed("every event must be an object")
        event_id = raw.get("event_id")
        if not isinstance(event_id, str) or not (1 <= len(event_id) <= 64):
            raise ValidationFailed("event_id must be a string of 1..64 characters")
        if event_id in seen_ids:
            continue  # R-05: first occurrence wins, later duplicates are not an error
        seen_ids.add(event_id)
        etype = raw.get("type")
        at_raw = raw.get("at")
        try:
            at = parse_instant(at_raw) if isinstance(at_raw, str) else None
        except ValueError:
            at = None
        if at is None:
            raise ValidationFailed(f"event {event_id!r}: at must be an RFC 3339 instant")
        if etype == "commit":
            commits.append(_parse_commit(raw, at, event_id))
        elif etype == "deployment":
            deployments.append(_parse_deployment(raw, at, event_id))
        elif etype == "incident":
            incidents.append(_parse_incident(raw, at, event_id))
        else:
            raise ValidationFailed(f"event {event_id!r}: type must be commit, deployment or incident")
    return commits, deployments, incidents


def _check_well_formed(commits: list, deployments: list, incidents: list) -> dict:
    commit_by_sha = {}
    for c in commits:
        if c.sha in commit_by_sha:
            raise ValidationFailed(f"duplicate commit sha {c.sha!r}")
        commit_by_sha[c.sha] = c
    for c in commits:
        if c.reverts is not None and c.reverts not in commit_by_sha:
            raise ValidationFailed(f"commit reverts unknown sha {c.reverts!r}")
    incident_ids = {i.incident_id for i in incidents}
    for d in deployments:
        for sha in d.commits:
            if sha not in commit_by_sha:
                raise ValidationFailed(f"deployment {d.deployment_id!r} references unknown sha {sha!r}")
        if d.caused_by is not None and d.caused_by not in incident_ids:
            raise ValidationFailed(f"deployment {d.deployment_id!r} references unknown incident {d.caused_by!r}")
    deployment_ids = {d.deployment_id for d in deployments}
    for i in incidents:
        for dep_id in i.deployment_ids:
            if dep_id not in deployment_ids:
                raise ValidationFailed(f"incident {i.incident_id!r} references unknown deployment {dep_id!r}")
    opened, resolved = set(), set()
    for i in incidents:
        bucket = opened if i.phase == "opened" else resolved
        if i.incident_id in bucket:
            raise ValidationFailed(f"incident {i.incident_id!r} carries phase {i.phase!r} twice")
        bucket.add(i.incident_id)
    for incident_id in resolved:
        if incident_id not in opened:
            raise ValidationFailed(f"incident {incident_id!r} resolved without being opened")
    return commit_by_sha


def _resolve_change_ids(commits: list, commit_by_sha: dict) -> dict:
    cache: dict = {}

    def resolve(sha: str, trail: set):
        if sha in cache:
            return cache[sha]
        if sha in trail:
            raise ValidationFailed(f"commit {sha!r} is part of a revert cycle")
        commit = commit_by_sha[sha]
        if commit.reverts is None:
            result = commit.change_id
        else:
            result = resolve(commit.reverts, trail | {sha})
        cache[sha] = result
        return result

    return {c.sha: resolve(c.sha, set()) for c in commits}


def _covering_incident(deployment_id: str, incident_opened_at: dict, incident_deployments: dict):
    candidates = [
        iid for iid, deps in incident_deployments.items()
        if deployment_id in deps and iid in incident_opened_at
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda iid: (incident_opened_at[iid], iid))  # earliest opened, then lowest id (R-12)
    return candidates[0]


def compute_metrics(payload: dict) -> dict:
    window_from, window_to = _parse_window(payload)
    commits, deployments, incidents = _parse_events(payload)
    commit_by_sha = _check_well_formed(commits, deployments, incidents)
    change_id_of = _resolve_change_ids(commits, commit_by_sha)

    incident_deployments: dict = {}
    incident_opened_at: dict = {}
    incident_resolved_at: dict = {}
    for i in incidents:
        incident_deployments.setdefault(i.incident_id, set()).update(i.deployment_ids)
        if i.phase == "opened":
            incident_opened_at[i.incident_id] = i.at
        else:
            incident_resolved_at[i.incident_id] = i.at

    production = [d for d in deployments if d.environment == "production"]
    inwindow = [d for d in production if window_from <= d.at < window_to]  # R-01 + R-02
    successful = [d for d in inwindow if d.outcome == "success"]
    failed = [d for d in inwindow if d.outcome == "failure"]

    window_days = (window_to - window_from).total_seconds() / 86400
    frequency = len(inwindow) / window_days

    deployments_without_commits = sum(1 for d in inwindow if not d.commits)  # E4

    shas_inwindow = set()
    for d in inwindow:
        shas_inwindow.update(d.commits)
    commits_never_on_main = sum(  # E3: any outcome, any in-window production deployment
        1 for sha in shas_inwindow if commit_by_sha[sha].branch != "main"
    )

    first_successful_deploy_for_sha: dict = {}
    for d in successful:
        for sha in d.commits:
            current = first_successful_deploy_for_sha.get(sha)
            if current is None or d.at < current.at:
                first_successful_deploy_for_sha[sha] = d

    lead_times = []
    negative_lead_time_pairs = 0
    for sha, dep in first_successful_deploy_for_sha.items():
        seconds, was_negative = _clamped_seconds(dep.at, commit_by_sha[sha].at)  # E1
        if was_negative:
            negative_lead_time_pairs += 1
        lead_times.append(seconds)
    change_lead_time_seconds_p50 = _median(lead_times)

    recovered_times = []
    open_failures = 0
    for d in failed:
        covering = _covering_incident(d.deployment_id, incident_opened_at, incident_deployments)
        if covering is None or covering not in incident_resolved_at:
            open_failures += 1  # E5
            continue
        seconds, _ = _clamped_seconds(incident_resolved_at[covering], d.at)
        recovered_times.append(seconds)
    failed_deployment_recovery_time_seconds_p50 = _median(recovered_times)

    overlap_ids = list(incident_opened_at.keys())
    overlapping_incident_pairs = 0
    for a_idx in range(len(overlap_ids)):
        a_start = incident_opened_at[overlap_ids[a_idx]]
        a_end = incident_resolved_at.get(overlap_ids[a_idx], window_to)  # E6: unresolved ends at window.to
        for b_idx in range(a_idx + 1, len(overlap_ids)):
            b_start = incident_opened_at[overlap_ids[b_idx]]
            b_end = incident_resolved_at.get(overlap_ids[b_idx], window_to)
            if a_start < b_end and b_start < a_end:
                overlapping_incident_pairs += 1

    rework_deployments = sum(1 for d in inwindow if d.unplanned and d.caused_by is not None)

    change_fail_rate = _round(len(failed) / len(inwindow), 6) if inwindow else None
    deployment_rework_rate = _round(rework_deployments / len(inwindow), 6) if inwindow else None

    change_first_commit_at: dict = {}
    for c in commits:
        cid = change_id_of[c.sha]
        current = change_first_commit_at.get(cid)
        if current is None or c.at < current:
            change_first_commit_at[cid] = c.at

    delivered_first_deploy_at: dict = {}
    for d in successful:
        for sha in d.commits:
            cid = change_id_of[sha]
            current = delivered_first_deploy_at.get(cid)
            if current is None or d.at < current:
                delivered_first_deploy_at[cid] = d.at

    true_lead_times = []
    for cid, deploy_at in delivered_first_deploy_at.items():
        seconds, _ = _clamped_seconds(deploy_at, change_first_commit_at[cid])
        true_lead_times.append(seconds)
    true_change_lead_time_seconds_p50 = _median(true_lead_times)

    return {
        "spec_version": SPEC_VERSION,
        "window": {"from": fmt_instant(window_from), "to": fmt_instant(window_to)},
        "deployment_frequency_per_day": _round(frequency, 6),
        "change_lead_time_seconds_p50": (
            _round(change_lead_time_seconds_p50, 0) if change_lead_time_seconds_p50 is not None else None
        ),
        "failed_deployment_recovery_time_seconds_p50": (
            _round(failed_deployment_recovery_time_seconds_p50, 0)
            if failed_deployment_recovery_time_seconds_p50 is not None else None
        ),
        "change_fail_rate": change_fail_rate,
        "deployment_rework_rate": deployment_rework_rate,
        "counts": {
            "deployments": len(inwindow),
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovered_times),
            "open_failures": open_failures,
            "rework_deployments": rework_deployments,
            "lead_time_pairs": len(lead_times),
            "changes": len(set(change_id_of.values())),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_time_pairs,
            "deployments_without_commits": deployments_without_commits,
            "commits_never_on_main": commits_never_on_main,
            "revert_chains_collapsed": sum(1 for c in commits if c.reverts is not None),
            "overlapping_incident_pairs": overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered": len(delivered_first_deploy_at),
            "true_change_lead_time_seconds_p50": (
                _round(true_change_lead_time_seconds_p50, 0)
                if true_change_lead_time_seconds_p50 is not None else None
            ),
        },
    }
