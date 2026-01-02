# Phase 1: Security by Design - Implementation Plan

## 🧠 Working Principles — Phase 1: Security by Design

Detta dokument styr hur arbetet ska utföras, inte bara vad som ska göras.

### Grundprincip

**Vi bygger inte nya produktfeatures. Vi bygger enforcement + verifiering.**

Vi aktiverar och bevisar säkerhetsbeteenden som redan finns eller som är direkt portabla från copy-pastev2.

### Säkerhetsfilosofi

- **Säkerhet ska vara automatisk** – användaren ska inte behöva tänka, välja eller konfigurera.
- **Systemet ska alltid vara fail-closed:**
  - Vid osäkerhet ska systemet blockera, inte fortsätta tyst.
- **Alla säkerhetspåståenden ska vara verifierbara i Docker med körbara scripts.**
  - Ingen verifiering = inget klart.

### Arbetsmetod (obligatorisk)

Varje steg ska:
- peka på exakta filer och rader som ändras
- ha tydliga acceptance criteria
- avslutas med PASS/FAIL-verifiering

**Inga antaganden. Inga gissningar. Inga "bör fungera".**

- UI-ändringar måste verifieras i browser mode.
- Backend-ändringar måste verifieras via `_verify`-scripts.

### Arkitektoniska regler

- **Inget innehåll (text, filer, identifiers) får nå:**
  - events
  - logs
  - audit trails
- **Delete betyder riktig delete:**
  - DB + filstore
  - inga orphans
  - verifierat efteråt
- **Metadata får loggas – aldrig content.**

### Definition of Done

En punkt i denna plan är inte klar förrän:
- verifieringsscript körs i Docker
- resultatet är PASS
- beviset kan visas utan förklaring

**Målet med Phase 1 är att vi utan tvekan ska kunna säga:**  
*"I detta verktyg kan du arbeta säkert utan att röja källor, utan att bryta mot GDPR av misstag, och när du raderar data är den verkligen borta."*

## ✅ PHASE 1 — Security by Design (Checklist för Cursor)

### 0) Setup & Guardrails

- [ ] Skapa dokument: `docs/PHASE_1_SECURITY_BY_DESIGN_PLAN.md` och lägg in checklistan (denna) så den lever i repot
- [ ] Bekräfta körmiljö: `docker compose ps` visar api + postgres healthy
- [ ] Bekräfta hur verifieringsscripts körs i Arbetsytan: `docker compose exec api python _verify/<script>.py` (working dir `/app`)

### Milestone 1 — Event "No Content" Enforcement (Max effekt / Min risk)

#### 1.1 Inventory: var ska enforcement in?

- [ ] Lista alla ställen i `apps/api/main.py` där `ProjectEvent` skapas (rad-länkar)
- [ ] Bekräfta att `apps/api/security_core/privacy_guard.py` innehåller:
  - `sanitize_for_logging()`
  - `assert_no_content()`
- [ ] Definiera "förbjudna fält" (en lista i docs + i verify-script): se "Definitions & Guardrails" ovan för komplett lista

#### 1.2 Implementera enforcement i alla events

- [ ] Importera Privacy Guard i `apps/api/main.py`
- [ ] Skapa en liten helper (t.ex. `_safe_event_metadata(meta: dict, context: str) -> dict`) som:
  - kör `sanitize_for_logging(meta, context=...)`
  - kör `assert_no_content(sanitized, context=...)`
  - returnerar `sanitized`
- [ ] Byt ut samtliga `ProjectEvent(... metadata=...)` så att metadata alltid passerar helpern
- [ ] Säkerställ fail-closed:
  - DEV (`DEBUG=true`): raise AssertionError (så vi ser fel direkt)
  - PROD (`DEBUG=false`): droppa fält och fortsätt (enligt policy)
- [ ] Dokumentera vilken env-flagga som styr "DEV vs PROD": `DEBUG` (default: `false`)

#### 1.3 Verifieringsscript: event policy

