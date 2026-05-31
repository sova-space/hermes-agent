#!/usr/bin/env python3
"""
Build docs/index.html from docs/index.md (content) + docs/template.html (design).

Usage:
    python docs/build.py

Dependencies:
    pip install python-frontmatter
"""
import pathlib
import sys

try:
    import frontmatter
except ImportError:
    sys.exit("Missing dependency: pip install python-frontmatter")

ROOT = pathlib.Path(__file__).parent


def highlight_code(code: str, env: bool = False) -> str:
    """Apply simple syntax highlighting to code blocks."""
    lines = []
    for line in code.splitlines():
        if env and "=" in line:
            key, _, val = line.partition("=")
            lines.append(
                f'<span class="kw">{key}</span>='
                f'<span class="val">{val}</span>'
            )
        else:
            # highlight first word if it looks like a command keyword
            parts = line.split(" ", 1)
            if parts[0] in ("git", "cd", "railway", "docker", "pip", "uv"):
                rest = f" {parts[1]}" if len(parts) > 1 else ""
                lines.append(f'<span class="kw">{parts[0]}</span>{rest}')
            else:
                lines.append(line)
    return "\n".join(lines)


def render(d: dict) -> str:
    github = d["github"]

    # ── Hero badges ──────────────────────────────────────────────────────────
    hero_badges = "".join(
        f'<span class="badge">{b}</span>' for b in d["hero_badges"]
    )

    # ── Bot mockup accounts ──────────────────────────────────────────────────
    bot_accounts = "".join(
        f'<div class="account-row">'
        f'<span class="account-name">{a["name"]}</span>'
        f'<span class="account-amount">{a["amount"]}</span>'
        f'</div>'
        for a in d["bot_accounts"]
    )

    # ── Stats bar ─────────────────────────────────────────────────────────────
    stats_items = "".join(
        f'<div style="text-align:center;">'
        f'<div style="font-size:clamp(1.5rem,3vw,2rem);font-weight:800;'
        f'color:{s["color"]};font-family:var(--font-mono)">{s["value"]}</div>'
        f'<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;'
        f'letter-spacing:0.05em;text-transform:uppercase;">{s["label"]}</div>'
        f'</div>'
        for s in d["stats"]
    )

    # ── Feature cards ─────────────────────────────────────────────────────────
    features_grid = "".join(
        f'<div class="feature-card">'
        f'<div class="feature-icon">{f["icon"]}</div>'
        f'<div class="feature-title">{f["title"]}</div>'
        f'<div class="feature-desc">{f["desc"]}</div>'
        f'</div>'
        for f in d["features"]
    )

    # ── Pocket bars ───────────────────────────────────────────────────────────
    pockets_visual = "".join(
        f'<div class="pocket" data-pct="{p["pct"]}" data-color="{p["grad_from"]}" '
        f'data-delay="{p["delay"]}">'
        f'<div class="pocket-pct"'
        f'{" style=\"color:" + p["grad_from"] + "\"" if p.get("overspent") else ""}>'
        f'{p["pct"]}%</div>'
        f'<div class="pocket-bar-wrap">'
        f'<div class="pocket-fill" style="background:linear-gradient(180deg,{p["grad_from"]},{p["grad_to"]})"></div>'
        f'</div>'
        f'<div class="pocket-amount">{p["amount"]}</div>'
        f'<div class="pocket-emoji">{p["emoji"]}</div>'
        f'<div class="pocket-label">{p["label"]}</div>'
        f'</div>'
        for p in d["pockets"]
    )

    pocket_transfer = (
        f'<div style="text-align:center;">'
        f'<div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;'
        f'text-transform:uppercase;letter-spacing:0.08em;">From</div>'
        f'<div style="background:{d["pocket_from_bg"]};border:0.5px solid {d["pocket_from_border"]};'
        f'border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;color:{d["pocket_from_color"]};">'
        f'{d["pocket_from_label"]}</div>'
        f'</div>'
        f'<div style="font-size:20px;color:var(--accent-blue)">→</div>'
        f'<div style="text-align:center;">'
        f'<div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;'
        f'text-transform:uppercase;letter-spacing:0.08em;">To</div>'
        f'<div style="background:{d["pocket_to_bg"]};border:0.5px solid {d["pocket_to_border"]};'
        f'border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;color:{d["pocket_to_color"]};">'
        f'{d["pocket_to_label"]}</div>'
        f'</div>'
    )

    # ── Finance checklist ─────────────────────────────────────────────────────
    finance_checklist = "".join(
        f'<li><span class="check-icon">✓</span> {item}</li>'
        for item in d["finance_checklist"]
    )

    # ── Daily digest mockup ───────────────────────────────────────────────────
    digest_rows = (
        f'<div class="account-row">'
        f'<span class="account-name">Balance</span>'
        f'<span style="color:var(--accent-green)">{d["digest_balance"]}</span>'
        f'</div>'
        f'<div class="account-row">'
        f'<span class="account-name">Spent today</span>'
        f'<span style="color:#f5c842">{d["digest_spent_today"]}</span>'
        f'</div>'
        f'<div class="account-row">'
        f'<span class="account-name">Forecast</span>'
        f'<span style="color:var(--text-primary)">{d["digest_forecast"]}</span>'
        f'</div>'
        f'<hr class="divider-line">'
        f'<div class="account-row" style="font-size:12px">'
        f'<span class="account-name">{d["digest_pocket_alert"]}</span>'
        f'<span style="color:#ff5555">32% left</span>'
        f'</div>'
        f'<div class="account-row" style="font-size:12px">'
        f'<span class="account-name">{d["digest_debt_alert"]}</span>'
        f'<span style="color:#ff5555">due in 2 days</span>'
        f'</div>'
    )

    # ── Couple pockets ────────────────────────────────────────────────────────
    def mini_pockets(items: list) -> str:
        return "".join(
            f'<div class="mini-pocket">'
            f'<div class="mini-pocket-header">'
            f'<span class="mini-pocket-name">{p["name"]}</span>'
            f'<span class="mini-pocket-pct">{p["pct"]}%</span>'
            f'</div>'
            f'<div class="mini-bar">'
            f'<div class="mini-fill" data-w="{p["pct"]}" style="background:{p["color"]}"></div>'
            f'</div>'
            f'</div>'
            for p in items
        )

    couple_your = mini_pockets(d["your_pockets"])
    couple_shared = mini_pockets(d["shared_pockets"])

    # ── Setup steps ───────────────────────────────────────────────────────────
    def render_step(step: dict) -> str:
        inner = f'<div class="step-title">{step["title"]}</div>'
        if step.get("desc"):
            inner += f'<div class="step-desc">{step["desc"]}</div>'
        if step.get("code"):
            code = step["code"].replace("{github}", github)
            highlighted = highlight_code(code, env=step.get("code_env", False))
            inner += f'<pre>{highlighted}</pre>'
        return (
            f'<div class="step reveal">'
            f'<div class="step-num">{step["num"]}</div>'
            f'<div>{inner}</div>'
            f'</div>'
        )

    setup_steps = "".join(render_step(s) for s in d["setup_steps"])

    # ── OSS cards ─────────────────────────────────────────────────────────────
    oss_cards = "".join(
        f'<div class="oss-card" style="flex:1;">'
        f'<div class="oss-icon">{c["icon"]}</div>'
        f'<div class="oss-title">{c["title"]}</div>'
        f'<div class="oss-desc">{c["desc"]}</div>'
        f'</div>'
        for c in d["oss_cards"]
    )

    # ── Footer links ──────────────────────────────────────────────────────────
    footer_links = "".join(
        f'<a href="{lnk["href"].replace("{github}", github)}">{lnk["label"]}</a>'
        for lnk in d["footer_links"]
    )

    footer_credit = d["footer_credit"].replace("{github}", github)

    # ── Assemble all substitutions ────────────────────────────────────────────
    subs = {
        "PAGE_TITLE":          d["page_title"],
        "OG_TITLE":            d["og_title"],
        "OG_DESCRIPTION":      d["og_description"],
        "OG_IMAGE":            d["og_image"],
        "META_DESCRIPTION":    d["meta_description"],
        "GITHUB_URL":          github,
        "HERO_TAG":            d["hero_tag"],
        "HERO_H1":             d["hero_h1"],
        "HERO_SUBTITLE":       d["hero_subtitle"],
        "HERO_BADGES":         hero_badges,
        "BOT_ACCOUNTS":        bot_accounts,
        "BOT_LAST_SYNCED":     d["bot_last_synced"],
        "STATS_ITEMS":         stats_items,
        "FEATURES_TAG":        d["features_tag"],
        "FEATURES_TITLE":      d["features_title"],
        "FEATURES_SUBTITLE":   d["features_subtitle"],
        "FEATURES_GRID":       features_grid,
        "POCKETS_TAG":         d["pockets_tag"],
        "POCKETS_TITLE":       d["pockets_title"],
        "POCKETS_SUBTITLE":    d["pockets_subtitle"],
        "POCKETS_VISUAL":      pockets_visual,
        "POCKET_TRANSFER":     pocket_transfer,
        "POCKET_MOVE_AMOUNT":  d["pocket_move_amount"],
        "POCKETS_HINT":        d["pockets_hint"],
        "FINANCE_TAG":         d["finance_tag"],
        "FINANCE_TITLE":       d["finance_title"],
        "FINANCE_SUBTITLE":    d["finance_subtitle"],
        "FINANCE_CHECKLIST":   finance_checklist,
        "DIGEST_ROWS":         digest_rows,
        "COUPLE_TAG":          d["couple_tag"],
        "COUPLE_TITLE":        d["couple_title"],
        "COUPLE_SUBTITLE":     d["couple_subtitle"],
        "COUPLE_YOUR_POCKETS": couple_your,
        "COUPLE_SHARED_POCKETS": couple_shared,
        "COUPLE_CAPTION":      d["couple_caption"],
        "SETUP_TAG":           d["setup_tag"],
        "SETUP_TITLE":         d["setup_title"],
        "SETUP_SUBTITLE":      d["setup_subtitle"],
        "SETUP_STEPS":         setup_steps,
        "OSS_TAG":             d["oss_tag"],
        "OSS_TITLE":           d["oss_title"],
        "OSS_SUBTITLE":        d["oss_subtitle"],
        "OSS_CARDS":           oss_cards,
        "CTA_TITLE":           d["cta_title"],
        "CTA_SUBTITLE":        d["cta_subtitle"],
        "FOOTER_LINKS":        footer_links,
        "FOOTER_CREDIT":       footer_credit,
    }

    template = (ROOT / "template.html").read_text()
    for key, val in subs.items():
        template = template.replace("{{" + key + "}}", val)

    return template


def main() -> None:
    post = frontmatter.load(ROOT / "index.md")
    html = render(post.metadata)
    out = ROOT / "index.html"
    out.write_text(html)
    print(f"Built {out}")


if __name__ == "__main__":
    main()
