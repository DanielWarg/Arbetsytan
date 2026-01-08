## Arbetsytan

Säker journalistisk arbetsyta (showreel) för hantering av känsligt material: projekt, dokument, röstmemo, Scout (feeds) och **Fort Knox** för deterministiska integritetsrapporter.

### Showreel-video (UI)

- **Intro-route**: öppna `/intro` (eller startsidan om “hoppa över” inte är ikryssad).
- **Video-fil**: lägg `Arbetsytan__Teknisk_djupdykning.mp4` i repo-root (Makefile kopierar den in i `apps/web/public/` vid `make build-web` / `make prod-up`).
- **Alternativ**: sätt `VITE_SHOWREEL_VIDEO_URL` om du vill peka på en extern videokälla.

### Varför den här repo:n finns (för arbetsgivare)

- **Produkt-idé**: en intern redaktionell yta där original aldrig exponeras, men där journalisten ändå kan jobba snabbt.
- **Teknisk idé**: en deterministisk sanitiseringspipeline + policy-gates (“fail‑closed”) + tydlig UX.
- **Demo-idé**: kör lokalt (Docker) och kan exponeras över HTTPS på **en domän** via Tailscale Funnel.

### Kärnfeatures (kort)

- **Maskad vy som default**: UI visar sanitiserad text; original ligger i separat lagring.
- **Progressiv sanering**: `normal → strict → paranoid` med PII-gate.
- **Scout**: RSS/Atom → skapa projekt från “leads” med samma sanitiseringspipeline.
- **Röstmemo**: lokal STT (ingen extern tjänst) → transkribering sparas som dokument.
- **Fort Knox**: kompilera **Intern** / **Extern** rapport från projekt-underlag med input/output-gates, re-id guard och idempotens. Rapporter kan sparas som dokument.
- **Showreel-deploy**: Caddy + Docker Compose lokalt, HTTPS via Tailscale Funnel.

### Fort Knox (vad det är och varför det är intressant)

Fort Knox är en deterministisk “rapportstation” som sammanställer projektets underlag utan att tumma på integritet:

- **Input gate**: stoppar om underlag inte når rätt saneringsnivå eller om PII‑gate failar.
- **Extern policy**: striktare och fail‑closed. Datum/tid blockar inte; datum/tid maskas deterministiskt i pipeline vid `strict/paranoid`.
- **Output gate + re-id guard**: stoppar om output riskerar att återskapa citat/identifierare.
- **Idempotens**: samma input → samma fingerprint → samma rapport.
- **UX**: “Datum maskat” syns som icke-blockande info, och rapporten kan sparas som dokument i projektet.

Mer: `docs/ARCHITECTURE.md` och `docs/FLOWS.md`.

### Säkerhet (principer)

- **Metadata-only logs**: inga råtexter (varken input eller output) i loggar/events.
- **Fail-closed**: om sanering/gates inte kan bevisas → ingen export/rapport.
- **SSRF-skydd** i feed-import (endast http/https, blockar privata IP-range, timeouts).

Mer: `SECURITY_MODEL.md` och `docs/SECURITY.md`.

### Snabbstart (lokalt)

Förutsättningar: Docker Desktop + `docker-compose` (och Node om du vill köra web lokalt utanför docker).

Starta hela stacken:

```bash
make dev
```

Öppna UI:
- `http://localhost:3000`

### Demo-deploy: en domän via Tailscale Funnel (HTTPS)

Kör lokal “prod-demo” (Caddy + API + Postgres) på `localhost:8443`:

```bash
make prod-up
```

Exponera över HTTPS via Funnel (en domän, ingen subdomän):

```bash
tailscale funnel 443 localhost:8443
```

Runbook: `deploy/tailscale/README.md`.

### Verifiering (snabbt)

```bash
make verify
make verify-sanitization
make verify-fortknox-v1-loop
```

Mer: `RUNBOOK.md` och `docs/VERIFYING.md`.

### Dokumentation (ingångar)

- **Översikt & riktning**: `VISION.md`, `PRINCIPLES.md`, `ROADMAP.md`
- **Säkerhet**: `SECURITY_MODEL.md`, `docs/SECURITY.md`
- **Arkitektur & flöden**: `docs/ARCHITECTURE.md`, `docs/FLOWS.md`
- **Deploy**: `deploy/tailscale/README.md`

### Teknisk stack (kort)

- **Backend**: FastAPI + PostgreSQL
- **Frontend**: React + Vite
- **STT**: faster-whisper/Whisper (lokalt)
- **Fort Knox Local**: lokal LLM-brygga (se `fortknox-local/`)

### Appendix: STT-detaljer (för den som vill grotta)

Det finns benchmark/verify-stöd och fler detaljer i `docs/STT_BENCHMARK.md` och `docs/VERIFYING.md`.

