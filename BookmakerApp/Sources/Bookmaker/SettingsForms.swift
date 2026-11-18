import AppKit
import SwiftUI

struct TypesetSections: View {
    @Binding var settings: TypesetSettings

    var body: some View {
        Section("Typesetting") {
            Picker("Page size", selection: $settings.pageSize) {
                ForEach(pageSizes, id: \.self) { Text($0.uppercased()).tag($0) }
            }
            FontFamilyPicker(selection: $settings.fontFamily)
            NumberField(label: "Font size", value: $settings.fontSize, unit: "pt", step: 0.5, range: 6...24)
            NumberField(label: "Line height", value: $settings.lineHeight, unit: "×", step: 0.05, range: 0.8...3)
        }
        Section("Margins") {
            NumberField(label: "Top", value: $settings.marginTop, unit: "in", step: 0.05, range: 0...3)
            NumberField(label: "Bottom", value: $settings.marginBottom, unit: "in", step: 0.05, range: 0...3)
            NumberField(label: "Left", value: $settings.marginLeft, unit: "in", step: 0.05, range: 0...3)
            NumberField(label: "Right", value: $settings.marginRight, unit: "in", step: 0.05, range: 0...3)
        }
    }
}

struct ImposeSection: View {
    @Binding var settings: ImposeSettings

    var body: some View {
        Section("Imposition") {
            Picker("Sheet size", selection: $settings.sheetSize) {
                ForEach(sheetSizes, id: \.self) { Text($0.uppercased()).tag($0) }
            }
            Stepper(value: $settings.signatureSize, in: 1...32) {
                LabeledContent("Signature") {
                    Text("\(settings.signatureSize) sheets (\(settings.signatureSize * 4) pp)")
                        .monospacedDigit()
                }
            }
        }
    }
}

struct NumberField: View {
    let label: String
    @Binding var value: Double
    let unit: String
    let step: Double
    let range: ClosedRange<Double>

    var body: some View {
        LabeledContent(label) {
            HStack(spacing: 4) {
                TextField(label, value: $value, format: .number.precision(.fractionLength(0...3)))
                    .labelsHidden()
                    .multilineTextAlignment(.trailing)
                    .frame(width: 56)
                Text(unit)
                    .foregroundStyle(.secondary)
                    .frame(width: 16, alignment: .leading)
                Stepper(label, value: Binding(
                    get: { value },
                    set: { value = ($0 / step).rounded() * step }
                ), in: range, step: step)
                .labelsHidden()
            }
        }
    }
}

struct FontFamilyPicker: View {
    @Binding var selection: String
    private static let families = NSFontManager.shared.availableFontFamilies.sorted()

    var body: some View {
        Picker("Font", selection: $selection) {
            if !Self.families.contains(selection) {
                Text(selection).tag(selection)
            }
            ForEach(Self.families, id: \.self) { Text($0).tag($0) }
        }
    }
}

/// The app's Settings window: defaults for newly added books, plus paths.
struct SettingsView: View {
    @Environment(Library.self) private var library
    @AppStorage("repoPath") private var repoPath = ""

    var body: some View {
        @Bindable var library = library
        TabView {
            Form {
                Text("Applied to books added from now on. Existing books keep their own settings.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                TypesetSections(settings: $library.defaultTypeset)
                ImposeSection(settings: $library.defaultImpose)
                Section {
                    Button("Restore Defaults") {
                        library.defaultTypeset = TypesetSettings()
                        library.defaultImpose = ImposeSettings()
                    }
                }
            }
            .formStyle(.grouped)
            .tabItem { Label("New Books", systemImage: "book") }

            Form {
                Section {
                    LabeledContent("Library folder") {
                        Text(library.root.path).truncationMode(.middle).lineLimit(1)
                    }
                    HStack {
                        Spacer()
                        Button("Show in Finder") { NSWorkspace.shared.open(library.root) }
                        Button("Choose…") {
                            if let url = chooseFolder(startingAt: library.root) { library.root = url }
                        }
                    }
                }
                Section {
                    LabeledContent("bookmaker repo") {
                        Text(AppConfig.repoURL.path).truncationMode(.middle).lineLimit(1)
                    }
                    let found = FileManager.default.isExecutableFile(atPath: AppConfig.pythonURL.path)
                    LabeledContent("Python") {
                        Label(found ? ".venv/bin/python" : ".venv/bin/python not found",
                              systemImage: found ? "checkmark.circle.fill" : "xmark.octagon.fill")
                            .foregroundStyle(found ? .green : .red)
                    }
                    HStack {
                        Spacer()
                        if !repoPath.isEmpty {
                            Button("Use Built-in Path") { repoPath = "" }
                        }
                        Button("Choose…") {
                            if let url = chooseFolder(startingAt: AppConfig.repoURL) { repoPath = url.path }
                        }
                    }
                }
            }
            .formStyle(.grouped)
            .tabItem { Label("Locations", systemImage: "folder") }
        }
        .frame(width: 480, height: 560)
    }

    private func chooseFolder(startingAt url: URL) -> URL? {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.directoryURL = url
        return panel.runModal() == .OK ? panel.url : nil
    }
}
