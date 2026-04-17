// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "LokiKit",
    platforms: [
        .iOS(.v26),
        .macOS(.v26),
    ],
    products: [
        .library(
            name: "LokiKit",
            targets: ["LokiKit"]
        ),
    ],
    dependencies: [
        .package(url: "https://github.com/TelemetryDeck/SwiftSDK", from: "2.0.0"),
    ],
    targets: [
        .target(
            name: "LokiKit",
            dependencies: [
                .product(name: "TelemetryDeck", package: "SwiftSDK"),
            ]
        ),
        .testTarget(
            name: "LokiKitTests",
            dependencies: ["LokiKit"]
        ),
    ]
)
