# Arbetsytan

Säker arbetsmiljö för journalister som hanterar känsliga tips och källor. Arbetsytan samlar material i projekt, sanerar automatiskt allt känsligt innehåll och visar endast maskad vy som standard.

## Vad gör Arbetsytan?

Arbetsytan är ett internt arbetsverktyg som:

- **Samlar källmaterial** – Organisera dokument, PDF-filer, textfiler och röstmemo i projekt
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
2. **Ladda upp material** – PDF, textfiler eller spela in röstmemo direkt i webbläsaren
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

## Teknisk stack

- **Backend:** FastAPI (Python), PostgreSQL
- **Frontend:** React + Vite
- **Tal-till-text:** openai-whisper (lokal, ingen extern tjänst)
- **Deployment:** Docker Compose

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
make up      # Starta i bakgrunden (production mode)
make down    # Stoppa alla services
make verify  # Kör smoke tests (kräver att services körs)
make clean   # Stoppa och ta bort volumes
```

## Showreel

Detta är ett live demo-verktyg byggt som om det vore för intern nyhetsredaktionsanvändning. Fokus ligger på att visa hur säker, strukturerad hantering av känsligt material kan fungera i praktiken.

