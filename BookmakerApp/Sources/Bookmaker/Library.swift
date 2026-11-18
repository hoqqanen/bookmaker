import AppKit
import Foundation
import Observation

/// Where the Python pipeline lives and where built books are kept.
enum AppConfig {
    static var repoURL: URL {
        if let path = UserDefaults.standard.string(forKey: "repoPath"), !path.isEmpty {
            return URL(fileURLWithPath: path)
        }
        if let path = Bundle.main.object(forInfoDictionaryKey: "BMRepoPath") as? String {
            return URL(fileURLWithPath: path)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }

    static var pythonURL: URL {
        repoURL.appendingPathComponent(".venv/bin/python")
    }

    static var defaultLibraryURL: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Bookmaker Library")
    }
}

/// The book library: one folder per item holding the source file, the
/// generated PDFs, the build log, and `item.json`.
@Observable
final class Library {
    var items: [LibraryItem] = []
    var running: Set<UUID> = []
    var logs: [UUID: String] = [:]
    /// Bumped after each successful build so PDF views reload.
    var revisions: [UUID: Int] = [:]
    /// Set when files are added from outside the window (Finder/Dock), so the UI can select them.
    var lastAdded: UUID?

    var root: URL {
        didSet {
            UserDefaults.standard.set(root.path, forKey: "libraryPath")
            load()
        }
    }

    var defaultTypeset: TypesetSettings {
        didSet { Self.storeDefault(defaultTypeset, key: "defaultTypeset") }
    }
    var defaultImpose: ImposeSettings {
        didSet { Self.storeDefault(defaultImpose, key: "defaultImpose") }
    }

    init() {
        let path = UserDefaults.standard.string(forKey: "libraryPath")
        root = path.map { URL(fileURLWithPath: $0) } ?? AppConfig.defaultLibraryURL
        defaultTypeset = Self.loadDefault(key: "defaultTypeset") ?? TypesetSettings()
        defaultImpose = Self.loadDefault(key: "defaultImpose") ?? ImposeSettings()
        load()
    }

    // MARK: Paths

    func folder(_ item: LibraryItem) -> URL { root.appendingPathComponent(item.id.uuidString) }
    func sourceURL(_ item: LibraryItem) -> URL { folder(item).appendingPathComponent(item.sourceFileName) }
    func imposedURL(_ item: LibraryItem) -> URL { folder(item).appendingPathComponent("imposed.pdf") }
    func instructionsURL(_ item: LibraryItem) -> URL { folder(item).appendingPathComponent("imposed_INSTRUCTIONS.txt") }
    private func logURL(_ item: LibraryItem) -> URL { folder(item).appendingPathComponent("log.txt") }
    private func metadataURL(_ item: LibraryItem) -> URL { folder(item).appendingPathComponent("item.json") }

    /// The sequentially paginated PDF: generated for EPUBs, the original for PDFs.
    func flatURL(_ item: LibraryItem) -> URL {
        item.kind == .epub ? folder(item).appendingPathComponent("book_flat.pdf") : sourceURL(item)
    }

    func item(_ id: UUID) -> LibraryItem? { items.first { $0.id == id } }

    // MARK: Persistence

