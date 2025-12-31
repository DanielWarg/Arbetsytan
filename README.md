# Arbetsytan

Säker arbetsmiljö för journalister som hanterar känsliga tips och källor. Arbetsytan erbjuder en strukturerad process från mottagning till analys med fokus på säkerhet, översikt och stöd för journalistiskt arbete.

## Dokumentation

- [VISION.md](VISION.md) – Produktvision och arbetsflöde
- [PRINCIPLES.md](PRINCIPLES.md) – Non-negotiable principer
- [ROADMAP.md](ROADMAP.md) – Utvecklingsroadmap med stop/go-punkter
- [RUNBOOK.md](RUNBOOK.md) – Verifieringsrunbook för FAS 0–4

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

## Demo

_Placeholder – demo URL kommer att läggas till när demo är tillgänglig._

