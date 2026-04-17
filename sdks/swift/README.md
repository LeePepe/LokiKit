# LokiKit

A reusable Swift package for structured logging and telemetry, shipping events to Grafana Loki.

## Features

- `Logger` protocol with `PrintLogger` implementation
- `TelemetryService` protocol with `LokiTelemetryService` and `NoopTelemetryService`
- Offline event queue with disk persistence and automatic retry
- Grafana Cloud compatible (Bearer token auth)

## Requirements

- Swift 6.2+
- iOS 26+ / macOS 26+

## Usage

```swift
import LokiKit

// Create the telemetry service
let telemetry = LokiTelemetryService(
    endpoint: URL(string: "http://localhost:3100/loki/api/v1/push")!,
    appLabels: ["app": "MyApp", "env": "production"],
    authToken: "your-bearer-token" // optional, for Grafana Cloud
)

// Track an event
telemetry.track(name: "recording.started", properties: ["provider": "whisper"])

// Flush on app backgrounding / quit
await telemetry.flush()
```

## Logging

```swift
import LokiKit

let logger = PrintLogger(subsystem: "MyApp")
logger.info("App started")
logger.debug("Recording started", context: ["provider": "whisper"])
logger.error(someError)
```
