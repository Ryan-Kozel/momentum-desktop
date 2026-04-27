"""Small shared utilities for the views."""
from __future__ import annotations


def fmt_time(t: str | None) -> str:
    """'HH:MM' 24h -> compact 12h like '6:30a', '12p', '5p'. None/empty -> ''."""
    if not t:
        return ""
    try:
        h, m = map(int, t.split(":"))
    except (ValueError, AttributeError):
        return t
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return t
    ap = "a" if h < 12 else "p"
    h12 = h % 12 or 12
    if m == 0:
        return f"{h12}{ap}"
    return f"{h12}:{m:02d}{ap}"


def fmt_shift(shift: dict) -> str:
    """Compact summary for calendar cells: 'CC 6:30a-12p' or 'CC 6-12p'."""
    label = shift.get("label") or ""
    s = fmt_time(shift.get("start_time"))
    e = fmt_time(shift.get("end_time"))
    if s and e:
        # Drop am/pm on start if it matches end's am/pm (tighter display)
        if s[-1] == e[-1]:
            s_compact = s[:-1]
        else:
            s_compact = s
        return f"{label} {s_compact}-{e}".strip()
    if s:
        return f"{label} {s}".strip()
    return label


def parse_time(s: str) -> str | None:
    """Accept '6:30', '6:30am', '18:30', '6', '6a', '6pm' -> 'HH:MM' 24h. None on fail."""
    if not s:
        return None
    s = s.strip().lower().replace(" ", "")
    if not s:
        return None

    # Strip am/pm suffix
    ampm = None
    if s.endswith(("am", "a")):
        ampm = "am"
        s = s.rstrip("am")
    elif s.endswith(("pm", "p")):
        ampm = "pm"
        s = s.rstrip("pm")

    # Parse hh or hh:mm
    if ":" in s:
        try:
            h_str, m_str = s.split(":", 1)
            h = int(h_str)
            m = int(m_str)
        except ValueError:
            return None
    else:
        try:
            h = int(s)
            m = 0
        except ValueError:
            return None

    if not (0 <= m <= 59):
        return None

    # Apply am/pm
    if ampm == "am":
        if h == 12:
            h = 0
        elif not (1 <= h <= 12):
            return None
    elif ampm == "pm":
        if h == 12:
            pass
        elif 1 <= h <= 11:
            h += 12
        else:
            return None
    else:
        # 24h format
        if not (0 <= h <= 23):
            return None

    return f"{h:02d}:{m:02d}"
