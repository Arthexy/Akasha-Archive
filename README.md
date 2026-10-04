# HoYo–Akasha Hub

A local Genshin Impact workspace with a Rich terminal interface and a FastAPI dashboard. Public showcase data comes from Enka.Network; build rankings come from Akasha. Optional HoYoLAB cookies enable private daily notes.

## Deploy to Vercel (public showcase and rankings)

Import `Arthexy/Akasha-Archive` at https://vercel.com/new. Use the **FastAPI**
framework preset and repository root (`./`). Leave build and output overrides
disabled. Python 3.12 is selected by `.python-version`.

Vercel automatically enables public mode via `VERCEL=1`. This mode ignores local
configuration and HoYoLAB environment credentials, blocks server configuration
writes and private endpoints, and hides private account features. Do not upload
`config.json` or add HoYoLAB cookies to Vercel.

Default UID, theme, language, ranking preference and recent accounts are stored
in each visitor's browser. They do not sync between devices or browsers and are
removed when site data is cleared. Public Enka/Akasha data is fetched on demand;
the server cache is temporary and keyed by UID.

Deployment and production hosts are allowed through Vercel's URL environment
variables. For a custom domain, add its hostname to `HOYO_HUB_ALLOWED_HOSTS`
(comma-separated, without `https://`) and redeploy. Keep Vercel's system
environment variables enabled. Ranking availability also depends on Akasha
and the runtime's `curl` binary; verify a real UID after deployment.

For a local public-mode preview, set `HOYO_HUB_PUBLIC=1` before starting the app.
Offline checks: `node tests/test_device_preferences.cjs` and
`python -m pytest tests/test_public_deployment.py -q`.

## Local installation

Python 3.11 or newer is required. No Node.js, database, or frontend build step.

### Windows / PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python cli.py serve
```

### Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python cli.py serve
```

Open **http://127.0.0.1:8000**. Enter a public UID, or open Settings to save a default UID. The dashboard starts with a genuine empty state; it does not invent player data.

## Dashboard redesign

Web UI uses Indonesian copy, a dark archive palette, system serif/sans fonts, portrait showcase grids, and a separate character detail destination. Back restores showcase filters, page, scroll and character focus. Existing accent settings remain compatible: `amber` maps to muted gold and `green` to soft green.

HoYoLAB settings separate preferences, cookie saving/testing, and bound-account selection. Saving cookies does not automatically test access. Cookie deletion asks for confirmation and explicitly distinguishes local credentials from environment overrides. Enka/Akasha refresh does not refresh private notes.

Refresh controls use provider cooldown/TTL information from API responses. Missing values remain unavailable; valid zero values remain zero. See `REDESIGN-QA.md` for checked scenarios and remaining validation.

Offline UI checks:

```powershell
node tests/test_frontend.cjs
.\.venv\Scripts\python tests/preview_redesign.py
```

The second command serves an explicitly labelled fixture dashboard at `http://127.0.0.1:8001`. It uses no user config, credentials, or provider requests. The normal app on port 8000 never uses these fixtures.

## CLI commands

Use your virtual environment's Python executable for these commands:

```bash
python cli.py setup
python cli.py profile --uid 812345678
python cli.py showcase --uid 812345678
python cli.py character 10000046 --uid 812345678
python cli.py rankings --uid 812345678
python cli.py notes
python cli.py status --json
python cli.py serve --port 8000
```

Data commands support `--refresh`, `--json`, and `--no-color`. `--uid` only selects a public account; private notes use the verified bound HoYoLAB account. The `NO_COLOR` environment variable is supported.

Exit codes: 0 success, 2 configuration/input, 3 authentication, 4 unavailable source, 5 rate limit, 130 interrupted.

## HoYoLAB connection

1. Open **Settings → HoYoLAB connection**.
2. Select Overseas or China.
3. Enter your own `ltuid_v2` and `ltoken_v2` cookie values.
4. If required by your provider, add `ltmid_v2` or `cookie_token_v2` under additional cookies. Other supported cookie fields can be placed directly in local config.
5. Save connection, test access, select a bound Genshin account, and save selection.
6. Open Daily notes.

