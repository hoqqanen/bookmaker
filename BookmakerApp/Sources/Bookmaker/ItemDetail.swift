import AppKit
import SwiftUI

struct ItemDetail: View {
    enum Output: String, CaseIterable, Identifiable {
        case imposed = "Imposed"
        case flat = "Reading Copy"
        var id: Self { self }
    }

    @Environment(Library.self) private var library
    let itemID: UUID
    @State private var output: Output = .imposed
    @State private var showInspector = true

    var body: some View {
        if let item = library.item(itemID) {
            let url = output == .imposed ? library.imposedURL(item) : library.flatURL(item)
            let exists = FileManager.default.fileExists(atPath: url.path)
            let running = library.running.contains(itemID)

            preview(item: item, url: url, exists: exists, running: running)
                .navigationTitle(item.title)
                .navigationSubtitle(subtitle(item))
                .toolbar {
                    ToolbarItem(placement: .principal) {
                        Picker("Output", selection: $output) {
                            ForEach(Output.allCases) { Text($0.rawValue).tag($0) }
                        }
                        .pickerStyle(.segmented)
                    }
                    ToolbarItemGroup {
                        Button {
                            printPDF(at: url, title: item.title, imposed: output == .imposed)
                        } label: {
                            Label("Print", systemImage: "printer")
                        }
                        .keyboardShortcut("p")
                        .disabled(!exists || running)
                        .help("Print (⌘P)")

                        Button {
                            NSWorkspace.shared.open(url)
                        } label: {
                            Label("Open in Preview", systemImage: "arrow.up.forward.app")
                        }
                        .disabled(!exists)
                        .help("Open in Preview")

                        Button {
                            NSWorkspace.shared.activateFileViewerSelecting([exists ? url : library.folder(item)])
                        } label: {
                            Label("Show in Finder", systemImage: "folder")
                        }
                        .help("Show in Finder")

                        Button {
                            showInspector.toggle()
                        } label: {
                            Label("Settings", systemImage: "sidebar.trailing")
                        }
                        .help("Show or hide book settings")
                    }
                }
                .inspector(isPresented: $showInspector) {
                    ItemInspector(itemID: itemID)
                        .inspectorColumnWidth(min: 280, ideal: 320, max: 420)
                }
        }
    }

    @ViewBuilder
    private func preview(item: LibraryItem, url: URL, exists: Bool, running: Bool) -> some View {
        if exists {
            PDFKitView(url: url, revision: library.revisions[itemID, default: 0])
                .overlay(alignment: .top) {
                    if running {
                        Label("Rebuilding…", systemImage: "hourglass")
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(.regularMaterial, in: Capsule())
                            .padding(10)
                    }
                }
        } else if running {
            ProgressView("Building…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let error = item.lastError {
            ContentUnavailableView {
                Label("Build Failed", systemImage: "exclamationmark.triangle")
            } description: {
                Text(error)
            } actions: {
                Button("Try Again") { library.build(itemID) }
            }
        } else {
            ContentUnavailableView {
                Label("Not Built", systemImage: "doc")
            } actions: {
                Button("Build") { library.build(itemID) }
            }
        }
    }

    private func subtitle(_ item: LibraryItem) -> String {
        guard let date = item.lastBuilt else { return item.sourceFileName }
        return "Built " + date.formatted(.relative(presentation: .named))
    }
}

struct ItemInspector: View {
    @Environment(Library.self) private var library
    let itemID: UUID
    @State private var showLog = false

    var body: some View {
        if let item = library.item(itemID) {
            let running = library.running.contains(itemID)
            Form {
                Section {
                    TextField("Title", text: binding(\.title))
                }

                if item.kind == .epub {
                    TypesetSections(settings: binding(\.typeset))
                }
                ImposeSection(settings: binding(\.impose))

                Section {
                    HStack {
                        Button("Use Defaults") {
                            var copy = item
                            copy.typeset = library.defaultTypeset
                            copy.impose = library.defaultImpose
                            library.update(copy)
                        }
                        Button("Save as Defaults") {
                            if item.kind == .epub { library.defaultTypeset = item.typeset }
                            library.defaultImpose = item.impose
                        }
                        Spacer()
                        rebuildButton(item: item, running: running)
                    }
                }

                if let instructions = try? String(contentsOf: library.instructionsURL(item), encoding: .utf8) {
                    Section("Printing & Folding") {
                        Text(instructions)
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                    }
                }

                Section {
                    DisclosureGroup("Build Log", isExpanded: $showLog) {
                        Text(library.logs[itemID] ?? "No log yet.")
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .formStyle(.grouped)
            .onChange(of: item.lastError) { _, error in
                if error != nil { showLog = true }
            }
        }
    }

    @ViewBuilder
    private func rebuildButton(item: LibraryItem, running: Bool) -> some View {
        let button = Button(running ? "Building…" : "Rebuild") { library.build(itemID) }
            .keyboardShortcut("r")
            .disabled(running)
        if item.needsRebuild {
            button.buttonStyle(.borderedProminent)
        } else {
            button
        }
    }

    private func binding<T>(_ keyPath: WritableKeyPath<LibraryItem, T>) -> Binding<T> {
        Binding(
            get: { library.item(itemID)![keyPath: keyPath] },
            set: { newValue in
                guard var item = library.item(itemID) else { return }
                item[keyPath: keyPath] = newValue
                library.update(item)
            }
        )
    }
}
