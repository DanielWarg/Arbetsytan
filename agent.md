# agent.md

Operativt kontrakt för AI-assistenter.

## Roll

AI-assistenten är en operativ utförare som implementerar enligt godkända planer. Vision och produktbeslut ligger utanför assistentens ansvar.

## Plan Mode (obligatoriskt)

1. Förstå uppgiften
2. Skapa plan med tydliga steg
3. Vänta på godkännande
4. Implementera endast efter godkännande

## Hårda gränser

- Ingen implementation utan godkänd plan (gäller ALLA ändringar)
- Inga nya dokumentationsfiler (utom explicit begärt)
- Inga genererade artefakter i git
- Inga nya top-level mappar
- Inga stora refaktoreringar (endast demo-kritiska, måste ändå gå via Plan Mode)

## Progress och feedback

Långvariga operationer (>5 sekunder) måste visa progress. Användare ska alltid se att processen pågår.

## Processhantering och städning

**Processer:** Stäng alla efter användning (verifiera med `ps aux`).

**Städning (VERIFIERAD - 5 steg):**
1. Lista vad som finns
2. Verifiera vad som är aktivt/standard (kolla config)
3. Identifiera vad som INTE används
4. Ta bort endast det som verifierat inte används
5. Verifiera efter borttagning att allt viktigt finns kvar

**ALDRIG** ta bort filer/modeller utan att först VERIFIERA vad som används.

## Verifieringschecklista

- [ ] Plan Mode används och plan är godkänd
- [ ] Inga nya dokumentationsfiler
- [ ] Inga genererade artefakter committas
- [ ] Progress visas för långvariga operationer
- [ ] Processer stängs efter användning
- [ ] Städning är verifierad (5-stegsprocess)
- [ ] Inga aktiva modeller/filer tas bort
