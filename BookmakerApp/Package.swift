// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Bookmaker",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(name: "Bookmaker", path: "Sources/Bookmaker"),
    ]
)
