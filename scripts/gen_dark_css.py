"""Generate frontend/src/DarkAuto.css — dark-mode overrides for every light colour
used in the app stylesheets. Re-run after changing any stylesheet:

    python3 /app/scripts/gen_dark_css.py

Hand-written dark tweaks live in frontend/src/Dark.css (imported after this file).
"""
import re
from pathlib import Path

SRC = Path("/app/frontend/src")
FILES = ["index.css", "App.css", "Fixes.css", "Card.css", "Extras.css", "Ops.css", "Portal.css",
         "Visitors.css", "Lanjutan.css", "Theme.css"]
# :where() keeps each override at the same specificity as its light original,
# so the original cascade (generic vs specific rules) is preserved in dark mode.
PREFIX = ':where(html[data-theme="dark"])'

# Selectors that must keep their light look (paper previews, logos, knobs, cards on gradients)
SKIP = ["banner-button", "id-qr", "chooser-head img", "back-head", ".switch span", "cam-switch",
        "print-sheet", "bulk-print", "id-card", "lb-hero", "print-header", "student-hero-badge",
        "lb-avatar", "cam-cooldown", "visit-cam-bar", "shelf-spine span", "swatch", "logo-img",
        "login-logos", "card-logo", "theme-"]

SURFACE, SURFACE2, SUNK = "var(--surface)", "var(--surface-2)", "var(--sunk)"
BG = {
    "#fff": SURFACE, "#ffffff": SURFACE, "white": SURFACE, "#ffffffe6": "rgba(26,22,48,.92)",
    "#f8fafc": SURFACE2, "#f7f7fb": SURFACE2, "#faf9ff": "rgba(139,92,246,.07)", "#faf8ff": "rgba(139,92,246,.08)",
    "#f1f5f9": SUNK, "#f1f0f7": SUNK, "#e2e8f0": SUNK, "#cbd5e1": "#3a3460",
    "#f5f3ff": "rgba(139,92,246,.14)", "#ede9fe": "rgba(139,92,246,.2)", "#ddd6fe": "rgba(139,92,246,.3)",
    "var(--v50)": "rgba(139,92,246,.12)", "var(--v100)": "rgba(139,92,246,.2)",
    "#dcfce7": "rgba(34,197,94,.16)", "#f0fdf4": "rgba(34,197,94,.1)", "#ecfdf5": "rgba(34,197,94,.1)", "#d1fae5": "rgba(34,197,94,.2)",
    "#fef3c7": "rgba(245,158,11,.16)", "#fffbeb": "rgba(245,158,11,.1)", "#fff7ed": "rgba(249,115,22,.1)", "#ffedd5": "rgba(249,115,22,.16)",
    "#fee2e2": "rgba(239,68,68,.16)", "#fef2f2": "rgba(239,68,68,.1)", "#ffe4e6": "rgba(244,63,94,.16)",
    "#f0fdfa": "rgba(20,184,166,.12)", "#eff6ff": "rgba(139,92,246,.14)",
}
BORDER = {
    "#e2e8f0": "var(--line)", "#e9e8f3": "var(--line)", "#f1f5f9": "var(--line)", "#f1f0f7": "var(--line)",
    "#cbd5e1": "var(--line-strong)", "#dcdbea": "var(--line-strong)", "#fff": "var(--surface)",
    "#ddd6fe": "rgba(167,139,250,.35)", "#c4b5fd": "rgba(167,139,250,.45)", "#bfdbfe": "rgba(167,139,250,.35)",
    "#93c5fd": "rgba(167,139,250,.45)", "var(--v100)": "rgba(167,139,250,.25)", "var(--v200)": "rgba(167,139,250,.4)",
    "#bbf7d0": "rgba(34,197,94,.35)", "#a7f3d0": "rgba(34,197,94,.35)", "#86efac": "rgba(34,197,94,.45)",
    "#fde68a": "rgba(245,158,11,.35)", "#fcd34d": "rgba(245,158,11,.45)", "#fed7aa": "rgba(249,115,22,.35)",
    "#fecaca": "rgba(239,68,68,.35)", "#fca5a5": "rgba(239,68,68,.45)",
}
TEXT = {
    "#0f172a": "var(--ink)", "#16132b": "var(--ink)", "#1e293b": "var(--ink)", "#2e1065": "var(--ink)",
    "#334155": "var(--ink-2)", "#3b3854": "var(--ink-2)", "#475569": "var(--ink-2)",
    "#64748b": "var(--muted)", "#6b6880": "var(--muted)",
    "#7c3aed": "#a78bfa", "#6d28d9": "#c4b5fd", "#5b21b6": "#c4b5fd", "#4c1d95": "#ddd6fe",
    "var(--v600)": "#a78bfa", "var(--v700)": "#c4b5fd", "var(--v800)": "#ddd6fe", "var(--v900)": "#ede9fe", "var(--v950)": "#ede9fe",
    "#15803d": "#4ade80", "#16a34a": "#4ade80", "#047857": "#34d399", "#4d7c0f": "#a3e635",
    "#b45309": "#fbbf24", "#a16207": "#fcd34d", "#92400e": "#fcd34d", "#9a3412": "#fdba74", "#c2410c": "#fdba74",
    "#7c2d12": "#fed7aa", "#d97706": "#fbbf24",
    "#b91c1c": "#f87171", "#dc2626": "#f87171", "#be123c": "#fb7185",
    "#1d4ed8": "#c4b5fd", "#0d9488": "#2dd4bf", "#0369a1": "#7dd3fc",
}
SHADOW_TINT = {"#d1fae5": "rgba(16,185,129,.25)", "#fee2e2": "rgba(239,68,68,.25)"}

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b|var\(--v\d+\)|\bwhite\b")


