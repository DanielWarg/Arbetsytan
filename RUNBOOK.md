# 🧭 Arbetsytan – Runbook (FAS 0–4)

**Syfte:**
Verifiera att Arbetsytan uppfyller alla krav upp till och med **FAS 4 – Narrativ låsning**, utan att behöva tolka eller "känna efter".

**Principer:**
- Demo-first
- Security by default
- Deterministisk verifiering
- STOP/GO per fas

---

## 🧪 FAS 0 – Styrning & disciplin (AUTOMATISK + STATISK)

### Mål
Säkerställa att projektet följer fastställda spelregler.

### Automatiska kontroller

```bash
make verify-fas0
```

**PASS om:**
- Alla filer finns (`agent.md`, `VISION.md`, `PRINCIPLES.md`, `SECURITY_MODEL.md`)
- Inga tomma filer
- `agent.md` innehåller:
  - Plan Mode
  - Demo-first
  - STOP/GO-princip

### Manuell kontroll (1 min)
- Öppna `agent.md`
- Bekräfta att inga undantag lagts till

**Status:** PASS / FAIL
➡️ FAIL = stoppa allt arbete

---

## 🧪 FAS 1 – Core Platform & UI-system (AUTOMATISK)

### Mål
Basen är stabil, körbar och ser professionell ut.

### Automatiska kontroller

```bash
make verify-fas1
```

**PASS om:**
- Frontend laddar utan console errors (`http://localhost:3000`)
- Backend svarar OK (`http://localhost:8000/health`)
- Ingen "dev placeholder"-UI syns
- Alla endpoints svarar korrekt

### UI-smoke-test (manuell, 2 min)
- [ ] Dashboard laddar
- [ ] Projektlista syns
- [ ] "Skapa projekt"-modal öppnas
- [ ] Navigation fungerar

**Status:** PASS / FAIL

---

## 🧪 FAS 2 – Material ingest & läsning (AUTOMATISK)

### Mål
Journalistens kärnflöde fungerar.

### Automatiskt ingest-test

```bash
make verify-fas2
```

**PASS om:**
- Dokument laddas upp (PDF/TXT)
- Dokument visas i projekt
- Read-only view (ingen edit)
- Ingen raw text i frontend HTML
- Dokumentvy saknar input-fält

### Automatisk assert
- Upload endpoint returnerar metadata (inte masked_text)
- GET /api/documents/{id} returnerar masked_text
- Inga raw PII-värden i API responses

**Status:** PASS / FAIL

---

## 🧪 FAS 3 – Progressive Sanitization 🔒 (HELT AUTOMATISK)

### Mål
Bevisa att PII aldrig läcker och att systemet inte är paranoid-by-default.

### Kommando

```bash
make verify-sanitization
```

### Script verifierar:
- Safe document → `sanitize_level = normal|strict` (INTE paranoid)
- `usage_restrictions.ai_allowed == true`
- `usage_restrictions.export_allowed == true`
- Email/phone maskerade (`[EMAIL]`, `[PHONE]`)
- Datum, belopp, målnummer bevarade (inte maskerade)

**PASS om:**
- Alla assertions passerar
- Exit code = 0

➡️ **Detta är en absolut STOP/GO-punkt**
Ingen vidare fas utan PASS här.

**Status:** PASS / FAIL

---

## 🧪 FAS 4 – Narrativ låsning (HALVAUTOMATISK)

Detta är **kommunikation**, så vi kombinerar statisk analys + UI-check.

### 4.1 Statisk verifiering (AUTOMATISK)

```bash
make verify-fas4-static
```

**PASS om:**
- `DEMO_NARRATIVE.md` finns
- Alla låsta formuleringar finns exakt (verbatim) i UI-kod
- Inga alternativa formuleringar hittas

### 4.2 UI-verifiering (MANUELL, CHECKLISTA)

#### DocumentView
- [ ] Texten "Maskad vy" syns
- [ ] Tooltip förklarar att original aldrig exponeras
- [ ] Inga ord som "visa original", "fulltext", "rådata"
- [ ] Formulering matchar DEMO_NARRATIVE.md exakt

#### ProjectDetail
- [ ] Saneringsnivå visas (badge)
- [ ] Tooltip förklarar nivåerna korrekt (normal/strict/paranoid)
- [ ] "AI avstängt" har förklaring – inte bara status
- [ ] Formuleringar matchar DEMO_NARRATIVE.md exakt

#### CreateProject
- [ ] Klassificering förklaras korrekt
- [ ] Ingen överdriven juridisk text
- [ ] Matchar DEMO_NARRATIVE.md exakt

