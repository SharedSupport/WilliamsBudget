# Household Ledger

A phone-first budget dashboard built from the Modernized Financial Workbook. Four files, no build step, no server, no dependencies.

## Read this before you push anything

**GitHub Pages serves publicly.** Even from a private repo, the published site is reachable by anyone with the URL unless you're on GitHub Enterprise. Never commit a backup file, a bank CSV, or the workbook itself.

The app is built so this is safe by default. All of your numbers live in `localStorage` on your phone. The repo holds only the app shell plus the starting figures already in `index.html`. Nothing is ever transmitted. The included `.gitignore` blocks the obvious mistakes.

If you'd rather nothing be public at all, see "Private hosting" below.

## Deploy to GitHub Pages

Deployment is automatic: `.github/workflows/pages.yml` publishes the site to GitHub Pages on every push. The repo must be public (or on a paid GitHub plan) for Pages to work. The site lands at `https://YOURNAME.github.io/REPONAME/`.

## Install on your phones

- **iPhone:** open the URL in Safari, Share → Add to Home Screen
- **Android:** open in Chrome, menu → Install app

It then runs full screen, launches from the home screen, and works offline.

## Two phones, one budget

Built-in sync through a **private** GitHub repo: both phones read and write one `ledger.json` file via the GitHub API, so a change on one phone shows up on the other. Setup (once):

1. Create a new **private** repository on github.com, e.g. `ledger-data`. Private matters — this file holds your real numbers, unlike the app shell in this repo.
2. Make a fine-grained token: GitHub Settings → Developer settings → Fine-grained tokens → Generate new token. Repository access: **only** `ledger-data`. Permissions: **Contents → Read and write**. (Fine-grained tokens expire — a year max — so calendar a renewal.)
3. On each phone: **Today → Your data → Set up sync**, paste the repo name and token.

The app pulls on launch and pushes a couple of seconds after every change; **Sync now** forces a round-trip. Transactions and paid-off checkmarks from both phones are merged, other edits use newest-wins. The commit history of `ledger-data` doubles as an audit log of every change.

The token is stored in localStorage on each phone. If a phone is lost, revoke that token in GitHub settings — it can only ever touch the one data repo.

Manual fallback still works: **Export backup** / **Restore backup** moves a JSON file by hand.

## Private hosting

Cloudflare Pages is the better home for this, and it's free.

1. Point Cloudflare Pages at the same repo. It deploys on every push.
2. Turn on **Cloudflare Access** (free up to 50 users) and allow only your two email addresses.

Anyone else hitting the URL gets a login wall instead of your mortgage balance. Same deployment flow, actually private. Netlify's password protection is a lighter alternative.

## Bank transactions

Three ways in, cheapest first.

**CSV export (built in, free).** Download a transaction CSV from your bank's site, then **Spending → Import bank CSV**. It handles quoted fields, `$`, and `(41.10)` style negatives, auto-detects the date/description/amount columns, and skips rows already imported so re-importing the same file is safe.

Categories apply automatically from keyword rules seeded with local merchants (Weis, Sheetz, Turkey Hill). When you set a category by hand on a transaction, it writes a new rule from that merchant name and catches it next time.

**SimpleFIN Bridge (~$1.50/mo).** Purpose-built for personal finance tools. You authorize your bank once and get a stable read-only JSON endpoint. Far less setup than Plaid for a two-person household, and no OAuth app to maintain. This is the natural next step if the CSV routine gets tedious.

**Plaid.** You already know it from PayeeGuard, and the free tier covers a household. But it needs a server to hold the secret and run the token exchange, so it only makes sense once there's a backend anyway. Worth noting that Plaid's transaction categories are coarser than the rules engine here after a few months of training.

## Files

| File | What it does |
|---|---|
| `index.html` | The whole app: markup, styles, logic |
| `manifest.json` | Home screen name, icons, colors |
| `sw.js` | Offline cache. Bump `CACHE` when you edit files |
| `icon-*.png` | Home screen icons |

## Editing the starting numbers

Bills, debts, and goals are all editable in the app. The seeded values live in the `seed()` function near the top of the script in `index.html` if you'd rather change what a fresh install starts with.

Two things carried over from the workbook that need your confirmation:

- **Water/Sewer** is quarterly at $110, anchored to February/May/August/November. The workbook didn't record the actual quarter, so check a bill and fix it under Bills → Edit if it's off.
- **PSLF count** is set to 71 of 120. The workbook's roadmap tab says 72 after August 2026, so verify against your certification letter.