Cookies are stored in local `config.json` as plaintext, omitted from API reads, and never sent to Enka/Akasha. They are optional. Daily notes are not available for arbitrary public UIDs. The app does not extract browser cookies or change HoYoLAB privacy settings automatically.

The `genshin.py` dependency handles region-specific DS signatures. Cookie validity, verification requirements, and provider changes may still affect access. If verification is required, complete it in the official HoYoLAB application/site. Live authenticated integration requires your own credentials and cannot be verified by the bundled offline tests.

## Configuration

Copy `config.example.json` to `config.json`, or save settings through the UI/CLI. Configuration is relative to the application directory, not the terminal working directory. Saving uses atomic replacement. POSIX file permissions are restricted to the file owner; on Windows, use your user directory's normal access controls.

Supported environment overrides:

```text
HOYO_HUB_UID
HOYO_HUB_LTUID_V2
HOYO_HUB_LTOKEN_V2
HOYO_HUB_HOST
HOYO_HUB_PORT
```

Priority: environment → file → defaults. Environment secrets are not copied to disk when changing settings. Removing credentials in the dashboard clears disk credentials and disables notes; remove environment overrides separately to erase those values.

`server.host` accepts loopback, private LAN IPv4 addresses (10/8, 172.16/12, 192.168/16), or a Tailscale IP (100.64.0.0/10). Use an explicit interface address; wildcard and public hosts are rejected. The web API uses same-origin checks and a page-issued CSRF token for mutations.

## Preview on another device over Wi-Fi / LAN

Find the PC's Wi-Fi or Ethernet IPv4 address with `ipconfig`, then start:

```powershell
.\.venv\Scripts\python cli.py serve --host 192.168.1.6
```

Replace the example IP with your PC's address. On another device on the same network, open `http://192.168.1.6:8000`. Allow Python through Windows Firewall on private networks if prompted. Tailscale is not required. To persist this, set `server.host` in `config.json` to that IP; update it if the PC's address changes.

## Remote access over Tailscale

An optional way to reach the dashboard from another network. When bound to a Tailscale IP, devices connect over your tailnet and Tailscale traffic is end-to-end encrypted.

1. Install Tailscale on the PC running the hub and on every device you want to use:
   - Windows: https://tailscale.com/download/windows
   - Android: Play Store / F-Droid
   - iOS: App Store
2. Sign in to the **same account** on every device.
3. Find this PC's Tailscale IP:

   ```powershell
   tailscale ip -4
   ```

   It looks like `100.x.y.z`.

4. Start the server bound to that address:

   ```powershell
   .\.venv\Scripts\python cli.py serve --host 100.x.y.z
   ```

   Startup output confirms the URL and whether it is loopback or tailnet-only.

5. From the other device open `http://100.x.y.z:8000`.

**Optional — persist the host** so plain `cli.py serve` always uses Tailscale:

```json
"server": { "host": "100.x.y.z", "port": 8000, "allowed_hosts": [] }
```

**Optional — MagicDNS name.** If you enable Tailscale MagicDNS and prefer `http://mypc:8000`, add the name to `allowed_hosts`:

```json
"server": { "host": "100.x.y.z", "port": 8000, "allowed_hosts": ["mypc"] }
```

The Host allowlist is computed at startup; restart the server after changing it. Requests carrying any other Host header are rejected with `400`.

Use loopback for local access, your private LAN IP for same-network previews, or Tailscale for access over your tailnet.

## Data and caching

