.PHONY: dev up down verify clean

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

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker system prune -f

