# SECURITY_MODEL.md

## Grundprincip

**Security by default** – Säkerhet kräver inga användarval; det är standard. Systemet är säkert från start, inte efter konfiguration.

**Maskad vy som standard** – Alla arbetar i maskerad miljö som utgångspunkt. Känslig information är dold tills explicit åtkomst begärs.

**Fail-closed vid osäkerhet** – Vid osäkerhet stängs systemet ner; ingen "fail-open". Bättre att blockera än att exponera känsligt material.

## Två arbetsytor

### Normalyta (maskad)

Standardarbetsmiljö där all känslig information är maskerad. Användare ser strukturerad information utan att exponera källor eller känsliga detaljer.

### Originalyta / Fort Knox

Åtkomst till originalmaterial kräver:

- **Aktiv handling** – Explicit begäran, inga automatismer
- **Tydlig varning** – Systemet varnar innan åtkomst beviljas
- **Tidsbegränsad åtkomst** – Åtkomst upphör automatiskt efter definierad tid
- **Inga previews i listor** – Originalmaterial visas aldrig i listor eller översikter

## Klassificering

Material klassificeras i tre nivåer:

- **Normal** – Allmänt material utan särskild känslighet
- **Känslig** – Material som kräver extra försiktighet
- **Källkänslig** – Material som direkt kan exponera källor

Klassificering påverkar:

- **Text** – Maskering av känsliga delar i normalvy
- **Metadata** – Filnamn, titlar och previews maskeras eller döljs
- **Loggning** – Känsligare material loggas mindre detaljerat
- **Åtkomst** – Strikta åtkomstregler för källkänsligt material

## Roller och åtkomst

- **Owner (reporter)** – Full åtkomst till eget material, kan bevilja åtkomst till andra
- **Editor (maskad åtkomst)** – Kan arbeta med material i maskad vy, begära Fort Knox-åtkomst vid behov
- **Admin (drift)** – Systemadministration, aldrig innehållsåtkomst

## Loggpolicy

**Vad som loggas:**
- Säkerhetshändelser (åtkomstförsök, autentisering)
- Incidenter (fel, avvikelser)
- Systemdrift (tillgänglighet, prestanda)

**Vad som aldrig loggas:**
- Innehåll i material
- Källinformation
- Användaraktivitet för personaluppföljning

Loggar är för säkerhet och incidenthantering, inte för övervakning av användare.

## Extern AI

Extern AI används endast via maskad export:

- **Endast via maskad export** – Inget originalmaterial lämnar systemet
- **Alltid opt-in** – Användare måste explicit godkänna export
- **Ingen rådata lämnar systemet** – Endast maskerat, strukturerat material exporteras

## Designintention

Säkerhetsmodellen är designad för att:

- **Skydda journalistiskt arbete** – Källor och material skyddas från exponering
- **Minimera risken att göra fel** – Standardinställningar är säkra; fel kräver aktiv handling
- **Göra rätt beteende till standard** – Säkerhet är default, inte valfritt

