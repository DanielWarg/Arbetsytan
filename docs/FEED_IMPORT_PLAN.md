# Feed Import Implementation Plan

## A) Inventory - Nuvarande System

### Projekt-skapande
- **Fil:** `apps/api/main.py:140-168`
- **Endpoint:** `POST /api/projects`
- **Schema:** `ProjectCreate` (från `schemas.py`)
- **Model:** `Project` (från `models.py`)

### Document Ingest Pipeline
- **Fil:** `apps/api/main.py:434-689` (`POST /api/projects/{project_id}/documents`)
- **Pipeline-steg:**
  1. Extract text (`extract_text_from_pdf` eller `extract_text_from_txt`)
  2. Normalize (`normalize_text` från `text_processing.py`)
  3. Progressive sanitization:
     - `mask_text(normalized_text, level="normal")`
     - `pii_gate_check(masked_text)`
     - Om fail → `mask_text(..., level="strict")`
     - Om fail → `mask_text(..., level="paranoid")`
  4. Spara `Document` med: `filename`, `file_type`, `masked_text`, `sanitize_level`, `pii_gate_reasons`, `usage_restrictions`

### PII Gate & Sanitization
- **Fil:** `apps/api/text_processing.py`
- **Funktioner:** `mask_text()`, `pii_gate_check()`, `normalize_text()`
- **Säkerhet:** Fail-closed princip

### Database Models
- **Fil:** `apps/api/models.py`
- **Project:** id, name, description, classification, status, due_date, tags (JSON)
- **Document:** id, project_id, filename, file_type, classification, masked_text, file_path, sanitize_level, usage_restrictions (JSON), pii_gate_reasons (JSON)
- **OBS:** Document saknar metadata-fält för feed info → måste läggas till

### Feed Parsing (befintlig)
- **Fil:** `apps/api/scout.py`
- **Bibliotek:** `feedparser` (redan i `requirements.txt`)
- **Användning:** RSS/Atom parsing med `feedparser.parse()`

### Frontend
- **Fil:** `apps/web/src/pages/CreateProject.jsx` - Modal för projekt-skapande
- **Fil:** `apps/web/src/pages/ProjectsList.jsx` - Lista projekt med "Nytt projekt" knapp

---

## Filer som skapas/ändras

**Backend:**
- `apps/api/feeds.py` (NY) - Feed fetching med SSRF-skydd, parsing, HTML-to-text
- `apps/api/models.py` - Lägg till `metadata` (JSON) i Document
- `apps/api/schemas.py` - Lägg till FeedPreviewResponse, FeedItemPreview, CreateProjectFromFeedRequest/Response
- `apps/api/main.py` - Lägg till GET /api/feeds/preview och POST /api/projects/from-feed

**Frontend:**
- `apps/web/src/pages/CreateProjectFromFeed.jsx` (NY) - Modal för feed import
- `apps/web/src/pages/ProjectsList.jsx` - Lägg till "Skapa projekt från feed" knapp

**Verifiering:**
- `apps/api/_verify/verify_feed_import.py` (NY) - Test script med fixture
- `tests/fixtures/sample.rss` (NY) - Test fixture

**Dokumentation:**
- `docs/FEED_IMPORT_PLAN.md` (denna fil)

---

## Säkerhetskrav

- **SSRF-skydd (ROBUST):**
  - Endast http/https tillåtna
  - DNS-resolve och validera resolved IP (blocka privata IP även efter DNS)
  - Blocka redirects till privata IP (följ redirects men validera varje hop)
  - Blocka: localhost, 127.0.0.1, privata IP-range, link-local
  - Timeout: 10s, Max storlek: 5MB

- **DB-migration:** Måste bevisas att Document.metadata läggs till korrekt (API får inte ge 500)

- **Dedupe:** guid prioriteras, annars link (per projekt)

- **Ingen ändring i PII-gate/sanitization:** Använd exakt samma pipeline som befintliga dokument
