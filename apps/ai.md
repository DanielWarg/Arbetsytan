PLAN MODE ONLY. Follow agent.md at all times. Do not implement yet.

Mål: Lägg upp “Local AI Summary” (FAS 5.5) via ett externt lokalt gränssnitt som INTE är Ollama.

Krav:

Välj llama.cpp server som primär runtime (OpenAI-liknande eller native HTTP), eftersom Ollama-versionen inte stödjer modellen.

Definiera ett backend-interface LocalLLMClient (summarize only) som kan byta runtime senare.

Inkludera fail-closed rules:

Only masked_text is ever sent.

If any document has ai_allowed=false → local AI summary disabled.

Lägg in timeouts (t.ex. 20s) och “fallback to deterministic brief” om LLM inte svarar.

Specificera exakt:

nya config env vars (LLM_BASE_URL, LLM_MODEL_NAME, LLM_TIMEOUT)

exakt endpoint/contract vi pratar med (request/response JSON)

vilka filer i Arbetsytan som ändras (backend + frontend)

Ingen ny top-level mapp.

Leverera:

Exakt plan (stegordning)

API-kontrakt för POST /api/projects/{id}/summaries?mode=local_ai

Minimal “smoke test” i runbook (en deterministic payload, förväntad shape)
STOP.