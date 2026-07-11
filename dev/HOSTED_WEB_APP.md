# Hosted Watto — Launch Playbook (Vercel + Supabase + Stripe)

The exact, cheapest-that-scales path from this repo to a paid web app at
`watto.app` (or whatever domain you buy). Written to be followed top-to-bottom.

**Monthly fixed cost at launch: ~$0–25.** Vercel Hobby free (upgrade to Pro
$20 when you take payments — required by their ToS for commercial use),
Supabase free tier, Stripe pay-per-transaction, domain ~$12/yr. Everything
scales usage-based from there; the AI spend is the real cost and it's covered
by tier pricing below.

---

## 1. Architecture

```
Browser (Next.js on Vercel)
   │  supabase-js: signup/login (Google OAuth + email magic link)
   │  fetch /api/appraise, /api/answer   (JWT in header)
   ▼
Vercel serverless API routes            ← the ONLY place your OpenRouter key exists
   │  1. verify Supabase JWT
   │  2. check quota row (Postgres)     ← tiers & cooldowns enforced here
   │  3. run the engine pipeline        ← engine.py logic ported to TS (or a
   │  4. increment usage, log tokens       Python route — Vercel supports both)
   ▼
Supabase (Postgres + Auth + Storage)    Stripe (Checkout + Customer Portal + webhooks)
```

**Why the API key can't be stolen:** it lives only in Vercel env vars,
server-side. The browser never sees it — it sends a Supabase JWT, and the
serverless function makes the OpenRouter call. Rate limits + quotas mean even
a stolen *user account* can only burn its own tier allowance.

## 2. Set up Supabase (~30 min)