def map_value(prop, value):
    if "gradient" in value or "url(" in value:
        return None
    p = prop.strip().lower()
    if p in ("background", "background-color"):
        table = BG
    elif p == "color":
        table = TEXT
    elif p.startswith("border") or p.startswith("outline"):
        table = BORDER
    elif p == "box-shadow":
        table = SHADOW_TINT
    else:
        return None
    changed = False

    def sub(m):
        nonlocal changed
        tok = m.group(0).lower()
        if tok in table:
            changed = True
            return table[tok]
        return m.group(0)

    out = HEX.sub(sub, value)
    return out if changed else None


def prefix_selector(sel):
    parts = [s.strip() for s in sel.split(",") if s.strip()]
    res = []
    for s in parts:
        if any(k in s for k in SKIP):
            continue
        if s in (":root", "html"):
            continue
        if s == "body":
            res.append(f"{PREFIX} body")
        else:
            res.append(f"{PREFIX} {s}")
    return ",".join(res)


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse(css, media=None, out=None):
    """Very small CSS walker: handles rules, @media (nested once), skips @keyframes/@import/@page."""
    out = [] if out is None else out
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            break
        head = css[i:j].strip()
        # find matching brace
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if head.startswith("@import"):
            head = head.split(";")[-1].strip()
        if head.startswith("@media"):
            q = head[len("@media"):].strip()
            if "print" not in q:
                parse(body, q, out)
        elif head.startswith("@"):
            pass
        elif head:
            decls = []
            for d in body.split(";"):
                if ":" not in d:
                    continue
                prop, val = d.split(":", 1)
                imp = "!important" in val
                v = val.replace("!important", "").strip()
                nv = map_value(prop, v)
                if nv:
                    decls.append(f"{prop.strip()}:{nv}{'!important' if imp else ''}")
            sel = prefix_selector(head)
            if decls and sel:
                out.append((media, f"{sel}{{{';'.join(decls)}}}"))
        i = k
    return out


def main():
    lines = ["/* AUTO-GENERATED by /app/scripts/gen_dark_css.py — do not edit by hand. */", "@media screen{"]
    for f in FILES:
        css = strip_comments((SRC / f).read_text())
        rules = parse(css)
        if not rules:
            continue
        lines.append(f"/* {f} */")
        for media, rule in rules:
            lines.append(f"@media {media}{{{rule}}}" if media else rule)
    lines.append("}")
    (SRC / "DarkAuto.css").write_text("\n".join(lines) + "\n")
    print("rules:", len(lines) - 3)


if __name__ == "__main__":
    main()
