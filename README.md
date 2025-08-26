# Net and Load Test

A comprehensive testing framework for network simulation and load testing with configurable delays, error rates, and synthetic response generation.

## Table of Contents

- [Overview](#overview)
- [Components](#components)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)


## Overview

This project provides two main testing components:

1. **Net Test** - Network issue simulation and performance testing
2. **Load Test** - Sophisticated mock server for API mocking and load testing

## Components

### Net Test

The Net test component aims at testing network issues.

#### Purpose
- **Network Issue Simulation**: Reproduce hard-to-replicate network conditions with configurable delays and error rates
- **Performance Testing**: Generate controlled response sizes and latencies to test system behavior

### Load Test

The load testing component provides a sophisticated mock server designed to simulate realistic application behavior under load.

#### Purpose
- **API Mocking**: Serve realistic file responses (PDFs, images, JSON) with configurable behavior
- **Load Testing**: Stress test applications with predictable synthetic responses

#### Key Features

**Synthetic Response Generation**
- **Configurable Response Sizes**: Generate responses from bytes to megabytes (next step: save to file system instead of response plain text)
- **Precise Timing Control**: Set delays from microseconds to minutes with jitter support
- **Deterministic Content**: Reproducible responses using seed values for consistent testing
- **Content Verification**: Built-in SHA-256 checksums for response integrity validation

**Mock File Endpoints**
- **Multiple File Types**: Serve PDFs, images, JSON, or any file type
- **Realistic Latency**: Configure latency according to lognormal distribution
- **Error Simulation**: Set probability-based failure rates (5xx errors)
- **Random File Selection**: Randomly serve files from configured directories

**Enterprise Features**
- **Header Redaction**: Automatically redact sensitive headers (API keys, tokens) in logs
- **Detailed Logging**: Comprehensive request/response logging with timing data

## Quick Start

### Prerequisites

- Docker
- Git

### Local Build and Run

```bash
# Build the Docker image
docker build -t mockserver:local www/app/

# Run the local server
docker run -p 8080:80 \
  -v "$(pwd)/www/app/example-config.yaml:/code/config.yaml" \
  -v "$(pwd)/www/app/example-outputs:/code/example-outputs" \
  -v "$(pwd)/www/app/partition-outputs:/code/partition-outputs" \
  -v "$(pwd)/www/app/vlm-outputs:/code/vlm-outputs" \
  -e NETTEST_CONFIG=/code/config.yaml \
  -e LOG_LEVEL=debug \
  mockserver:local
```

### Alternative: Run Basic Server

```bash
# Run the basic server
docker run -p 8080:8080 ctrahey/nettest:0.0.9
```

## API Reference

### Synthetic Response API Example


```bash
# Basic: 1KB response after 500ms delay
curl -X POST "http://localhost:8080/test/1kb/500ms" \
-F "files=@www/app/example-outputs/hello-english.txt"

# With jitter and custom status
curl -X POST "http://localhost:8080/test/2mb/1s?jitter=100&response_status=201" \
-F "files=@www/app/example-outputs/hello-english.txt"

# With seed for reproducible responses
curl -X POST "http://localhost:8080/test/500b/100ms?seed=42" \
  -F "files=@www/app/example-outputs/hello-english.txt"
```
### Load Test API Example

Example :
```
curl http://localhost:8080/v1/example

```

## Configuration

### Configuration-Driven Mock Endpoints

Create a YAML configuration file like `www/app/example-config.yaml` to define mock endpoints with specific behaviors.