    func load() {
        let fm = FileManager.default
        try? fm.createDirectory(at: root, withIntermediateDirectories: true)
        let dirs = (try? fm.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)) ?? []
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        items = dirs.compactMap { dir in
            guard let data = try? Data(contentsOf: dir.appendingPathComponent("item.json")) else { return nil }
            return try? decoder.decode(LibraryItem.self, from: data)
        }.sorted { $0.added > $1.added }
        logs = [:]
        for item in items {
            logs[item.id] = try? String(contentsOf: logURL(item), encoding: .utf8)
        }
    }

    private func save(_ item: LibraryItem) {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? encoder.encode(item) {
            try? data.write(to: metadataURL(item))
        }
    }

    func update(_ item: LibraryItem) {
        guard let index = items.firstIndex(where: { $0.id == item.id }) else { return }
        items[index] = item
        save(item)
    }

    // MARK: Adding and removing

    /// Copies each EPUB/PDF into the library and starts building it. Returns the new item IDs.
    @discardableResult
    func add(_ urls: [URL]) -> [UUID] {
        var added: [UUID] = []
        for url in urls {
            guard let kind = SourceKind(rawValue: url.pathExtension.lowercased()) else { continue }
            let item = LibraryItem(
                id: UUID(),
                title: url.deletingPathExtension().lastPathComponent,
                kind: kind,
                sourceFileName: url.lastPathComponent,
                added: Date(),
                typeset: defaultTypeset,
                impose: defaultImpose
            )
            do {
                try FileManager.default.createDirectory(at: folder(item), withIntermediateDirectories: true)
                try FileManager.default.copyItem(at: url, to: sourceURL(item))
            } catch {
                NSAlert(error: error).runModal()
                continue
            }
            save(item)
            items.insert(item, at: 0)
            added.append(item.id)
            build(item.id)
        }
        return added
    }

    func delete(_ id: UUID) {
        guard let item = item(id), !running.contains(id) else { return }
        try? FileManager.default.trashItem(at: folder(item), resultingItemURL: nil)
        items.removeAll { $0.id == id }
    }

    // MARK: Building

    func build(_ id: UUID) {
        guard var item = item(id), !running.contains(id) else { return }
        let folder = folder(item)

        var args: [String]
        switch item.kind {
        case .epub:
            args = ["-m", "epub2pdf.book", sourceURL(item).path, folder.path]
                + item.typeset.arguments + item.impose.arguments
                + ["--output-name", "imposed.pdf"]
        case .pdf:
            args = ["-m", "epub2pdf.impose_cli", sourceURL(item).path, imposedURL(item).path]
                + item.impose.arguments
        }

        let process = Process()
        process.executableURL = AppConfig.pythonURL
        process.arguments = args
        process.currentDirectoryURL = AppConfig.repoURL
        var env = ProcessInfo.processInfo.environment
        env["PYTHONUNBUFFERED"] = "1"
        process.environment = env

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        logs[id] = "$ python " + args.map(shellQuote).joined(separator: " ") + "\n\n"

        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            let text = String(decoding: data, as: UTF8.self)
            DispatchQueue.main.async { self?.logs[id, default: ""] += text }
        }

        let typeset = item.typeset
        let impose = item.impose
        process.terminationHandler = { [weak self] proc in
            pipe.fileHandleForReading.readabilityHandler = nil
            let rest = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
            let status = proc.terminationStatus
            DispatchQueue.main.async {
                self?.finish(id, status: status, output: rest, typeset: typeset, impose: impose)
            }
        }

        do {
            try process.run()
            running.insert(id)
        } catch {
            item.lastError = "Couldn't run \(AppConfig.pythonURL.path): \(error.localizedDescription)"
            logs[id, default: ""] += item.lastError! + "\n"
            update(item)
        }
    }

    private func finish(_ id: UUID, status: Int32, output: String, typeset: TypesetSettings, impose: ImposeSettings) {
        running.remove(id)
        logs[id, default: ""] += output
        guard var item = item(id) else { return }
        if status == 0 {
            item.lastBuilt = Date()
            item.builtTypeset = typeset
            item.builtImpose = impose
            item.lastError = nil
            revisions[id, default: 0] += 1
        } else {
            item.lastError = "Build failed (exit status \(status)). See the log for details."
        }
        update(item)
        try? logs[id]?.write(to: logURL(item), atomically: true, encoding: .utf8)
        if !NSApp.isActive {
            NSApp.requestUserAttention(.informationalRequest)
        }
    }

    // MARK: Helpers

    private static func loadDefault<T: Decodable>(key: String) -> T? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }

    private static func storeDefault<T: Encodable>(_ value: T, key: String) {
        UserDefaults.standard.set(try? JSONEncoder().encode(value), forKey: key)
    }
}

private func shellQuote(_ s: String) -> String {
    s.allSatisfy { $0.isLetter || $0.isNumber || "-_./=".contains($0) } ? s : "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'"
}