- [ ] Skapa: `apps/api/_verify/verify_event_no_content_policy.py`
- [ ] Testfall 1: försök skapa event med förbjuden nyckel (t.ex. `{"text": "content"}`) → AssertionError i DEV
- [ ] Testfall 2: försök skapa event med source identifier (t.ex. `{"filename": "secret.pdf"}`) → AssertionError i DEV
- [ ] Testfall 3: skapa event med harmlös metadata (t.ex. `{"project_id": 123}`) → PASS
- [ ] Scriptet ska köras i **DEV mode** (`DEBUG=true`) för att bevisa fail-closed hårt
- [ ] Optional: testfall som visar PROD "drops" utan crash (för demo-trovärdighet)
- [ ] Scriptet ska vara körbart i Docker och skriva tydligt PASS/FAIL

#### 1.4 Acceptance / Bevis

- [ ] Kör i Docker: `docker compose exec api python _verify/verify_event_no_content_policy.py`
- [ ] Verifiera i browser mode att UI fortfarande fungerar och events laddar

### Milestone 2 — Secure Delete (Project + Allt innehåll) med Verifiering

#### 2.1 Inventory: vad ingår i "Project delete"?

- [ ] Lista alla data som måste bort när projekt raderas:
  - documents + deras filer
  - recordings + audio + transcript-filer
  - notes (inkl ev. attachments/bilder om ni har)
  - events
- [ ] Identifiera var filerna ligger (upload dir / filstore paths)
- [ ] Bekräfta befintlig `delete_project()` i `apps/api/main.py` (rad ~219) och vad den gör idag

#### 2.2 Implementera "wipe + orphan detection + idempotency"

- [ ] Före delete: räkna antal filer som tillhör projektet (utan att logga filnamn)
- [ ] Radera DB-rader i rätt ordning / via cascade så att allt kopplat försvinner
- [ ] Wipe filstore:
  - ta bort filer kopplade till projektet (documents/recordings/notes)
  - verifiera att filerna faktiskt är borta
- [ ] Orphan detection:
  - hitta filer i projektets filområde som inte längre har DB-referens
  - efter wipe: ska det vara 0
- [ ] Fail-closed:
  - om wipe/verifiering misslyckas → returnera error och blockera delete (ingen "silent success")
- [ ] Loggpolicy:
  - logga bara antal (counts), inga paths eller filenames
- [ ] Idempotent:
  - kör delete igen på samma projekt → ska inte krascha / ska ge kontrollerat svar

#### 2.3 Verifieringsscript: secure delete

- [ ] Skapa: `apps/api/_verify/verify_secure_delete.py`
- [ ] Scriptet ska:
  - skapa projekt
  - ladda upp minst 1 document
  - skapa 1 recording (eller ladda upp) så det blir filer på disk
  - skapa 1 note
  - verifiera att filer finns på disk innan delete
  - kalla delete endpoint
  - verifiera:
    - DB: inga rader kvar kopplade till projektet
    - filsystem: inga filer kvar kopplade till projektet
    - orphan count = 0
- [ ] Scriptet ska vara körbart i Docker och skriva PASS/FAIL

#### 2.4 Delete-confirmation UX (minimal, för demo-trovärdighet)

- [ ] UI: Delete kräver bekräftelse (skriv projektnamn / "RADERA" eller liknande)
- [ ] UI visar efter delete en "Deleted project" bekräftelse (utan att återge namn/filer)
- [ ] Detta är inte "ny funktionalitet" – det är ett UX-skal för att visa att deletion är seriöst

#### 2.5 Acceptance / Bevis

- [ ] Kör i Docker: `docker compose exec api python _verify/verify_secure_delete.py`
- [ ] Verifiera i UI: skapa projekt + fyll med material + delete → projektet försvinner och går inte att nå via URL efteråt
- [ ] Verifiera delete-confirmation flow i browser mode

### Milestone 3 — "Verify Suite" + Make target

#### 3.1 Samla Phase 1 verifieringar

- [ ] Säkerställ att följande scripts finns och kör:
  - `verify_event_no_content_policy.py`
  - `verify_secure_delete.py`
  - (befintliga) `verify_recording_sanitization.py`
  - (befintliga) `verify_transcript_normalization.py`
  - (befintliga) `verify_enhanced_transcript_pipeline.py`

#### 3.2 Lägg till "one command"

- [ ] Lägg till `make verify-security-phase1` (eller motsvarande) som kör samtliga scripts i rätt ordning i Docker
- [ ] Output ska tydligt visa PASS/FAIL per script

#### 3.3 Acceptance / Bevis

