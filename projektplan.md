## Projektplan (showreel polish)

Det här dokumentet är **styrande** för arbetet i repo:t. Vi bygger inte fler features förrän polish‑passet är klart.

### Principer (låsta)
- **Konsekvent UI**: samma komponent-familj överallt (knappar, inputs, cards, modals).
- **Stabilt & tryggt**: tydliga tomlägen/loading/error, inga “råa” stacktraces i UI.
- **Showreel‑säkert**: inga secrets i repo, inga raw content i loggar.
- **Minsta ändring som ger maximal effekt**.

### Phase 1 (status)
- [x] Projektstatus (redaktionellt läge)
- [x] Källor / referenser
- [x] Export / avslut
- [x] Röstmemo/transkription som dokument
- [x] Fort Knox “External” gate (datum maskas i pipeline, datum blockar inte)
- [x] Fort Knox: spara rapport som dokument (intern/extern)

### Showreel polish sprint (nu)
- [x] **Design-system light**: enhetliga `Button`, `Input`, `Select`, `Card`, `Modal` i alla nyckelvyer
- [ ] **Spacing/typografi**: harmonisera rubriker, padding, list‑layout så det känns “premium”
- [x] **Tomlägen/loading/error**: polera i Scout, Projekt, Fort Knox (samma ton och layout)
- [ ] **Copy-pass**: konsekvent svenska (ex: “Research/Bearbetning/Faktakoll/Klar/Arkiverad”)
- [x] **Responsivitet**: laptop-bredd + mindre (toolbar-wrap, modals, listor)
- [x] **Demo-check**: en snabb “happy path” genom hela appen utan visuella glitchar

### Tekniska regler
- UI-komponenter ska bo i `apps/web/src/ui/`.
- Undvik duplicerad knapp‑CSS i pages/components – använd `.btn*` där det går.

