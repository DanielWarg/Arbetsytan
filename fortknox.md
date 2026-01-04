Ja. Fort Knox kan bli “den enda platsen där text får lämna arbetsytan” – men bara i en form som är **bevisligen icke-PII** och **policy-styrd**. Här är ett spår som är både säljigt och tekniskt realistiskt.

### Fort Knox i en mening

**En låst sammanställningskammare** som tar emot *endast* sanitiserad, PII-fri text från ditt projekt, kör en **lokal LLM** för att skapa en rapport, och kan (om du vill) exportera en “extern version” som aldrig kan innehålla personuppgifter.

---

## Grundprinciper (så det blir “security by default” på riktigt)

1. **Enkelriktad data**
   Arbetsytan → Fort Knox. Aldrig tvärtom. Inga råa original i Fort Knox.

2. **Fail-closed i två lager**

   * Lager 1: din befintliga PII-pipeline (normal/strict/paranoid + gate) innan något ens får skickas.
   * Lager 2: Fort Knox kör en **egen gate** på allt som kommer in (och på allt som ska ut). Om något triggar: stopp.

3. **Minimerad dataprodukt**
   Fort Knox får inte “hela projektet”. Den får:

   * masked_text (paranoid när det behövs)
   * minimal metadata (typ doc_id + typ + datum)
   * **inga länkar till originalfiler**, inga filvägar, ingen råtext.

4. **Deterministiska “export-kontrakt”**
   Fort Knox producerar bara format som du kan revidera deterministiskt:

   * “Kundrapport v1” (mallstyrd)
   * “Internt PM”
   * “Extern sammanfattning (PII-fri)”

---

## Hur det kan se ut som produkt (och hur du förklarar det)

### Fort Knox-lägen (enkla och tydliga i UI)

* **Intern sammanställning (lokal)**
  Kör lokala modellen, skapar längre rapport som fortfarande är PII-fri men mer detaljerad.
* **Extern sammanställning (hård)**
  Extra hårda regler: inga datum i kombination med händelser som kan identifiera, inga unika citat, inga namn/roller utöver generiska.
* **Citatförbud**
  Förbjud att output innehåller exakta citat längre än typ 8 ord (så du minskar re-identifiering).

---

## Teknisk design (minimal men robust)

### 1) Fort Knox som separat “silo”

En egen backend-modul/service:

* `/api/fortknox/compile` → tar projekt_id + “policy” + “template”
* Den hämtar endast `Document.masked_text` + restrictions.
* Kör lokal LLM (Ollama / llama.cpp) och genererar `KnoxReport`.

### 2) KnoxPolicy = hjärtat

En policy som alltid skickas med:

* max detaljnivå
* förbjudna element (namn, personnummer, adresser, kontonummer, unika citat, etc.)
* “risk budget”: om gate triggar mer än N gånger → stoppa och kräva manuell granskning

### 3) Dubbel-output-gate

* Gate på input: “om masked_text inte är minst strict/paranoid enligt regler → vägra”
* Gate på output: kör samma pii_gate_check + extra heuristik (“unikhetsfilter”)

### 4) Audit utan innehåll

Logga aldrig textinnehåll. Logga endast:

* report_id, project_id, policy_id
* hash på indata (ex: sha256 av sammanfogad masked_text)
* timestamps
* gate-resultat (pass/fail + reasons)

Det här blir en stor trygghet i GDPR-snack: “vi loggar inte innehåll”.

---

## Vad Fort Knox faktiskt “sammanställer”

För att det ska vara användbart trots hård sanitization:

* **teman** (3–8 bullets)
* **tidslinje på hög nivå** (“veckan”, “senaste perioden”) utan exakta datum om du väljer extern
* **risker och åtgärder** (generiska)
* **öppna frågor** (vad behöver verifieras)
* **rekommenderade nästa steg** (deterministisk mall)

Och: Fort Knox kan alltid säga “för lite underlag” istället för att gissa.

---

## UI-idé (superenkel och premium)

En knapp i projektet: **“Skapa Fort Knox-rapport”**

* Välj “Intern” eller “Extern”
* Välj mall (Weekly, Incident, Brief)
* Tryck “Kompilera”
* Resultat visas i en låst vy med:

  * “Exportera PDF”
  * “Kopiera”
  * “Visa gate-logg” (pass/fail, men aldrig text)

---

## “Fort Knox” kan vara ditt säljargument

En bra formulering till kund:

> “Fort Knox är vår sammanställningskammare. Inget råmaterial lämnar arbetsytan. Allt som går in och ut måste passera en automatisk integritetsgrind. Om vi inte kan garantera att en rapport är fri från personuppgifter – då produceras den inte.”

---

## Två konkreta varianter att välja på

### Variant A: Fort Knox = intern modul i samma backend

* enklast att bygga
* samma DB
  – svårare att sälja “silo”-känslan

### Variant B: Fort Knox = separat service + separat DB schema

* tydlig isolering
* lättare att prata “Fort Knox perimeter”
  – lite mer infra

Jag lutar B om du vill att det ska kännas “på riktigt”.

---

## Prompt till Cursor för nästa steg i chatten

“Designa och implementera en minimal Fort Knox v1: skapa en separat modul/service (eller tydligt avgränsad package) som kan generera en KnoxReport från ett project_id genom att endast använda Document.masked_text. Inför KnoxPolicy (internal/external), kör dubbel pii_gate (input + output), logga endast audit-metadata (inga texter), och skapa endpoint POST /api/fortknox/compile samt en enkel frontend-knapp i projektvyn som triggar kompilering och visar rapporten. Lägg verify-script som bevisar att Fort Knox vägrar om input/output triggar gate.”

Vill du att Fort Knox också ska kunna göra en “red team-check” (dvs försöka återidentifiera och om den *kan* så stoppar den)? Det är en stark premium-grej, men vi kan hålla v1 enklare.