- [ ] Kör: `make verify-security-phase1` → allt PASS i Docker

### Definition of Done (Phase 1)

- [ ] Events kan inte råka innehålla content eller source identifiers (bevisat via verify-script)
- [ ] Secure delete tar bort DB + filstore och lämnar 0 orphans (bevisat via verify-script)
- [ ] Allt går att verifiera med ett kommando i Docker
- [ ] Browser-mode smoke test: skapa → arbeta → delete → inte nåbart efteråt

### "No guessing" regler (som Cursor måste följa)

- Alla förändringar ska peka på exakt fil + rad där det ändrades
- Inga "jag tror" – varje claim måste ha ett verifieringssteg
- Inga UI-ändringar utan browser-verifiering

## Scope

**Vad som ingår:**

- Event "no content" enforcement (Privacy Guard integration)

- Secure Delete med filstore wipe och verifiering

- Verifieringsscript för alla security-invariants

- Fail-closed policy vid osäkerhet

- Delete-confirmation UX (minimal, för demo-trovärdighet)

**Vad som INTE ingår:**

- Extern AI-integration (Security Core förblir dormant)

- Ersättning av befintlig masking (text_processing.py förblir aktiv)

- Ny datamodell eller migrationer

## Definitions & Guardrails

### Förbjudna fält i Events/Logs/Audit

**Content-nycklar (aldrig tillåtna):**
- `body`, `text`, `content`, `transcript`, `note_body`, `file_content`, `payload`, `query_params`, `query`, `segment_text`, `transcript_text`, `file_data`, `raw_content`, `original_text`, `headers`, `authorization`, `cookie`

**Source identifier-nycklar (aldrig tillåtna när `SOURCE_SAFETY_MODE=true`):**
- `ip`, `ip_address`, `client_ip`, `remote_addr`, `x-forwarded-for`, `x-real-ip`, `user_agent`, `user-agent`, `referer`, `referrer`, `origin`, `url`, `uri`, `filename`, `filepath`, `file_path`, `original_filename`, `querystring`, `query_string`, `cookies`, `cookie`, `headers`, `host`, `hostname`

**Tillåtna metadata (exempel):**
- `project_id`, `document_id`, `note_id`, `event_type`, `actor`, `count`, `size`, `mime`, `duration_seconds`, `sanitize_level`, `classification`

**Källa:** `apps/api/security_core/privacy_guard.py` (`_FORBIDDEN_CONTENT_KEYS`, `_FORBIDDEN_SOURCE_KEYS`)

### DEV vs PROD Mode

**Env-flagga:** `DEBUG` (default: `false`)

**Beteende:**
- **DEV mode** (`DEBUG=true`): `assert_no_content()` raises `AssertionError` vid förbjudna nycklar (fail-closed, hårdt stopp)
- **PROD mode** (`DEBUG=false`): `sanitize_for_logging()` droppar förbjudna fält tyst, fortsätter (fail-closed, mjukt stopp)

**Verifiering:**
- Verify-scripts körs i **DEV mode** för att bevisa fail-closed hårt
- Optional: testfall som visar PROD "drops" utan crash

**Källa:** `apps/api/security_core/config.py` (`debug = os.getenv("DEBUG", "false").lower() == "true"`)

## Inventory: copy-pastev2 Security Modules

### 1. Privacy Guard (Event Policy)

**Filer:**
- `copy-pastev2/backend/app/core/privacy_guard.py`
- `copy-pastev2/backend/app/modules/transcripts/service.py` (användning)
- `copy-pastev2/backend/app/modules/record/service.py` (användning)
- `copy-pastev2/backend/app/modules/projects/router.py` (användning)

**Vad gör den:**
- `sanitize_for_logging()` - Rensar content och source identifiers från metadata
- `assert_no_content()` - Strikt kontroll att data inte innehåller förbjudna nycklar
- Fail-closed: DEV mode raises AssertionError, PROD mode drops fields

**Hur används den:**
- ALLA event-metadata går via `sanitize_for_logging()` + `assert_no_content()`
- Exempel: `audit_metadata = sanitize_for_logging({"title": title}, context="audit")` → `assert_no_content(audit_metadata, context="audit")`

