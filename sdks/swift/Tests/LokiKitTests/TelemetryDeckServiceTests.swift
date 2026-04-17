import XCTest
@testable import LokiKit

final class TelemetryDeckServiceTests: XCTestCase {

    // MARK: - Initialization

    func testIsEnabledDefaultsToTrue() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        XCTAssertTrue(service.isEnabled)
    }

    func testIsEnabledCanBeSetToFalse() {
        let service = TelemetryDeckService(appID: testAppID(), isEnabled: false, testMode: true)
        XCTAssertFalse(service.isEnabled)
    }

    func testIsEnabledMutation() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        XCTAssertTrue(service.isEnabled)
        service.isEnabled = false
        XCTAssertFalse(service.isEnabled)
        service.isEnabled = true
        XCTAssertTrue(service.isEnabled)
    }

    // MARK: - Track

    func testTrackEventDoesNotCrashWhenEnabled() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.isEnabled = true
        let event = TelemetryEvent(name: "test.event", properties: ["key": "value"])
        // Should not throw or crash
        service.track(event)
    }

    func testTrackEventDoesNotCrashWhenDisabled() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.isEnabled = false
        let event = TelemetryEvent(name: "test.event.disabled")
        // Should be a no-op, no crash
        service.track(event)
    }

    func testTrackNameAndPropertiesDoesNotCrashWhenEnabled() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.isEnabled = true
        service.track(name: "test.named.event", properties: ["platform": "macOS", "version": "1.0"])
    }

    func testTrackNameAndPropertiesDoesNotCrashWhenDisabled() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.isEnabled = false
        service.track(name: "test.named.event.disabled", properties: ["platform": "macOS"])
    }

    func testTrackNameNoPropertiesDoesNotCrash() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.track(name: "test.no.properties")
    }

    // MARK: - Flush

    func testFlushCompletesWithoutError() async {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        // flush() is a no-op wrapper; should complete without throwing
        await service.flush()
    }

    func testFlushCompletesWhenDisabled() async {
        let service = TelemetryDeckService(appID: testAppID(), isEnabled: false, testMode: true)
        await service.flush()
    }

    // MARK: - Reset Identifier

    func testResetIdentifierDoesNotCrash() {
        let service = TelemetryDeckService(appID: testAppID(), testMode: true)
        service.resetIdentifier()
    }

    // MARK: - TelemetryService Protocol Conformance

    func testConformsToTelemetryServiceProtocol() {
        let service: any TelemetryService = TelemetryDeckService(appID: testAppID(), testMode: true)
        XCTAssertTrue(service.isEnabled)
    }

    // MARK: - Helpers

    /// Returns a consistent sentinel App ID for tests.
    /// Using a fixed UUID ensures TelemetryDeck initializes cleanly in test mode.
    private func testAppID() -> String {
        "00000000-0000-0000-0000-000000000000"
    }
}
