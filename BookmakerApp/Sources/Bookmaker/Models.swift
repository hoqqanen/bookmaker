import Foundation

/// Trim sizes accepted by `epub2pdf.book --page-size`.
let pageSizes = ["a5", "a4", "5x8", "5.5x8.5", "6x9", "letter"]
/// Sheet sizes accepted by `--sheet-size`.
let sheetSizes = ["a4", "a3", "a5", "letter", "legal"]

private func num(_ value: Double) -> String {
    String(format: "%g", value)
}

/// Options for the EPUB -> flat PDF step (`epub2pdf.book`).
struct TypesetSettings: Codable, Equatable {
    var pageSize = "a5"
    var fontFamily = "Baskerville"
    var fontSize = 10.5  // pt
    var lineHeight = 1.2
    var marginTop = 0.6  // inches
    var marginBottom = 0.6
    var marginLeft = 0.6
    var marginRight = 0.6

    var arguments: [String] {
        [
            "--page-size", pageSize,
            "--font-family", fontFamily,
            "--font-size", num(fontSize) + "pt",
            "--line-height", num(lineHeight),
            "--margin-top", num(marginTop) + "in",
            "--margin-bottom", num(marginBottom) + "in",
            "--margin-left", num(marginLeft) + "in",
            "--margin-right", num(marginRight) + "in",
        ]
    }

    var summary: String {
        "\(pageSize.uppercased()) · \(fontFamily) \(num(fontSize))pt"
    }
}

/// Options for the signature imposition step.
struct ImposeSettings: Codable, Equatable {
    var sheetSize = "a4"
    var signatureSize = 8  // sheets per signature

    var arguments: [String] {
        ["--sheet-size", sheetSize, "--signature-size", String(signatureSize)]
    }
}

enum SourceKind: String, Codable {
    case epub, pdf
}

struct LibraryItem: Codable, Identifiable, Hashable {
    let id: UUID
    var title: String
    let kind: SourceKind
    let sourceFileName: String
    let added: Date
    var typeset: TypesetSettings
    var impose: ImposeSettings
    /// Settings used for the last successful build, to detect stale output.
    var builtTypeset: TypesetSettings?
    var builtImpose: ImposeSettings?
    var lastBuilt: Date?
    var lastError: String?

    var needsRebuild: Bool {
        guard lastBuilt != nil else { return true }
        return builtImpose != impose || (kind == .epub && builtTypeset != typeset)
    }

    static func == (a: LibraryItem, b: LibraryItem) -> Bool { a.id == b.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
}
