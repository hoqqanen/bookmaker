import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @Environment(Library.self) private var library
    @State private var selection: UUID?
    @State private var dropTargeted = false

    var body: some View {
        NavigationSplitView {
            List(selection: $selection) {
                ForEach(library.items) { item in
                    ItemRow(item: item)
                        .tag(item.id)
                        .contextMenu { contextMenu(for: item) }
                }
            }
            .overlay {
                if library.items.isEmpty {
                    ContentUnavailableView(
                        "Drop EPUBs or PDFs",
                        systemImage: "books.vertical",
                        description: Text("EPUBs are typeset and imposed.\nPDFs are imposed into signatures.")
                    )
                }
            }
            .navigationSplitViewColumnWidth(min: 220, ideal: 260)
            .toolbar {
                Button(action: chooseFiles) { Label("Add Books", systemImage: "plus") }
                    .help("Add EPUBs or PDFs (⌘O)")
            }
        } detail: {
            if let id = selection, library.item(id) != nil {
                ItemDetail(itemID: id).id(id)
            } else {
                ContentUnavailableView(
                    "No Book Selected",
                    systemImage: "book.closed",
                    description: Text("Drag EPUB or PDF files anywhere into this window.")
                )
            }
        }
        .onDrop(of: [.fileURL], isTargeted: $dropTargeted, perform: handleDrop)
        .overlay {
            if dropTargeted {
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(Color.accentColor, lineWidth: 3)
                    .background(Color.accentColor.opacity(0.06))
                    .padding(4)
                    .allowsHitTesting(false)
            }
        }
        .onDeleteCommand {
            if let id = selection { library.delete(id) }
        }
        .onChange(of: library.lastAdded) { _, id in
            if let id { selection = id }
        }
        .onReceive(NotificationCenter.default.publisher(for: .addBooks)) { _ in chooseFiles() }
    }

    @ViewBuilder
    private func contextMenu(for item: LibraryItem) -> some View {
        Button("Rebuild") { library.build(item.id) }
            .disabled(library.running.contains(item.id))
        Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([library.folder(item)]) }
        Divider()
        Button("Move to Trash", role: .destructive) { library.delete(item.id) }
            .disabled(library.running.contains(item.id))
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        let group = DispatchGroup()
        var urls: [URL] = []
        for provider in providers {
            group.enter()
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                if let url { DispatchQueue.main.async { urls.append(url) } }
                group.leave()
            }
        }
        group.notify(queue: .main) {
            if let first = library.add(urls).first { selection = first }
        }
        return true
    }

    private func chooseFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [.pdf, UTType("org.idpf.epub-container") ?? .data]
        guard panel.runModal() == .OK else { return }
        if let first = library.add(panel.urls).first { selection = first }
    }
}

struct ItemRow: View {
    @Environment(Library.self) private var library
    let item: LibraryItem

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: item.kind == .epub ? "book.closed" : "doc.richtext")
                .font(.title2)
                .foregroundStyle(.secondary)
                .frame(width: 26)
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title).lineLimit(1)
                Text(item.kind == .epub ? item.typeset.summary : "PDF")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
            status
        }
        .padding(.vertical, 3)
    }

    @ViewBuilder
    private var status: some View {
        if library.running.contains(item.id) {
            ProgressView().controlSize(.small)
        } else if item.lastError != nil {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.red)
                .help(item.lastError ?? "")
        } else if item.needsRebuild {
            Image(systemName: "arrow.triangle.2.circlepath").foregroundStyle(.orange)
                .help("Settings changed since the last build")
        }
    }
}
