import AppKit
import PDFKit
import SwiftUI

struct PDFKitView: NSViewRepresentable {
    let url: URL
    /// Changes whenever the file on disk is rebuilt, forcing a reload.
    let revision: Int

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.backgroundColor = .underPageBackgroundColor
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {
        let key = "\(url.path)#\(revision)"
        guard context.coordinator.loadedKey != key else { return }
        context.coordinator.loadedKey = key
        view.document = PDFDocument(url: url)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        var loadedKey: String?
    }
}

/// Shows the macOS print panel for a PDF at its actual size. Imposed sheets
/// default to landscape with short-edge (tumble) duplex, matching the
/// imposition instructions.
func printPDF(at url: URL, title: String, imposed: Bool) {
    guard let document = PDFDocument(url: url), let firstPage = document.page(at: 0) else {
        NSSound.beep()
        return
    }
    let info = NSPrintInfo.shared.copy() as! NSPrintInfo
    let bounds = firstPage.bounds(for: .mediaBox)
    info.paperSize = NSSize(width: min(bounds.width, bounds.height), height: max(bounds.width, bounds.height))
    info.orientation = bounds.width > bounds.height ? .landscape : .portrait
    info.topMargin = 0
    info.bottomMargin = 0
    info.leftMargin = 0
    info.rightMargin = 0
    info.isHorizontallyCentered = true
    info.isVerticallyCentered = true
    if imposed {
        let settings = PMPrintSettings(info.pmPrintSettings())
        PMSetDuplex(settings, PMDuplexMode(kPMDuplexTumble))
        info.updateFromPMPrintSettings()
    }

    guard let operation = document.printOperation(for: info, scalingMode: .pageScaleNone, autoRotate: false) else {
        NSSound.beep()
        return
    }
    operation.jobTitle = title
    operation.showsPrintPanel = true
    operation.showsProgressPanel = true
    operation.printPanel.options.insert([.showsPaperSize, .showsOrientation, .showsScaling, .showsPreview])
    if let window = NSApp.keyWindow {
        operation.runModal(for: window, delegate: nil, didRun: nil, contextInfo: nil)
    } else {
        operation.run()
    }
}
