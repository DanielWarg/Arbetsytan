# Arbetsytan

Säker arbetsmiljö för journalister som hanterar känsliga tips och källor. Arbetsytan samlar material i projekt, sanerar automatiskt allt känsligt innehåll och visar endast maskad vy som standard.

## Vad gör Arbetsytan?

Arbetsytan är ett internt arbetsverktyg som:

- **Samlar källmaterial** – Organisera dokument, PDF-filer, textfiler och röstmemo i projekt
- **Importerar RSS/Atom feeds** – Skapa projekt direkt från RSS/Atom feeds med automatisk import av feed-items som dokument
- **Sanerar automatiskt** – All känslig information (e-post, telefonnummer, personnummer) maskeras automatiskt
- **Visar maskad vy** – Standardarbetsmiljö är alltid maskad; originalmaterial exponeras aldrig
- **Transkriberar röstmemo** – Lokal tal-till-text via openai-whisper (ingen extern tjänst)
- **Förädlar transkript** – Deterministisk redaktionell förädling av röstmemo-transkript

## Vad är Arbetsytan INTE?

- **Inte en redaktionssystem eller CMS** – Systemet publicerar inte innehåll
- **Inte ett AI-skrivverktyg** – Genererar inte artiklar eller text för publicering
- **Inte en källhanteringsplattform** – Ersätter inte journalistens bedömning eller arbete
- **Inte ett produktionsverktyg** – Fokus ligger på säker hantering, inte publicering

## Arbetsflöde

1. **Skapa projekt** – Organisera material i ett projekt med klassificering (Offentlig, Känslig, Källkänslig)
   - Skapa manuellt eller importera från RSS/Atom feed
2. **Ladda upp material** – PDF, textfiler eller spela in röstmemo direkt i webbläsaren
   - Eller importera feed-items automatiskt som dokument
3. **Automatisk sanering** – Systemet maskerar all känslig information enligt progressive sanitization (Normal → Strikt → Paranoid)
4. **Läs maskad vy** – Alla dokument visas i maskad vy som standard; originalmaterial exponeras aldrig i arbetsytan
5. **Arbeta säkert** – Maskerad text är redaktionellt arbetsbar och kan användas utan risk för PII-läckage

## Säkerhetsmodell

**Security by default** – Säkerhet är standard, inte valfritt. All material maskeras automatiskt enligt deterministisk pipeline:

- **Normal sanering** – E-post, telefonnummer och personnummer maskeras
- **Strikt sanering** – Ytterligare numeriska sekvenser maskeras vid behov
- **Paranoid sanering** – Alla siffror och känsliga mönster maskeras när normal/strikt inte räcker

**Fail-closed** – Vid osäkerhet stängs systemet ner; inget material exponeras.

**Originalmaterial** – Originalmaterial bevaras i säkert lager och exponeras aldrig i arbetsytan.

## Dokumentation

- [VISION.md](VISION.md) – Produktvision och arbetsflöde
- [PRINCIPLES.md](PRINCIPLES.md) – Non-negotiable principer
- [SECURITY_MODEL.md](SECURITY_MODEL.md) – Säkerhetsmodell och klassificering
- [ROADMAP.md](ROADMAP.md) – Utvecklingsroadmap med stop/go-punkter
- [RUNBOOK.md](RUNBOOK.md) – Verifieringsrunbook för alla faser
- [docs/FEED_IMPORT_PLAN.md](docs/FEED_IMPORT_PLAN.md) – Feed import implementation och status

## Teknisk stack

- **Backend:** FastAPI (Python), PostgreSQL
- **Frontend:** React + Vite
- **Tal-till-text:** Whisper (lokal, ingen extern tjänst, konfigurerbar modellstorlek)
- **Deployment:** Docker Compose

## Lokal tal-till-text (STT)

Arbetsytan använder **faster-whisper** (default) eller **Whisper** för lokal tal-till-text-transkribering (ingen extern tjänst).

**Varför lokal STT?**
- Fullständig dataintegritet: ingen data lämnar systemet
- Driftssäkerhet: fungerar offline, inga API-beroenden
- Modell-caching säkerställer snabbare efterföljande transkriberingar
- Konfigurerbar modellstorlek för olika användningsfall

**Demo STT-konfiguration (default):**
- **Engine:** `STT_ENGINE=faster_whisper` (4x snabbare än Whisper)
- **Model:** `WHISPER_MODEL=small` (bättre kvalitet: 41.0s för 20MB fil, 1169 ord)
- **Motivering:** Bättre kvalitet än base (1169 ord vs 1150 ord, lägre nonsense ratio 0.166 vs 0.174)
- **CPU:** 696% peak, 494% medel
- **RAM:** 1.54GB

