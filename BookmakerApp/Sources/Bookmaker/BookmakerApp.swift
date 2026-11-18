import AppKit
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    let library = Library()

    /// Files dropped on the Dock icon or opened via Finder's "Open With".
    func application(_ application: NSApplication, open urls: [URL]) {
        if let id = library.add(urls).first {
            library.lastAdded = id
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main
struct BookmakerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate

    var body: some Scene {
        Window("Bookmaker", id: "library") {
            ContentView()
                .environment(delegate.library)
                .frame(minWidth: 900, minHeight: 560)
        }
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("Add Books…") { NotificationCenter.default.post(name: .addBooks, object: nil) }
                    .keyboardShortcut("o")
            }
        }

        Settings {
            SettingsView()
                .environment(delegate.library)
        }
    }
}

extension Notification.Name {
    static let addBooks = Notification.Name("BookmakerAddBooks")
}