**Status i Arbetsytan:**
- ✅ Porterad till `apps/api/security_core/privacy_guard.py` (identisk implementation)
- ❌ Används INTE i events (ingen enforcement)

### 2. Secure Delete (Purge + File Wipe)

**Filer:**
- `copy-pastev2/backend/app/modules/record/purge.py` (purge_expired_records)
- `copy-pastev2/backend/app/modules/transcripts/service.py` (delete_transcript)
- `copy-pastev2/backend/app/modules/projects/file_storage.py` (delete_file)

**Vad gör den:**
- Hard delete med CASCADE i DB
- Filstore wipe (tar bort alla filer från disk)
- Verifiering att inga orphans finns kvar
- Idempotent (kan köras flera gånger säkert)

**Hur används den:**
- `purge_expired_records()` - GDPR retention purge
- `delete_transcript()` - Hard delete med filstore wipe
- Verifiering: räknar filer före/efter, kontrollerar att alla är borta

**Status i Arbetsytan:**
- ✅ `delete_project()` finns i `apps/api/main.py:219`
- ❌ Saknar filstore wipe verifiering
- ❌ Saknar orphan detection
- ❌ Använder `os.remove()` utan verifiering

### 3. Verification Scripts

**Filer:**
- `copy-pastev2/scripts/test_purge.py`
- `copy-pastev2/scripts/comprehensive_security_test.py`
- `copy-pastev2/scripts/check_security_invariants.py`

**Vad gör de:**
- Testar event "no content" policy
- Testar secure delete med verifiering
- Testar filstore wipe
- Körs i Docker för reproducerbarhet

**Status i Arbetsytan:**
- ✅ Verifieringsscript finns i `apps/api/_verify/`
- ❌ Saknar script för event policy enforcement
- ❌ Saknar script för secure delete verifiering

## Gap Analysis: Arbetsytan

### Gap 1: Event "No Content" Enforcement

**Nuvarande:**
- Events skapas med `event_metadata` direkt (t.ex. `{"name": project.name}`)
- Ingen `assert_no_content()` kontroll
- Risk: content kan läcka i events

**Behöver:**
- Integrera `privacy_guard.assert_no_content()` i alla event-skapande
- Använda `sanitize_for_logging()` för metadata
- Fail-closed: raise AssertionError i DEV, drop fields i PROD

**Filer att ändra:**
- `apps/api/main.py` - alla `ProjectEvent` skapande (rad 135, 207, 294, 428, 694, 812, 1079)

### Gap 2: Secure Delete Verifiering

**Nuvarande:**
- `delete_project()` tar bort filer med `os.remove()` men verifierar inte
- Ingen orphan detection
- Ingen verifiering att alla filer är borta

**Behöver:**
- Verifiera filstore wipe (räkna filer före/efter)
- Detektera orphans (filer utan DB-referens)
- Fail-closed: om verifiering misslyckas, logga fel och blockera delete

**Filer att ändra:**
- `apps/api/main.py:219` - `delete_project()` funktion

### Gap 3: Verification Scripts

**Nuvarande:**
- Verifieringsscript finns men saknar event policy och secure delete tests

**Behöver:**
- `verify_event_no_content_policy.py` - testar att events aldrig innehåller content
- `verify_secure_delete.py` - testar secure delete med filstore wipe

**Filer att skapa:**
- `apps/api/_verify/verify_event_no_content_policy.py`
- `apps/api/_verify/verify_secure_delete.py`

## Milestones

### Milestone 1: Event "No Content" Enforcement ✅ COMPLETED

**Mål:** Alla events ska gå via Privacy Guard med fail-closed policy.

**Filer att ändra:**
- ✅ `apps/api/main.py` - lägg till imports och enforcement i alla event-skapande

**Acceptance criteria:**
- ✅ Alla `ProjectEvent` skapande använder `sanitize_for_logging()` + `assert_no_content()` (via `_safe_event_metadata()`)
- ✅ Test: försök skapa event med `{"text": "content"}` → AssertionError i DEV
- ✅ Test: försök skapa event med `{"filename": "secret.pdf"}` → AssertionError i DEV (source identifier)
- ✅ Verifieringsscript: `verify_event_no_content_policy.py` passerar

