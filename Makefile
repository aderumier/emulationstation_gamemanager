# GameManager Makefile
# Provides easy commands for building and managing the project

.PHONY: help build clean test install docker-build docker-push release

# Default target
help:
	@echo "GameManager Build System"
	@echo "======================="
	@echo ""
	@echo "Available commands:"
	@echo "  make build        - Build Debian package (syncs latest files)"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make test         - Run basic tests"
	@echo "  make install      - Install the built package"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-push  - Push Docker image to Docker Hub"
	@echo "  make release      - Full release process (version, build, git, docker)"
	@echo ""
	@echo "Examples:"
	@echo "  make build                    # Quick package build"
	@echo "  make release                  # Full release with version bump"
	@echo "  make docker-build             # Build Docker image only"

# Build Debian package
build:
	@echo "🔨 Building Debian package..."
	@./build_deb.sh

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -f gamemanager_*.deb
	@echo "✅ Clean completed"

# Run basic tests
test:
	@echo "🧪 Running basic tests..."
	@python3 -m py_compile app.py
	@python3 -m py_compile box_generator.py
	@python3 -m py_compile download_manager.py
	@echo "✅ Basic syntax tests passed"

# Install the built package
install: build
	@echo "📦 Installing package..."
	@sudo dpkg -i gamemanager_*.deb
	@echo "✅ Package installed"

# Build Docker image
docker-build: build
	@echo "🐳 Building Docker image..."
	@./build_release.sh --docker-only
	@echo "✅ Docker image built"

# Push Docker image
docker-push: docker-build
	@echo "📤 Pushing Docker image..."
	@docker push aderumier/emulationstation_gamemanager:latest
	@echo "✅ Docker image pushed"

# Full release process
release:
	@echo "🚀 Starting full release process..."
	@./build_release.sh
	@echo "✅ Release completed"

# Quick development build (no version bump)
dev-build:
	@echo "🔧 Development build..."
	@./build_deb.sh
	@echo "✅ Development build completed"
