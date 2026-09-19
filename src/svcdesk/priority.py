# ai-generated: 90% - Claude Code drafted, reviewed by the author

"""Priority matrix (docs/API.md section 3) and the C3 = vip resolution (DECISIONS.md)."""

_MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}

_ORDER = ["P1", "P2", "P3", "P4"]


def compute_priority(impact: int, urgency: int, vip: bool) -> str:
    base = _MATRIX[(impact, urgency)]
    if not vip:
        return base
    # C3 = vip: a VIP ticket at P3 or P4 is raised to P2; P1 and P2 are unchanged.
    if _ORDER.index(base) > _ORDER.index("P2"):
        return "P2"
    return base
