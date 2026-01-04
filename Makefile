.PHONY: dev up down verify clean verify-fas0 verify-fas1 verify-fas2 verify-fas4-static verify-all verify-transcription-quality verify-projects-e2e verify-feed-import

dev:
	@echo "Starting development environment..."
	docker-compose up --build

up:
	@echo "Starting production environment..."
	docker-compose up -d --build

down:
	@echo "Stopping all services..."
	docker-compose down

verify:
	@echo "Running smoke tests..."
	@echo "Testing /health endpoint..."
	@curl -s http://localhost:8000/health | grep -q "ok" && echo "✓ Health check passed" || (echo "✗ Health check failed" && exit 1)
	@echo "Testing /api/hello endpoint (with auth)..."
	@curl -s -u admin:password http://localhost:8000/api/hello | grep -q "Hello" && echo "✓ Hello endpoint passed" || (echo "✗ Hello endpoint failed" && exit 1)
	@echo "Creating project..."
	@PROJECT_ID=$$(curl -s -u admin:password -X POST http://localhost:8000/api/projects \
		-H "Content-Type: application/json" \
		-d '{"name":"Test Project","description":"Test description","classification":"normal"}' \
		| grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1) && \
		echo "✓ Project created (ID: $$PROJECT_ID)" || (echo "✗ Project creation failed" && exit 1)
	@echo "Listing projects..."
	@curl -s -u admin:password http://localhost:8000/api/projects | grep -q "Test Project" && echo "✓ List projects passed" || (echo "✗ List projects failed" && exit 1)
	@echo "Adding event..."
	@PROJECT_ID=$$(curl -s -u admin:password http://localhost:8000/api/projects | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1) && \
		curl -s -u admin:password -X POST http://localhost:8000/api/projects/$$PROJECT_ID/events \
		-H "Content-Type: application/json" \
		-d '{"event_type":"test_event","metadata":{"key":"value"}}' | grep -q "test_event" && \
		echo "✓ Add event passed" || (echo "✗ Add event failed" && exit 1)
	@echo "Fetching events..."
	@PROJECT_ID=$$(curl -s -u admin:password http://localhost:8000/api/projects | grep -o '"id":[0-9]*' | grep -o '[0-9]*' | head -1) && \
		curl -s -u admin:password http://localhost:8000/api/projects/$$PROJECT_ID/events | grep -q "test_event" && \
		echo "✓ Fetch events passed" || (echo "✗ Fetch events failed" && exit 1)
	@echo "All smoke tests passed!"

verify-sanitization:
	@echo "Running sanitization verification test..."
	@docker-compose exec -T api python3 /app/_verify/verify_sanitization.py || \
		(echo "Note: If containers are not running, start with 'make dev' first" && exit 1)

verify-fas0:
	@echo "=== FAS 0: Styrning & disciplin ==="
	@test -f agent.md && echo "✓ agent.md exists" || (echo "✗ agent.md missing" && exit 1)
	@test -f VISION.md && echo "✓ VISION.md exists" || (echo "✗ VISION.md missing" && exit 1)
	@test -f PRINCIPLES.md && echo "✓ PRINCIPLES.md exists" || (echo "✗ PRINCIPLES.md missing" && exit 1)
	@test -f SECURITY_MODEL.md && echo "✓ SECURITY_MODEL.md exists" || (echo "✗ SECURITY_MODEL.md missing" && exit 1)
	@test -s agent.md && echo "✓ agent.md is not empty" || (echo "✗ agent.md is empty" && exit 1)
	@grep -q "Plan Mode" agent.md && echo "✓ agent.md contains 'Plan Mode'" || (echo "✗ agent.md missing 'Plan Mode'" && exit 1)
	@grep -q "demo-first\|demo first" agent.md && echo "✓ agent.md contains 'demo-first'" || (echo "✗ agent.md missing 'demo-first'" && exit 1)
	@echo "✓ FAS 0 PASS"

verify-fas1:
	@echo "=== FAS 1: Core Platform & UI-system ==="
	@echo "Testing backend health..."
	@curl -s http://localhost:8000/health | grep -q "ok" && echo "✓ Backend health check passed" || (echo "✗ Backend health check failed" && exit 1)
	@echo "Testing frontend availability..."
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200" && echo "✓ Frontend responds" || (echo "✗ Frontend not responding" && exit 1)
	@echo "Testing API endpoints..."
	@curl -s -u admin:password http://localhost:8000/api/projects | grep -q "projects\|id" && echo "✓ API projects endpoint works" || (echo "✗ API projects endpoint failed" && exit 1)
	@echo "✓ FAS 1 PASS"

verify-fas2:
	@echo "=== FAS 2: Material ingest & läsning ==="
	@echo "Testing document upload..."
	@PROJECT_ID=$$(curl -s -u admin:password -X POST http://localhost:8000/api/projects \
		-H "Content-Type: application/json" \
		-d '{"name":"FAS2 Test","classification":"normal"}' \
		| grep -o '"id":[0-9]*' | cut -d: -f2 | head -1); \
		echo "✓ Test project created (ID: $$PROJECT_ID)"; \
		echo "Uploading test document..."; \
		DOC_RESPONSE=$$(curl -s -u admin:password -X POST http://localhost:8000/api/projects/$$PROJECT_ID/documents \
			-F "file=@apps/api/_verify/safe_document.txt"); \
		DOC_ID=$$(echo "$$DOC_RESPONSE" | grep -o '"id":[0-9]*' | cut -d: -f2 | head -1); \
		if [ -z "$$DOC_ID" ]; then \
			echo "✗ Document upload failed or ID not found"; \
			exit 1; \
		fi; \
		echo "✓ Document uploaded (ID: $$DOC_ID)"; \
		echo "Verifying document metadata (no masked_text in list)..."; \
		if curl -s -u admin:password http://localhost:8000/api/projects/$$PROJECT_ID/documents | grep -q "masked_text"; then \
			echo "✗ masked_text found in list response (should not be)"; \
			exit 1; \
		fi; \
		echo "✓ masked_text not in list response"; \
		echo "Verifying document view (masked_text in detail)..."; \
		if ! curl -s -u admin:password http://localhost:8000/api/documents/$$DOC_ID | grep -q "masked_text\|EMAIL\|PHONE"; then \
			echo "✗ masked_text missing in detail response"; \
			exit 1; \
		fi; \
		echo "✓ masked_text present in detail response"; \
		echo "✓ FAS 2 PASS"

verify-fas4-static:
	@echo "=== FAS 4: Narrativ låsning (statisk) ==="
	@test -f DEMO_NARRATIVE.md && echo "✓ DEMO_NARRATIVE.md exists" || (echo "✗ DEMO_NARRATIVE.md missing" && exit 1)
	@echo "Checking for locked formulations in UI..."
	@grep -r "All känslig information är automatiskt maskerad" apps/web/src 2>/dev/null && echo "✓ 'All känslig information är automatiskt maskerad' found" || (echo "✗ Masked view explanation not found" && exit 1)
	@grep -r "Maskad vy" apps/web/src 2>/dev/null && echo "✓ 'Maskad vy' found in UI" || (echo "✗ 'Maskad vy' not found in UI" && exit 1)
	@grep -r "Klassificering påverkar åtkomst" apps/web/src 2>/dev/null && echo "✓ Classification explanation found" || (echo "✗ Classification explanation not found" && exit 1)
	@grep -r "Normal: Standard sanering" apps/web/src 2>/dev/null && echo "✓ Sanitization level (Normal) explanation found" || (echo "✗ Sanitization level (Normal) not found" && exit 1)
	@grep -r "Strikt: Ytterligare numeriska sekvenser" apps/web/src 2>/dev/null && echo "✓ Sanitization level (Strikt) explanation found" || (echo "✗ Sanitization level (Strikt) not found" && exit 1)
	@grep -r "Paranoid: Alla siffror och känsliga mönster" apps/web/src 2>/dev/null && echo "✓ Sanitization level (Paranoid) explanation found" || (echo "✗ Sanitization level (Paranoid) not found" && exit 1)
	@grep -r "AI avstängt" apps/web/src 2>/dev/null && echo "✓ 'AI avstängt' found in UI" || (echo "✗ 'AI avstängt' not found in UI" && exit 1)
	@grep -r "Dokumentet krävde paranoid sanering" apps/web/src 2>/dev/null && echo "✓ AI disabled explanation found" || (echo "✗ AI disabled explanation not found" && exit 1)
	@echo "Note: 'Originalmaterial bevaras i säkert lager' should be added to DocumentView tooltip (see DEMO_NARRATIVE.md)"
	@echo "✓ FAS 4 (static) PASS"

verify-fas4-5:
	@echo "=== FAS 4.5: Editorial Control Layer ==="
	@echo "Testing due_date in project responses..."
	@PROJECT_ID=$$(curl -s -u admin:password -X POST http://localhost:8000/api/projects \
		-H "Content-Type: application/json" \
		-d '{"name":"FAS4.5 Test","classification":"normal","due_date":"2025-12-31T00:00:00Z"}' \
		| grep -o '"id":[0-9]*' | cut -d: -f2 | head -1); \
		if [ -z "$$PROJECT_ID" ]; then \
			echo "✗ Project creation failed"; \
			exit 1; \
		fi; \
		echo "✓ Project created (ID: $$PROJECT_ID)"; \
		if ! curl -s -u admin:password http://localhost:8000/api/projects/$$PROJECT_ID | grep -q "due_date"; then \
			echo "✗ due_date missing in project response"; \
			exit 1; \
		fi; \
		echo "✓ due_date present in project response"; \
		echo "Testing project edit (PUT)..."; \
		if ! curl -s -u admin:password -X PUT http://localhost:8000/api/projects/$$PROJECT_ID \
			-H "Content-Type: application/json" \
			-d '{"name":"FAS4.5 Test Updated"}' | grep -q "FAS4.5 Test Updated"; then \
			echo "✗ Project edit failed"; \
			exit 1; \
		fi; \
		echo "✓ Project edit works"; \
		echo "Testing project delete (DELETE)..."; \
		DELETE_STATUS=$$(curl -s -u admin:password -X DELETE http://localhost:8000/api/projects/$$PROJECT_ID -w "%{http_code}" -o /dev/null); \
		if [ "$$DELETE_STATUS" != "204" ]; then \
			echo "✗ Project delete failed (status: $$DELETE_STATUS, expected 204)"; \
			exit 1; \
		fi; \
		echo "✓ Project delete works (status: 204)"; \
		echo "✓ FAS 4.5 PASS"

verify-projects-e2e:
	@echo "=== Projects E2E Verification ==="
	@docker-compose exec -T api python3 /app/_verify/verify_projects_e2e.py || \
		(echo "Note: If containers are not running, start with 'make dev' first" && exit 1)

verify-transcription-quality:
	@echo "=== Transcription Quality Verification ==="
	@echo "Note: This may take 3-10 minutes with large-v3 (first run downloads model)"
	@echo "      If this hangs, run directly in container:"
	@echo "      docker exec arbetsytan-api-1 python3 /app/_verify/verify_transcription_quality.py"
	@docker-compose exec -T api python3 /app/_verify/verify_transcription_quality.py || \
		(echo "" && \
		 echo "Note: If containers are not running, start with 'make dev' first" && \
		 echo "      If timeout occurred, run directly in container:" && \
		 echo "      docker exec arbetsytan-api-1 python3 /app/_verify/verify_transcription_quality.py" && \
		 exit 1)

verify-security-phase1:
	@echo "======================================================================"
	@echo "PHASE 1: SECURITY BY DESIGN - Verification Suite"
	@echo "======================================================================"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "TEST 1/2: Event No Content Policy"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T -e DEBUG=true api python _verify/verify_event_no_content_policy.py || \
		(echo "✗ Event No Content Policy verification FAILED" && exit 1)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "TEST 2/2: Secure Delete Policy"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T api python _verify/verify_secure_delete.py || \
		(echo "✗ Secure Delete Policy verification FAILED" && exit 1)
	@echo ""
	@echo "======================================================================"
	@echo "✅ PHASE 1 VERIFICATION COMPLETE - All security policies enforced"
	@echo "======================================================================"
	@echo "Event No Content: ✅ PASS"
	@echo "Secure Delete: ✅ PASS"
	@echo ""

verify-all:
	@echo "🧭 Running all FAS 0-4 verifications..."
	@$(MAKE) verify-fas0
	@$(MAKE) verify-fas1
	@$(MAKE) verify-fas2
	@$(MAKE) verify-sanitization
	@$(MAKE) verify-fas4-static
	@$(MAKE) verify-fas4-5
	@$(MAKE) verify-projects-e2e
	@$(MAKE) verify-transcription-quality
	@echo ""
	@echo "🟢 All verifications PASSED - System ready for FAS 5"

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f

benchmark-stt:
	@echo "======================================================================"
	@echo "STT BENCHMARK MATRIX - Prestanda & Kvalitet"
	@echo "======================================================================"
	@echo "Kör 4 konfigurationer * 2 runs = 8 totala körningar"
	@echo "Uppskattad tid: 30-60 minuter (beroende på modell)"
	@echo ""
	@docker compose up -d --build
	@sleep 10
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KONFIGURATION 1/4: Whisper base"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T -e STT_ENGINE=whisper -e WHISPER_MODEL=base -e TEST_AUDIO_PATH=/app/Del21.wav -e NUM_RUNS=2 api python _verify/benchmark_stt_matrix.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KONFIGURATION 2/4: Whisper small"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T -e STT_ENGINE=whisper -e WHISPER_MODEL=small -e TEST_AUDIO_PATH=/app/Del21.wav -e NUM_RUNS=2 api python _verify/benchmark_stt_matrix.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KONFIGURATION 3/4: faster-whisper base"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T -e STT_ENGINE=faster_whisper -e WHISPER_MODEL=base -e TEST_AUDIO_PATH=/app/Del21.wav -e NUM_RUNS=2 api python _verify/benchmark_stt_matrix.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KONFIGURATION 4/4: faster-whisper small"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T -e STT_ENGINE=faster_whisper -e WHISPER_MODEL=small -e TEST_AUDIO_PATH=/app/Del21.wav -e NUM_RUNS=2 api python _verify/benchmark_stt_matrix.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "AGGREGERAR RESULTAT"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose exec -T api python _verify/aggregate_stt_benchmark.py
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "KOPIERAR RAPPORT"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@docker compose cp api:/app/test_results/STT_BENCHMARK.md docs/STT_BENCHMARK.md 2>/dev/null || echo "⚠️  Kunde inte kopiera rapport (kör manuellt: docker compose cp api:/app/test_results/STT_BENCHMARK.md docs/STT_BENCHMARK.md)"
	@echo ""
	@echo "======================================================================"
	@echo "✅ BENCHMARK KLAR"
	@echo "======================================================================"
	@echo "JSON Rapport: apps/api/test_results/stt_benchmark_report.json"
	@echo "Markdown Rapport: docs/STT_BENCHMARK.md"
	@echo "Transcripts: apps/api/test_results/transcripts/"
	@echo ""

verify-feed-import:
	@echo "======================================================================"
	@echo "FEED IMPORT VERIFICATION"
	@echo "======================================================================"
	@docker-compose exec -T api python3 /app/_verify/verify_feed_import.py || \
		(echo "" && \
		 echo "Note: If containers are not running, start with 'make dev' first" && \
		 exit 1)
	@echo ""
	@echo "======================================================================"
	@echo "✅ FEED IMPORT VERIFICATION COMPLETE"
	@echo "======================================================================"
	@echo "Results: apps/api/test_results/feed_import_verify.json"
	@echo ""