**Verifiering:**
```bash
docker compose exec -e DEBUG=true api python _verify/verify_event_no_content_policy.py
# Expected: ✅ ALL TESTS PASSED
# Result: ✅ PASSED (4/4 tests passed, 2025-01-02)
```

**Implementation notes:**
- Created helper function `_safe_event_metadata()` in `main.py` (line 18-34)
- Updated all 11 `ProjectEvent` creations to use `_safe_event_metadata()`
- Removed forbidden keys: `filename` from `document_uploaded` and `note_image_added` events
- Created verification script: `apps/api/_verify/verify_event_no_content_policy.py`

### Milestone 2: Secure Delete med Verifiering ✅ COMPLETED

**Mål:** `delete_project()` ska verifiera filstore wipe och detektera orphans.

**Filer att ändra:**
- ✅ `apps/api/main.py:240` - `delete_project()` funktion

**Acceptance criteria:**
- ✅ Räknar filer före delete (documents, recordings, journalist note images)
- ✅ Tar bort alla filer från disk
- ✅ Verifierar att alla filer är borta (ingen orphan)
- ✅ Loggar endast metadata (antal filer, inga filnamn/paths)
- ✅ Fail-closed: om verifiering misslyckas, logga fel och blockera delete

**Verifiering:**
```bash
docker compose exec api python _verify/verify_secure_delete.py
# Expected: ✅ ALL TESTS PASSED
# Result: ✅ PASSED (3/3 tests passed, 2025-01-02)
```

**Implementation notes:**
- Implemented 5-phase secure delete:
  1. Count all files (documents, recordings, journalist note images)
  2. Delete files from disk
  3. Verify no orphans remain (fail-closed if orphans detected)
  4. Delete DB records (CASCADE)
  5. Log only metadata (privacy-safe)
- HTTPException(500) raised if orphans detected
- Created verification script: `apps/api/_verify/verify_secure_delete.py`

### Milestone 3: Verification Scripts ✅ COMPLETED

**Mål:** Komplett verifieringssuite för alla security-invariants.

**Filer att skapa:**
- ✅ `apps/api/_verify/verify_event_no_content_policy.py`
- ✅ `apps/api/_verify/verify_secure_delete.py`
- ✅ `Makefile` - `verify-security-phase1` target

**Acceptance criteria:**
- ✅ Script kan köras i Docker
- ✅ Script testar fail-closed behavior
- ✅ Script verifierar att inga content/source identifiers läcker
- ✅ Script verifierar filstore wipe

**Verifiering:**
```bash
make verify-security-phase1
# Expected: Alla verifieringsscript passerar
# Result: ✅ PASSED (7/7 tests passed, 2025-01-02)
```

**Implementation notes:**
- Created `verify_event_no_content_policy.py` (4 tests)
- Created `verify_secure_delete.py` (3 tests)
- Added `make verify-security-phase1` target to Makefile
- All tests run in Docker with DEBUG=true for fail-closed proof

## Implementation Order

1. **Milestone 1** (Event enforcement) - Maximal effekt, minimal risk
2. **Milestone 2** (Secure delete) - Kräver Milestone 1 för logging
3. **Milestone 3** (Verification scripts) - Verifierar Milestone 1+2

## Risker och Mitigering

**Risk 1: Breaking changes i events**
- Mitigering: Testa i Docker först, behåll backward compatibility i metadata-struktur

**Risk 2: Filstore paths olika mellan copy-pastev2 och Arbetsytan**
- Mitigering: Använd `UPLOAD_DIR` från Arbetsytan, adaptera path-logik

**Risk 3: Olika datamodell (Project vs Record)**
- Mitigering: Adaptera delete-logik för Project-struktur (documents, recordings, notes, images)

## "No Guessing" Policy

Alla claims har referens:
- Event enforcement: `copy-pastev2/backend/app/modules/transcripts/service.py:674` (assert_no_content usage)
- Secure delete: `copy-pastev2/backend/app/modules/record/purge.py:25` (purge_expired_records)
- Privacy Guard: `copy-pastev2/backend/app/core/privacy_guard.py:140` (assert_no_content implementation)

## "Fail-Closed" Policy

- Event enforcement: DEV mode raises AssertionError, PROD mode drops fields
- Secure delete: Om verifiering misslyckas, blockera delete och logga fel
- Verification scripts: Alla tester måste passa, annars fail