- Enka returns the public character showcase, not the complete inventory.
- Character, weapon, and set names use cached Enka metadata with a CDN fallback. Equipped artifact piece names are supplemented from genshin-db. Missing translations show descriptive labels rather than raw hash numbers.
- Character portraits support skill-depot variants and costumes; the overview uses the player's selected profile picture. Visible characters without published build details keep a profile entry explaining the missing details.
- Akasha rankings include category, assumed weapon, bracket, rank, population, top percentage, and (when available) character level, element, artifact sets, and Crit Value from Akasha's builds endpoint. Matching against the latest showcase is explicitly unverified.
- Akasha requests are delegated to the system `curl` binary. Cloudflare fingerprints the TLS/HTTP2 handshake and challenges Python's httpx with 403; curl is served JSON. No challenge is solved and no clearance cookie is stored. If `curl` is missing, rankings report `CURL_UNAVAILABLE` while showcase and notes keep working.
- Artifact Crit Value is computed from artifact substats only.
- Daily notes include Resin, commissions, expeditions, realm currency, weekly discounts, and transformer information when provided.
- Missing values remain unavailable rather than becoming zero.
- Cache defaults: Enka 300 seconds, Akasha 900 seconds, notes 60 seconds. Provider TTL and rate-limit cooldowns take precedence over manual refresh.
- Cache is bounded and in-memory. CLI and web processes have independent caches. Restarting clears it.
- Temporary failures can display stale cached results with a warning. Authentication failures do not receive stale-cache fallback.
- Daily notes auto-refresh only while the browser tab is visible. Countdown timers are computed locally.
- Daily commission progress combines commissions and claimed/claimable Encounter Points, capped at the daily total. The breakdown distinguishes points ready to claim; stored long-term points do not count until converted.
- Load account fetches both showcase and enabled Akasha rankings. The same UID changes the action to Refresh data. Rankings have 10-row pagination above and below, compact category buttons with full-detail dialogs, and character icons. Showcase sorting supports both directions. Info buttons work with hover, keyboard focus, or a tap; settings fields have visibility toggles for typed values.

## Project map

| File | Role |
|---|---|
| `config.py` | Validated configuration and atomic persistence |
| `models.py` | Normalized character, stat, and artifact models |
| `enka_client.py` | Public Enka/Akasha clients and metadata |
| `hoyolab_client.py` | HoYoLAB adapter, account verification, notes |
| `services.py` | Shared orchestration for CLI and web |
| `cache.py` | Bounded cache, deduplication, stale fallback |
| `errors.py` | Structured errors |
| `cli.py` | Rich rendering and commands |
| `app.py` | FastAPI routes and local dashboard security |
| `templates/dashboard.html` | Dashboard shell and settings |
| `static/` | CSS, vanilla JavaScript, locally served font |
| `tests/test_hub.py` | Offline integration and parser tests |

## Local API

All paths use `/api/v1`:

```text
GET    /health
GET    /status
GET    /config
PATCH  /config
POST   /auth/hoyolab
DELETE /auth/hoyolab
POST   /auth/hoyolab/test
GET    /accounts/hoyolab
GET    /profile/{uid}
GET    /showcase/{uid}
GET    /showcase/{uid}/characters/{character_id}
GET    /rankings/{uid}
GET    /notes
POST   /refresh
```

Mutation requests require the same-origin `Origin` header and `X-CSRF-Token` from the dashboard HTML meta tag. `/refresh` accepts `{ "source": "showcase|rankings|notes", "uid": "..." }`. GET responses never contain saved cookies.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use mocked transport and temporary configs, including secret redaction, CSRF, bound-account checks, normalization, cooldowns, and cache deduplication. They do not send credentials or requests to live providers.

## Troubleshooting

- **No characters:** enable public character details in the in-game showcase, then wait for provider cache expiry.
- **No ranks:** Akasha may not have rankings for this build/account.
- **Metadata unavailable:** the showcase still works with numeric names; check GitHub connectivity.
- **Expired cookies:** replace cookies in Settings and test again.
- **Several game accounts:** use Test / list accounts and select the desired account.
- **Port occupied:** run `python cli.py serve --port 8001`.
- **Invalid configuration:** compare your file with `config.example.json`; secrets are deliberately omitted from error messages.
- **Termux:** not yet verified on Android ARM. Installation may require native build dependencies for Python packages.

## Sources and assets

- Enka API documentation: https://github.com/EnkaNetwork/API-docs
- Enka public endpoint: `https://enka.network/api/uid/{uid}/`
- Akasha adapter endpoint: `https://akasha.cv/api/getCalculationsForUser/{uid}` (observed schema; no stability guarantee)
- HoYoLAB adapter: https://github.com/thesadru/genshin.py
- JetBrains Mono font: https://github.com/JetBrains/JetBrainsMono, SIL Open Font License included in `static/fonts/OFL.txt`.

Independent local utility; not affiliated with HoYoverse, Enka.Network, or Akasha System.
