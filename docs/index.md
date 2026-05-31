---
# ── Meta ──────────────────────────────────────────────────────
page_title: "Sova Family — Personal Finance for Telegram"
og_title: "Sova Family — Personal Finance for Telegram"
og_description: "Connect Monobank, track spending with visual pockets, manage debt, goals and trips — all from a Telegram Mini App. Open source, self-hosted."
og_image: "https://nkhimin.github.io/hermes-agent/assets/logo-main.png"
meta_description: "Connect Monobank, track spending with visual pockets, manage debt, goals and trips — all from a Telegram Mini App. Open source, self-hosted."
github: "https://github.com/nkhimin/hermes-agent"

# ── Hero ──────────────────────────────────────────────────────
hero_tag: "Open Source · Self-hosted · MIT"
hero_h1: "Personal finance<br>for <span>Telegram</span>"
hero_subtitle: "Connect Monobank, track spending with visual pockets, manage debt, goals, and trips — all from a Telegram Mini App."
hero_badges:
  - "Python 3.11+"
  - "PTB 21.x"
  - "FastAPI"
  - "PostgreSQL"
  - "Railway"

# ── Bot mockup ────────────────────────────────────────────────
bot_accounts:
  - name: "💳 Black"
    amount: "12,450.00 UAH"
  - name: "💳 USD card"
    amount: "340.00 USD"
  - name: "💳 Savings"
    amount: "5,800.00 UAH"
bot_last_synced: "4 min ago"

# ── Stats bar ─────────────────────────────────────────────────
stats:
  - value: "Monobank"
    label: "native integration"
    color: "var(--accent-blue)"
  - value: "6 features"
    label: "in one Mini App"
    color: "var(--accent-cyan)"
  - value: "MIT"
    label: "free forever"
    color: "var(--accent-green)"
  - value: "Self-hosted"
    label: "your data, your server"
    color: "var(--accent-blue)"

# ── Features ──────────────────────────────────────────────────
features_tag: "What's inside"
features_title: "Everything your<br>finances need"
features_subtitle: "Six powerful features, one Telegram bot, zero spreadsheets."
features:
  - icon: "🪣"
    title: "Pockets"
    desc: "Visual liquid budget containers. Auto-filled from Monobank transactions by category. Watch them drain as you spend."
  - icon: "💳"
    title: "Balance"
    desc: "/balance shows all accounts and currencies instantly. Synced every hour from Monobank automatically."
  - icon: "💸"
    title: "Debt tracker"
    desc: "Track money you owe with due dates. Get reminded 3 days before payment is due. Never miss a debt."
  - icon: "🎯"
    title: "Goals"
    desc: "Set a savings target and deadline. Progress tracked automatically against your real Monobank balance."
  - icon: "✈️"
    title: "Trips"
    desc: "Set a trip budget with dates. Monobank transactions within that period are auto-tagged. See spent vs budget daily."
  - icon: "📈"
    title: "Forecast"
    desc: "End-of-month estimate based on recurring payments, manual income, and average daily spending."

# ── Pockets ───────────────────────────────────────────────────
pockets_tag: "Pockets system"
pockets_title: "Watch your budget breathe"
pockets_subtitle: "Pockets fill like liquid containers. Drain as you spend. Move funds between pockets with one tap."
pockets_hint: "Overspent on food? <span>Roll with punches — move funds in one tap.</span>"
pockets:
  - emoji: "🍔"
    label: "Food"
    pct: 64
    amount: "₴320 / ₴500"
    grad_from: "#f5c842"
    grad_to: "#d4a200"
    delay: 0
  - emoji: "✈️"
    label: "Travel"
    pct: 85
    amount: "₴850 / ₴1000"
    grad_from: "#4da6ff"
    grad_to: "#1a7acc"
    delay: 100
  - emoji: "🎉"
    label: "Fun"
    pct: 32
    amount: "₴160 / ₴500"
    grad_from: "#a78bfa"
    grad_to: "#7c3aed"
    delay: 200
  - emoji: "🧾"
    label: "Bills"
    pct: 93
    amount: "₴2,790 / ₴3,000"
    grad_from: "#ff5555"
    grad_to: "#cc0000"
    delay: 300
    overspent: true
  - emoji: "💊"
    label: "Health"
    pct: 51
    amount: "₴255 / ₴500"
    grad_from: "#00ff88"
    grad_to: "#00cc66"
    delay: 400
