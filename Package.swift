// swift-tools-version: 6.2

import PackageDescription

// 根 Package.swift:让仓库根即为 LokiKit Swift 包的入口。
// 消费方(如 VoxPocket)以 `.package(path: "../../../LokiKit")` 引用仓库根即可解析。
// 源码单一事实源仍在 sdks/swift/,此处通过 target `path` 指过去,不复制文件。
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
            ],
            path: "sdks/swift/Sources/LokiKit"
        ),
        .testTarget(
            name: "LokiKitTests",
            dependencies: ["LokiKit"],
            path: "sdks/swift/Tests/LokiKitTests"
        ),
    ]
)
