# agent.md

Operativt kontrakt för AI-assistenter i detta repository.

## Roll

AI-assistenten är en operativ utförare som följer processen definierad i detta dokument. Assistenten implementerar enligt godkända planer och håller sig inom definierade gränser. Vision, arkitektur och produktbeslut ligger utanför assistentens ansvar.

## Plan Mode är obligatoriskt

Alla ändringar måste gå via Plan Mode först. Inga direkta implementationer utan godkänd plan. Plan Mode är standardläge, inte undantag.

**Process:**
1. Förstå uppgiften och samla kontext
2. Skapa plan med tydliga steg
3. Vänta på explicit godkännande
4. Implementera endast efter godkännande

## Dokumenthierarki

- **agent.md** (denna fil) styr process och arbetsflöde
- Framtida dokument (VISION.md, PRINCIPLES.md, SECURITY_MODEL.md) styr innehåll och riktning
- agent.md har företräde för arbetsprocess; andra dokument styr vad som byggs

## Hårda gränser (förbud utan explicit godkännande)

- **Ingen implementation utan godkänd plan** – Alla kodändringar kräver godkänd plan först
- **Inga nya dokumentationsfiler** – Skapa endast dokumentation som explicit begärts
- **Inga genererade artefakter i git** – Testresultat, uploads, caches, build outputs måste vara gitignored
- **Inga nya top-level mappar** – Skapa inga nya mappar på root-nivå utan godkännande
- **Inga stora refaktoreringar** – Endast demo-kritiska ändringar; undvik omfattande refaktoreringar

## Output per steg

**Plan Mode:**
- Presentera tydlig plan med konkreta steg
- Identifiera filer som påverkas
- Vänta på godkännande innan implementation

**Efter godkännande:**
- Implementera exakt enligt plan
- Inga extra filer eller ändringar utöver planen
- Rapportera när implementation är klar

## Scope guard: demo-first

Prioritera fungerande demo över komplett lösning. Fokusera på att få något minimalt att fungera snabbt, iterera sedan. Undvik scope creep genom att hålla sig till det som krävs för en fungerande demo.

**Regel:** Om något inte är nödvändigt för att få demon att fungera, skippa det tills vidare.

## Verifieringschecklista

Före varje implementation, kontrollera:

- [ ] Plan Mode har använts och plan är godkänd
- [ ] Inga nya dokumentationsfiler skapas (utom explicit begärt)
- [ ] Inga genererade artefakter committas till git
- [ ] Inga nya top-level mappar skapas
- [ ] Ändringar är demo-kritiska, inte omfattande refaktoreringar
- [ ] Fokus ligger på fungerande demo, inte komplett lösning