**Alternativ konfiguration:**
- **Snabbast (lägre kvalitet):** `STT_ENGINE=faster_whisper WHISPER_MODEL=base` (15.2s, 1150 ord)
- **Bäst kvalitet:** `STT_ENGINE=faster_whisper WHISPER_MODEL=medium` (långsammare, men bäst kvalitet)
- **Whisper base:** `STT_ENGINE=whisper WHISPER_MODEL=base` (58.8s, 1107 ord)
- **Whisper small:** `STT_ENGINE=whisper WHISPER_MODEL=small` (179.2s, 1173 ord)

**Arkitektur:**
STT-motorn är abstraherad i `text_processing.py` för enkel utbytbarhet. Framtida motorbyten (t.ex. Silero ASR) kan implementeras utan ändringar i endpoints eller UI.

**Caching:**
STT-engine caches i global singleton för att undvika upprepad laddning. Modell-cache sparas i persistent Docker volume (`whisper_cache`) för att överleva container-rebuilds.

**Minneskrav:**
- **faster-whisper base:** ~0.8GB RAM (rekommenderat för demo)
- **faster-whisper small:** ~1.5GB RAM
- **whisper base:** ~0.9GB RAM
- **whisper small:** ~1.8GB RAM
- **base:** ~1-2GB RAM (bra för utveckling)
- **medium:** ~3-5GB RAM (bra balans, default)
- **large-v3:** ~6-10GB RAM (bäst kvalitet, kräver Docker Desktop med 10-12GB minne)

**Prestanda:**
- **medium (default):** ~3-5 minuter för första transkribering (modellladdning + CPU-inferens), efterföljande snabbare
- **large-v3:** ~15-20 minuter för första transkribering, bäst kvalitet men långsam på CPU
- **base/small:** ~1-2 minuter, snabbast men lägre kvalitet

**Begränsningar:**
- CPU-baserad inferens (ingen GPU-acceleration i nuvarande setup)
- För large-v3: Öka Docker Desktop minne till minst 10GB (Settings → Resources → Advanced → Memory)

## Security Core (framtida)

Security Core är en isolerad, dormant modul förberedd för framtida extern AI-integration. Modulen porterats från copy-pastev2 och innehåller Privacy Shield (defense-in-depth masking), Privacy Gate (hard enforcement för extern LLM) och Privacy Guard (content protection för loggning).

**Status:** Inaktiv, dormant, opt-in via feature flag. Ingen endpoint-användning. Befintlig masking i `text_processing.py` förblir aktiv och oberoende.

Se [docs/SECURITY_CORE.md](docs/SECURITY_CORE.md) för detaljer.

## Feed Import

Arbetsytan stödjer import av RSS/Atom feeds för att automatiskt skapa projekt med feed-items som dokument.

**Funktioner:**
- **Preview feed** – Förhandsgranska feed innan import (visar titel, beskrivning och första 3 items)
- **Skapa projekt från feed** – Importera feed-items som dokument med automatisk sanering och PII-maskning
- **Deduplikation** – Automatisk deduplikation baserat på feed item GUID eller länk
- **SSRF-skydd** – Robust skydd mot Server-Side Request Forgery (endast http/https, blockar privata IPs, timeout och max storlek)
- **Scout-integration** – Skapa projekt direkt från feeds i Scout-modal

**Användning:**
1. Gå till Kontrollrum
2. Klicka på "Skapa projekt från feed" eller öppna Scout-modal → Källor → "Skapa projekt"
3. Ange feed URL och välj antal items att importera (10 eller 25)
4. Förhandsgranska feed
5. Skapa projekt – feed-items importeras automatiskt som dokument genom samma ingest-pipeline som övriga dokument

**API endpoints:**
- `GET /api/feeds/preview?url=...` – Förhandsgranska feed
- `POST /api/projects/from-feed` – Skapa projekt från feed

Se [docs/FEED_IMPORT_PLAN.md](docs/FEED_IMPORT_PLAN.md) för teknisk dokumentation.

## Run locally

Starta hela stacken (Postgres + API + Web):

```bash
make dev
```

Detta startar:
- Postgres på port 5432
- FastAPI backend på port 8000
- React frontend på port 3000

Öppna webbläsaren på http://localhost:3000

### Andra kommandon

```bash
make up                  # Starta i bakgrunden (production mode)
make down                # Stoppa alla services
make verify              # Kör smoke tests (kräver att services körs)
make verify-feed-import  # Verifiera feed import-funktionalitet
make clean               # Stoppa och ta bort volumes
```

## Showreel

Detta är ett live demo-verktyg byggt som om det vore för intern nyhetsredaktionsanvändning. Fokus ligger på att visa hur säker, strukturerad hantering av känsligt material kan fungera i praktiken.

