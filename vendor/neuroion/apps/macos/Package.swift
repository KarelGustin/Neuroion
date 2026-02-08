// swift-tools-version: 6.2
// Package manifest for the Neuroion macOS companion (menu bar app + IPC library).

import PackageDescription

let package = Package(
    name: "Neuroion",
    platforms: [
        .macOS(.v15),
    ],
    products: [
        .library(name: "NeuroionIPC", targets: ["NeuroionIPC"]),
        .library(name: "NeuroionDiscovery", targets: ["NeuroionDiscovery"]),
        .executable(name: "Neuroion", targets: ["Neuroion"]),
        .executable(name: "neuroion-mac", targets: ["NeuroionMacCLI"]),
    ],
    dependencies: [
        .package(url: "https://github.com/orchetect/MenuBarExtraAccess", exact: "1.2.2"),
        .package(url: "https://github.com/swiftlang/swift-subprocess.git", from: "0.1.0"),
        .package(url: "https://github.com/apple/swift-log.git", from: "1.8.0"),
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.8.1"),
        .package(url: "https://github.com/steipete/Peekaboo.git", branch: "main"),
        .package(path: "../shared/NeuroionKit"),
        .package(path: "../../Swabble"),
    ],
    targets: [
        .target(
            name: "NeuroionIPC",
            dependencies: [],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .target(
            name: "NeuroionDiscovery",
            dependencies: [
                .product(name: "NeuroionKit", package: "NeuroionKit"),
            ],
            path: "Sources/NeuroionDiscovery",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .executableTarget(
            name: "Neuroion",
            dependencies: [
                "NeuroionIPC",
                "NeuroionDiscovery",
                .product(name: "NeuroionKit", package: "NeuroionKit"),
                .product(name: "NeuroionChatUI", package: "NeuroionKit"),
                .product(name: "NeuroionProtocol", package: "NeuroionKit"),
                .product(name: "SwabbleKit", package: "swabble"),
                .product(name: "MenuBarExtraAccess", package: "MenuBarExtraAccess"),
                .product(name: "Subprocess", package: "swift-subprocess"),
                .product(name: "Logging", package: "swift-log"),
                .product(name: "Sparkle", package: "Sparkle"),
                .product(name: "PeekabooBridge", package: "Peekaboo"),
                .product(name: "PeekabooAutomationKit", package: "Peekaboo"),
            ],
            exclude: [
                "Resources/Info.plist",
            ],
            resources: [
                .copy("Resources/Neuroion.icns"),
                .copy("Resources/DeviceModels"),
            ],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .executableTarget(
            name: "NeuroionMacCLI",
            dependencies: [
                "NeuroionDiscovery",
                .product(name: "NeuroionKit", package: "NeuroionKit"),
                .product(name: "NeuroionProtocol", package: "NeuroionKit"),
            ],
            path: "Sources/NeuroionMacCLI",
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
            ]),
        .testTarget(
            name: "NeuroionIPCTests",
            dependencies: [
                "NeuroionIPC",
                "Neuroion",
                "NeuroionDiscovery",
                .product(name: "NeuroionProtocol", package: "NeuroionKit"),
                .product(name: "SwabbleKit", package: "swabble"),
            ],
            swiftSettings: [
                .enableUpcomingFeature("StrictConcurrency"),
                .enableExperimentalFeature("SwiftTesting"),
            ]),
    ])
