
.PHONY: help test-flow test-unit test-integration build run clean logs restart

help:
	@echo "🚀 Legal Agent System - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test-flow        - Run comprehensive end-to-end test flow"
	@echo "  make test-unit        - Run unit tests (if available)"
	@echo "  make test-integration - Run integration tests (if available)"
	@echo ""
	@echo "🏗️  Development Commands:"
	@echo "  make build            - Build Docker containers"
	@echo "  make run              - Start the application"
	@echo "  make restart          - Restart the application"
	@echo "  make logs             - View application logs"
	@echo "  make clean            - Clean up containers and volumes"
	@echo ""
	@echo "📊 Status Commands:"
	@echo "  make status           - Check application status"
	@echo "  make health           - Check application health"
	@echo ""

test-flow:
	@echo "🧪 Running Comprehensive Test Flow..."
	@echo "====================================="
	@python3 tests/test_flow.py

test-unit:
	@echo "🧪 Running Unit Tests..."
	@echo "======================="
	@echo "Unit tests not yet implemented"
	@echo "Use 'make test-flow' for comprehensive testing"

test-integration:
	@echo "🧪 Running Integration Tests..."
	@echo "=============================="
	@echo "Integration tests not yet implemented"
	@echo "Use 'make test-flow' for comprehensive testing"

build:
	@echo "🏗️  Building Docker Containers..."
	@docker compose build --no-cache

run:
	@echo "🚀 Starting Legal Agent System..."
	@docker compose up -d

restart:
	@echo "🔄 Restarting Legal Agent System..."
	@docker compose restart

logs:
	@echo "📋 Viewing Application Logs..."
	@docker compose logs -f tachriat-app

clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker compose down -v
	@docker system prune -f


status:
	@echo "📊 Application Status:"
	@docker compose ps

health:
	@echo "🏥 Checking Application Health..."
	@curl -s http://localhost:8017/health | python3 -m json.tool 2>/dev/null || echo "Application not responding"


test-flow-verbose:
	@echo "🧪 Running Comprehensive Test Flow (Verbose)..."
	@echo "============================================="
	@python3 -u tests/test_flow.py

test-flow-debug:
	@echo "🧪 Running Test Flow with Debug Logs..."
	@echo "======================================"
	@docker compose logs tachriat-app --tail=50
	@echo ""
	@python3 tests/test_flow.py

dev-setup:
	@echo "⚙️  Setting up development environment..."
	@docker compose up -d mongodb
	@echo "Waiting for MongoDB to be ready..."
	@sleep 10
	@docker compose up -d tachriat-app
	@echo "Development environment ready!"

dev-reset:
	@echo "🔄 Resetting development environment..."
	@docker compose down -v
	@docker compose up -d
	@echo "Development environment reset!"

docs:
	@echo "📚 Available Documentation:"
	@echo "=========================="
	@echo "• API Documentation: http://localhost:8017/docs"
	@echo "• OpenAPI Schema: http://localhost:8017/openapi.json"
	@echo "• Health Check: http://localhost:8017/health"

test-azure-services:
	@echo "🔍 Testing Azure Services..."
	@python scripts/test_azure_services.py

fix-storage-account:
	@echo "🔧 Fixing Azure Storage Account Issues..."
	@python scripts/fix_storage_account.py

check-db-data:
	@echo "🔍 Checking Database Data..."
	@python scripts/check_db_data.py
