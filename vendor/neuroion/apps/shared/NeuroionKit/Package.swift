// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "NeuroionKit",
    platforms: [
        .iOS(.v18),
        .macOS(.v15),
    ],
    products: [
        .library(name: "NeuroionProtocol", targets: ["NeuroionProtocol"]),
        .library(name: "NeuroionKit", targets: ["NeuroionKit"]),
        .library(name: "NeuroionChatUI", targets: ["NeuroionChatUI"]),
    ],
    dependencies: [
        .package(url: "https://github.com/steipete/ElevenLabsKit", exact: "0.1.0"),
        .package(url: "https://github.com/gonzalezreal/textual", exact: "0.3.1"),
    ],
    targets: [
        .target(
            name: "NeuroionProtocol",
            path: "Sources/NeuroionProtocol",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .target(
            name: "NeuroionKit",
            dependencies: [
                "NeuroionProtocol",
                .product(name: "ElevenLabsKit", package: "ElevenLabsKit"),
            ],
            path: "Sources/NeuroionKit",
            resources: [
                .process("Resources"),
            ],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .target(
            name: "NeuroionChatUI",
            dependencies: [
                "NeuroionKit",
                .product(
                    name: "Textual",
                    package: "textual",
                    condition: .when(platforms: [.macOS, .iOS])),
            ],
            path: "Sources/NeuroionChatUI",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .testTarget(
            name: "NeuroionKitTests",
            dependencies: ["NeuroionKit", "NeuroionChatUI"],
            path: "Tests/NeuroionKitTests",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
                .enableExperimentalFeature("SwiftTesting"),
            ]),
    ])
