# Variables
DOCKER_IMAGE ?= ctrahey/nettest
VERSION ?= 0.0.9
PLATFORMS ?= linux/amd64,linux/arm64
REGISTRY ?= docker.io
BUILDER_NAME = multiplatform-builder
DOCKER_CONTEXT = www/app/

# Build targets
.PHONY: builder
builder:
	docker buildx create --name $(BUILDER_NAME) --driver docker-container --bootstrap || true
	docker buildx use $(BUILDER_NAME)

.PHONY: build
build: builder
	docker buildx build \
		--platform $(PLATFORMS) \
		--tag $(REGISTRY)/$(DOCKER_IMAGE):$(VERSION) \
		--sbom=true \
		--provenance=true \
		$(DOCKER_CONTEXT)

.PHONY: build-push
build-push: builder
	docker buildx build \
		--platform $(PLATFORMS) \
		--tag $(REGISTRY)/$(DOCKER_IMAGE):$(VERSION) \
		--push \
		--sbom=true \
		--provenance=true \
		$(DOCKER_CONTEXT)

.PHONY: sbom
sbom:
	docker sbom $(REGISTRY)/$(DOCKER_IMAGE):$(VERSION)

.PHONY: inspect
inspect:
	docker buildx imagetools inspect $(REGISTRY)/$(DOCKER_IMAGE):$(VERSION)

.PHONY: clean
clean:
	docker buildx rm $(BUILDER_NAME)

.PHONY: tag-latest
tag-latest:
	docker tag $(REGISTRY)/$(DOCKER_IMAGE):$(VERSION) $(REGISTRY)/$(DOCKER_IMAGE):latest
	docker push $(REGISTRY)/$(DOCKER_IMAGE):latest

# Test targets
.PHONY: test-deps
test-deps:
	@echo "Installing test dependencies..."
	cd $(DOCKER_CONTEXT) && pip install -e ".[test]"

.PHONY: test
test: test-deps
	@echo "Running tests..."
	cd $(DOCKER_CONTEXT) && python -m pytest tests/ -v

.PHONY: test-coverage
test-coverage: test-deps
	@echo "Running tests with coverage..."
	cd $(DOCKER_CONTEXT) && python -m pytest tests/ --cov=mockserver --cov-report=term-missing

.PHONY: test-debug
test-debug: test-deps
	@echo "Running tests with debug output..."
	cd $(DOCKER_CONTEXT) && python -m pytest tests/ -v -s --tb=long

.PHONY: test-clean
test-clean:
	@echo "Cleaning test artifacts..."
	cd $(DOCKER_CONTEXT) && rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/

# Development targets
.PHONY: dev-build
dev-build:
	@echo "Building local development image..."
	cd $(DOCKER_CONTEXT) && docker build -t mockserver:local .


.PHONY: help
help:
	@echo "Available targets:"
	@echo "  builder      - Create and set up buildx builder"
	@echo "  build        - Build multi-platform image with SBOM and attestations"
	@echo "  build-push   - Build and push multi-platform image"
	@echo "  sbom         - Generate SBOM for the image"
	@echo "  inspect      - Inspect the built image"
	@echo "  clean        - Remove buildx builder"
	@echo "  tag-latest   - Tag and push image as latest"
	@echo ""
	@echo "Test targets:"
	@echo "  test-deps    - Install test dependencies"
	@echo "  test         - Run all tests with verbose output"
	@echo "  test-coverage- Run tests with coverage report"
	@echo "  test-debug   - Run tests with debug output"
	@echo "  test-clean   - Clean test artifacts"
	@echo ""
	@echo "Development targets:"
	@echo "  dev-build    - Build local development Docker image"
	@echo ""
	@echo "Variables:"
	@echo "  DOCKER_IMAGE - Image name (default: myapp)"
	@echo "  VERSION      - Image version tag (default: latest)"
	@echo "  PLATFORMS    - Target platforms (default: linux/amd64,linux/arm64)"
	@echo "  REGISTRY     - Docker registry (default: docker.io)"