pocket_from_label: "🎉 Fun  ·  ₴160"
pocket_from_bg: "rgba(165,78,250,0.12)"
pocket_from_border: "rgba(165,78,250,0.3)"
pocket_from_color: "#a78bfa"
pocket_to_label: "🍔 Food  ·  ₴320"
pocket_to_bg: "rgba(245,200,66,0.12)"
pocket_to_border: "rgba(245,200,66,0.3)"
pocket_to_color: "#f5c842"
pocket_move_amount: "₴100"

# ── Finance section ───────────────────────────────────────────
finance_tag: "Finance agent"
finance_title: "Sova <span>Finance</span>"
finance_subtitle: "Your Monobank, inside Telegram."
finance_checklist:
  - "Connects to Monobank API with one token"
  - "Syncs accounts and transactions every hour"
  - "Pockets auto-filled by MCC category"
  - "Daily digest pushed at 9:00am"
  - "Debt reminders 3 days before due dates"
  - "End-of-month forecast on the 25th"
digest_balance: "18,590 UAH"
digest_spent_today: "₴340"
digest_forecast: "~₴8,200 by Jun 30"
digest_pocket_alert: "🪣 Fun pocket · 32% left"
digest_debt_alert: "⚠️ Debt to Olena · due in 2 days"

# ── Couple mode ───────────────────────────────────────────────
couple_tag: "Couple mode"
couple_title: "Built for two"
couple_subtitle: "Personal pockets stay private. Shared pockets belong to both of you."
couple_caption: "<strong>Both users see shared pockets.</strong> Personal pockets are yours alone."
your_pockets:
  - name: "🍔 Food"
    pct: 64
    color: "#f5c842"
  - name: "🎉 Fun"
    pct: 32
    color: "#a78bfa"
  - name: "💊 Health"
    pct: 88
    color: "#00ff88"
shared_pockets:
  - name: "🏠 Rent"
    pct: 95
    color: "#ff5555"
  - name: "🛒 Groceries"
    pct: 68
    color: "#4da6ff"
  - name: "⚡ Utilities"
    pct: 51
    color: "#00d4ff"

# ── Setup ─────────────────────────────────────────────────────
setup_tag: "Self-hosted"
setup_title: "Running in 5 steps"
setup_subtitle: "Deploy to Railway with your own Monobank token. Full control, no subscriptions."
setup_steps:
  - num: "01"
    title: "Clone the repo"
    code: "git clone {github}\ncd hermes-agent"
  - num: "02"
    title: "Set environment variables"
    code: "FINANCE_BOT_TOKEN=your_telegram_bot_token\nMONO_TOKEN=your_monobank_token\nGROUP_CHAT_ID=your_telegram_group_id\nMINI_APP_URL=your_mini_app_url"
    code_env: true
  - num: "03"
    title: "Deploy to Railway"
    code: "railway up --detach"
  - num: "04"
    title: "Add bot to Telegram group"
    desc: 'Add @sova_finance_bot to your Telegram forum group as admin with "Post messages" permission.'
  - num: "05"
    title: "Configure topics"
    desc: "Run /setup in the Finance topic. The bot auto-discovers thread IDs and saves them to config."

# ── Open source ───────────────────────────────────────────────
oss_tag: "Open source · MIT"
oss_title: "Built to be extended."
oss_subtitle: "One base class. One config file. One line to add a new agent."
oss_cards:
  - icon: "🔧"
    title: "Extend it"
    desc: "Add agents, connect new banks, build custom topics. BaseAgent is one file to implement."
  - icon: "🤝"
    title: "Contribute"
    desc: "Bug or idea? Open an issue or PR on GitHub. All contributions welcome."

# ── CTA ───────────────────────────────────────────────────────
cta_title: 'Start managing your<br>finances <span style="color:var(--accent-blue)">today</span>'
cta_subtitle: "Self-host in 5 minutes. Connect Monobank. Your data stays yours."

# ── Footer ────────────────────────────────────────────────────
footer_links:
  - label: "GitHub"
    href: "{github}"
  - label: "Setup"
    href: "#setup"
  - label: "Features"
    href: "#features"
footer_credit: 'Built with ❤️ in Ukraine &nbsp;·&nbsp; MIT License &nbsp;·&nbsp; <a href="{github}/issues" style="color:var(--text-muted);text-decoration:none;">Report issue</a>'
---