1. supabase.com → New project (free tier). Region close to your users.
2. **Auth:** Authentication → Providers → enable **Email** (magic link) and
   **Google** (create OAuth client in Google Cloud Console → paste client
   ID/secret; add Supabase's callback URL).
3. **Schema** — SQL editor, run:

```sql
create table profiles (
  id uuid primary key references auth.users on delete cascade,
  email text,
  tier text not null default 'free',          -- free|basic|pro|enterprise
  is_comped boolean not null default false,   -- your "free subscription" switch
  stripe_customer_id text,
  created_at timestamptz default now()
);

create table usage (
  user_id uuid references profiles(id) on delete cascade,
  period text not null,                       -- e.g. '2026-07' (monthly window)
  appraisals int not null default 0,
  tokens_in bigint not null default 0,
  tokens_out bigint not null default 0,
  cost_usd numeric(10,4) not null default 0,
  primary key (user_id, period)
);

create table appraisals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id),
  created_at timestamptz default now(),
  category text, identification text,
  result jsonb,                                -- the full report
  model_appraise text, cost_usd numeric(10,4)
);

create table anon_usage (                      -- free-run gating before signup
  fingerprint text primary key,                -- hash(ip + user agent)
  runs int not null default 0,
  last_run timestamptz default now()
);

create table enterprise_leads (
  id uuid primary key default gen_random_uuid(),
  email text, company text, message text,
  created_at timestamptz default now(),
  handled boolean default false
);

alter table profiles enable row level security;
alter table usage enable row level security;
alter table appraisals enable row level security;
create policy "own profile"    on profiles   for select using (auth.uid() = id);
create policy "own usage"      on usage      for select using (auth.uid() = user_id);
create policy "own appraisals" on appraisals for select using (auth.uid() = user_id);
-- writes happen only via API routes using the service-role key
```

4. Copy from Project Settings → API: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
   (safe for browser), `SUPABASE_SERVICE_ROLE_KEY` (server-only, bypasses RLS).

## 3. Set up Stripe (~45 min)

1. stripe.com → activate account (business details, bank account).
2. **Products** (Product catalog → Add product, each "Recurring / monthly"):
   - **Basic — $9.99/mo** → 50 appraisals/mo, standard models
   - **Pro — $29.99/mo** → 250 appraisals/mo, frontier appraisal model, PDF inputs
   - (Enterprise is not a Stripe product — it's a contact-us form → `enterprise_leads`.)
   Copy each **price ID** (`price_...`).
3. **Checkout:** use Stripe-hosted Checkout Sessions (no card data ever
   touches your code → minimal PCI scope). Success URL `/welcome`, cancel `/pricing`.
4. **Customer Portal:** Settings → Billing → Customer portal → enable, so
   users cancel/upgrade themselves (zero support burden).
5. **Webhook:** Developers → Webhooks → endpoint `https://YOURAPP/api/stripe-webhook`,
   events: `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.payment_failed`.
   Handler updates `profiles.tier`. **Verify the webhook signature** with
   `STRIPE_WEBHOOK_SECRET` — this is the step people skip and get robbed by.
   Tier changes must come *only* from webhooks, never from client claims.

## 4. Build & deploy the app (~1–2 days with Claude Code)

1. `npx create-next-app watto-web` (App Router, TypeScript, Tailwind).
2. Pages: `/` (the exact simple UI from `static/index.html`, reskinned in
   React), `/pricing`, `/account`, `/admin` (command center).
3. Port `engine.py` → `lib/engine.ts`. It's ~300 lines of prompts + fetch
   calls; the prompts move verbatim. (Alternative: keep Python and deploy the
   engine as a Vercel Python function — fine too, TS keeps one runtime.)
4. API routes (each: verify JWT → check quota → work → log usage):
   - `POST /api/appraise`, `POST /api/answer` — the pipeline. Store session
     state in a `sessions` table or encode it in the response and echo it
     back (stateless, simplest on serverless).
   - `POST /api/checkout` — creates Stripe Checkout Session for a price ID.
   - `POST /api/stripe-webhook` — tier sync (service-role key).
   - `POST /api/enterprise` — writes `enterprise_leads`, emails you (Resend
     free tier, 100 emails/day).
5. **Vercel:** push repo to GitHub → vercel.com → Import. Set env vars:
   `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
   Add your domain (bought at Cloudflare/Namecheap, ~$12/yr) — HTTPS automatic.
   **Set serverless function timeout to 300s** (research+appraise can take 60s+).

## 5. Tier & quota enforcement (the margin math)

Per-appraisal AI cost on default models ≈ **$0.03–0.12** (3 cheap calls + 1
frontier call + web plugin ≈ $0.02/appraisal surcharge). Design for the high end:

| Tier | Price | Quota/mo | Models | Worst-case AI cost | Gross margin |
|---|---|---|---|---|---|
| Anonymous | $0 | 3 lifetime | `:free` slugs only | ~$0 | — |
| Free account | $0 | 5/mo | `:free` slugs | ~$0 | — |
| Basic | $9.99 | 50 | mid (Gemini Flash appraise) | ~$2.50 | ~75% |
| Pro | $29.99 | 250 | frontier appraise (Sonnet) | ~$15 | ~50% at full burn |
| Enterprise | custom | custom | custom + API access | negotiated | price it |

Enforcement in the API route, atomic, race-safe:

```sql
insert into usage (user_id, period, appraisals) values ($1, to_char(now(),'YYYY-MM'), 1)
on conflict (user_id, period) do update set appraisals = usage.appraisals + 1
returning appraisals;  -- if > tier limit: refuse with "upgrade" message (and decrement or check first)
```

Also add a burst limit (e.g. 10 appraisals/hour on every tier) so a leaked
account can't burn a month's quota in a minute. Free models for free tiers
mean abuse costs you ~nothing. Most subscribers use a fraction of quota;
real blended margin will beat the worst-case column.

**Free-run gating flow (as you specified):** anonymous user gets 3 runs on
`:free` models keyed to `anon_usage.fingerprint` (hash of IP+UA — imperfect,
fine at this stakes level). On run 4, the submit button pops the login modal;
after login, the pricing page. If free models are down/refusing (they're
flaky), the popup appears on run 1 — same code path, so nothing breaks.

## 6. Command center (`/admin`)

A route gated by `profiles.email = you` (plus RLS deny-all; admin queries use
the service-role key server-side only). One page, four panels — all simple
selects over the tables above:

- **Subscribers:** list profiles + tier + Stripe status; buttons: **comp
  subscription** (`is_comped = true` — your free-subscription lever), change
  tier, ban.
- **Usage & spend:** appraisals + token cost per day/user (`usage` table);
  your OpenRouter dashboard shows the same spend from the provider side —
  alarm if they diverge.
- **Model control:** a `config` table (`tier → model slugs`) read by the API
  route on each call, so you can switch every tier's models live without a
  deploy (kill switch when a model misbehaves or a cheaper one ships).
- **Enterprise leads:** unhandled `enterprise_leads` rows, mark-handled.
  (Also emailed to you on submission.)

## 7. Security checklist (before taking money)

- [ ] OpenRouter key only in Vercel env vars; grep the client bundle for `sk-or` to prove it.
- [ ] Every API route verifies the Supabase JWT server-side (`supabase.auth.getUser(token)`), not just "is a token present".
- [ ] Stripe webhook signature verified; tier changes only via webhook.
- [ ] RLS enabled on all tables; service-role key never in client code.
- [ ] Quota check is atomic (single upsert), plus hourly burst cap per user and per IP.
- [ ] Upload limits (10 MB/image, 5 images) enforced server-side; images re-encoded client-side as in the local app.
- [ ] Model output treated as untrusted: escape before render (already the pattern in `static/index.html`).
- [ ] Set an OpenRouter **spend limit** on the key (their dashboard) — the ultimate blast-radius cap.
- [ ] Appraisal results stored per-user and only readable by that user (RLS).
- [ ] Terms of service: "estimates, not certified appraisals; no financial advice."

## 8. Launch sequence

1. Supabase project + schema (§2) → 2. Stripe products + webhook (§3) →
3. Build/port app (§4) → 4. Deploy to Vercel, test in Stripe **test mode**
   end-to-end (signup → 3 free runs → paywall → checkout → quota bumps →
   cancel in portal → tier drops) → 5. Flip Stripe live keys → 6. Point domain
   → 7. First 10 customers manually (pawn-shop Facebook groups, r/Flipping,
   r/pawnshop) before spending on ads.

**Ongoing ops:** watch the command center spend panel weekly; when
Basic-tier COGS < $1/user (typical), consider raising quotas as a retention
lever rather than cutting price.