**PASS om:**
- Alla punkter uppfyllda
- Språket känns tryggt, inte tekniskt
- Inga variationer från DEMO_NARRATIVE.md

**Status:** PASS / FAIL

---

## 🟢 SLUTSTATUS FAS 0–4

| Fas   | Status | Typ                  | Kommando                    |
| ----- | ------ | -------------------- | -------------------------- |
| FAS 0 | ?      | Statisk              | `make verify-fas0`          |
| FAS 1 | ?      | Runtime              | `make verify-fas1`          |
| FAS 2 | ?      | Runtime              | `make verify-fas2`           |
| FAS 3 | ?      | Automatisk (kritisk) | `make verify-sanitization`   |
| FAS 4 | ?      | Hybrid               | `make verify-fas4-static`   |

➡️ **Systemet är redo för showreel-modul (FAS 5)** när alla är PASS

**Notering:** FAS 5 (Röstmemo) och FAS 6 (Browser-inspelning) är implementerade och verifierade.

---

## 🧪 FAS 5 – Upload-only Röstmemo + deterministic transcript processor (FRYST)

### Mål
Verifiera att fil-uppladdning av ljudfiler fungerar och att deterministic transcript processor genererar korrekt markdown-format.

**Status:** Klar – fryst

**Notering:** FAS 6 utökar med browser recording + auth/proxy polish.

---

## 🧪 FAS 6 – Röstmemo: Browser-inspelning + upload + ingest (via proxy, inga creds i frontend) (MANUELL CHECKLISTA)

### Mål
Verifiera att MediaRecorder-baserad direktinspelning fungerar korrekt och säkert via proxy, utan credentials i frontend.

**Auth:** Auth hanteras utanför frontend (proxy/basic auth), inga creds i UI.

### Manual checklist

**a) Recording start/stop → POST /recordings (Network):**
- [ ] Klicka "Röstmemo" → "Spela in" → "Starta inspelning"
- [ ] Verifiera att timer startar (mm:ss format)
- [ ] Klicka "Stoppa" (eller vänta till auto-stop vid 30 sek)
- [ ] Verifiera i Network tab (DevTools) att blob skapas
- [ ] Verifiera POST till `/api/projects/{id}/recordings` skickas
- [ ] Verifiera att webm/ogg blob skickas med korrekt MIME-type i request

**b) Dokument skapas och öppnas:**
- [ ] Verifiera att dokument visas i Material-listan med korrekt filnamn
- [ ] Klicka på dokumentet och verifiera att DocumentView öppnas
- [ ] Verifiera att maskerad text visas korrekt (transcript format)

**c) Event metadata:**
- [ ] Verifiera `recording_transcribed` event i API (GET `/api/projects/{id}/events`)
- [ ] Kontrollera att event_metadata innehåller: `mime`, `size`, `recording_file_id`
- [ ] Kontrollera att `duration` finns om tillgänglig
- [ ] **KRITISKT:** Verifiera att INGET raw transcript, textutdrag eller filnamn finns i event

**d) Permission denied / unsupported → fail-closed + knapp "Byt till uppladdning" och fil-upload funkar:**
- [ ] Neka mikrofon-permission i browser (eller använd browser som saknar MediaRecorder)
- [ ] Verifiera att tydligt fel visas med meddelande
- [ ] Verifiera att knapp "Byt till uppladdning" visas
- [ ] Klicka på knappen och verifiera att fil-uppladdning fungerar
- [ ] **KRITISKT:** Ingen silent auto-switch ska ske

**e) Fil-uppladdning (fallback):**
- [ ] Klicka "Ladda upp fil" i mode selector
- [ ] Välj en ljudfil och verifiera att upload fungerar
- [ ] Verifiera att dokument skapas korrekt

**f) Max 30 sek auto-stop:**
- [ ] Starta inspelning och vänta till 30 sek
- [ ] Verifiera att inspelning stoppas automatiskt
- [ ] Verifiera att upload startar automatiskt

**PASS om:**
- Alla punkter (a-f) uppfyllda
- Inga console errors
- Inga raw data läcker i events
- Fail-closed fungerar korrekt
- Proxyn fungerar (relativa anrop `/api/...`)

**Status:** PASS / FAIL

---

## 📌 Rekommendation (nästa steg)

Nästa naturliga utökning av runbooken är:
- **Demo-runbook** ("så klickar Stampen på 5 minuter")

---

## 🚀 Snabbverifiering (alla fas)

```bash
make verify-all
```

Kör alla automatiska verifieringar i sekvens. Stoppar vid första FAIL.

