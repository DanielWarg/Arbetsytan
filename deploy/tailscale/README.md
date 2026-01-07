## Tailscale Funnel demo-deploy (en domän, HTTPS, inga publika portar)

Mål:
- `https://{DOMAIN_ROOT}/` → Frontend (Vite build, statiskt)
- `https://{DOMAIN_ROOT}/api/*` → FastAPI backend

All routing sker lokalt via **Caddy**. TLS hanteras av **Tailscale Funnel** (ingen egen TLS i Caddy).

### Förutsättningar
- Tailscale installerat och inloggat
- Docker Desktop (med `docker-compose`)
- Node.js (för `npm ci` + `npm run build`)
- (Caddy körs som docker-service, ingen separat installation behövs)

### Setup
Skapa din lokala env-fil (gitignored):

```bash
cp deploy/tailscale/env.example deploy/tailscale/.env
```

Uppdatera minst:
- `DOMAIN_ROOT`
- `CORS_ALLOW_ORIGINS` (ska matcha `https://{DOMAIN_ROOT}`)
- `BASIC_AUTH_PASS`
- `POSTGRES_PASSWORD` + `DATABASE_URL`

### Start

```bash
make prod-up
```

Lokalt (utan TLS):
- `http://localhost:8443/`
- `http://localhost:8443/api/health`

### Exponera över HTTPS (en domän, ingen subdomän)
Kör manuellt (ingen kod):

```bash
tailscale funnel 443 localhost:8443
```

Öppna:
- `https://{DOMAIN_ROOT}/`
- `https://{DOMAIN_ROOT}/api/health`

Stoppa Funnel:

```bash
tailscale funnel off
```

### Stop

```bash
make prod-down
```

### Logs

```bash
make prod-logs
```

### Smoke test (kräver aktiv Funnel)

```bash
make prod-smoke
```

### Felsökning
- **Caddy startar inte**: kontrollera att `caddy` finns i PATH och att port `8443` är ledig.
- **Funnel inte aktiv**: kör `tailscale status` och `tailscale funnel status`.
- **Backend 500**: `make prod-logs` och se `api`-containerns log (inga råtexter ska loggas).
- **CORS**: säkerställ `CORS_ALLOW_ORIGINS=https://{DOMAIN_ROOT}` i `deploy/tailscale/.env`.

