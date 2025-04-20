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
	@echo "Variables:"
	@echo "  DOCKER_IMAGE - Image name (default: myapp)"
	@echo "  VERSION      - Image version tag (default: latest)"
	@echo "  PLATFORMS    - Target platforms (default: linux/amd64,linux/arm64)"
	@echo "  REGISTRY     - Docker registry (default: docker.io)"