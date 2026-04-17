import XCTest
@testable import LokiKit

// MARK: - Spy

private final class SpyTelemetryService: TelemetryService, @unchecked Sendable {
    var isEnabled: Bool = true
    private(set) var trackedNames: [(name: String, properties: [String: String])] = []

    func track(_ event: TelemetryEvent) {
        guard isEnabled else { return }
        trackedNames.append((name: event.name, properties: event.properties))
    }

    func track(name: String, properties: [String: String]) {
        guard isEnabled else { return }
        trackedNames.append((name: name, properties: properties))
    }

    func flush() async {}
    func resetIdentifier() {}
}

// MARK: - Tests

final class TelemetryPerformanceTests: XCTestCase {

    // MARK: - measure sync

    func testMeasureSyncEmitsEventWithDurationMs() {
        let service = SpyTelemetryService()
        let result = service.measure("test.sync") { 42 }
        XCTAssertEqual(result, 42)
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "test.sync")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testMeasureSyncMergesExtraProperties() {
        let service = SpyTelemetryService()
        service.measure("op", properties: ["source": "test"]) {}
        XCTAssertEqual(service.trackedNames[0].properties["source"], "test")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testMeasureSyncOnErrorEmitsFailedEventWithErrorAndDuration() {
        let service = SpyTelemetryService()
        struct FakeError: Error, LocalizedError {
            var errorDescription: String? { "boom" }
        }
        XCTAssertThrowsError(try service.measure("op") { throw FakeError() })
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "op.failed")
        XCTAssertEqual(service.trackedNames[0].properties["error"], "boom")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testMeasureSyncDoesNotTrackWhenDisabled() {
        let service = SpyTelemetryService()
        service.isEnabled = false
        service.measure("op") {}
        XCTAssertTrue(service.trackedNames.isEmpty)
    }

    // MARK: - measure async

    func testMeasureAsyncEmitsEventWithDurationMs() async {
        let service = SpyTelemetryService()
        let result = await service.measure("test.async") { 99 }
        XCTAssertEqual(result, 99)
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "test.async")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testMeasureAsyncOnErrorEmitsFailedEvent() async {
        let service = SpyTelemetryService()
        struct FakeError: Error, LocalizedError {
            var errorDescription: String? { "async fail" }
        }
        do {
            try await service.measure("async.op") { throw FakeError() }
            XCTFail("Expected error")
        } catch {}
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "async.op.failed")
        XCTAssertEqual(service.trackedNames[0].properties["error"], "async fail")
    }

    // MARK: - measureStart / measureEnd

    func testManualStartEndEmitsEvent() {
        let service = SpyTelemetryService()
        let start = service.measureStart()
        service.measureEnd("manual.op", start: start)
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "manual.op")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testManualStartEndWithErrorEmitsFailedEvent() {
        let service = SpyTelemetryService()
        struct FakeError: Error, LocalizedError {
            var errorDescription: String? { "manual error" }
        }
        let start = service.measureStart()
        service.measureEnd("manual.op", start: start, error: FakeError())
        XCTAssertEqual(service.trackedNames.count, 1)
        XCTAssertEqual(service.trackedNames[0].name, "manual.op.failed")
        XCTAssertEqual(service.trackedNames[0].properties["error"], "manual error")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    func testManualEndMergesProperties() {
        let service = SpyTelemetryService()
        let start = service.measureStart()
        service.measureEnd("op", start: start, properties: ["env": "ci"])
        XCTAssertEqual(service.trackedNames[0].properties["env"], "ci")
        XCTAssertNotNil(service.trackedNames[0].properties["duration_ms"])
    }

    // MARK: - NoopTelemetryService passthrough

    func testMeasureOnNoopServiceDoesNotCrash() {
        let service = NoopTelemetryService()
        service.measure("noop.op") {}
    }

    func testMeasureAsyncOnNoopServiceDoesNotCrash() async {
        let service = NoopTelemetryService()
        await service.measure("noop.async.op") {}
    }
}
