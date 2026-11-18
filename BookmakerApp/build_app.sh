#!/bin/bash
# Builds Bookmaker.app into ./build. The app runs the epub2pdf pipeline from
# this repo (using its .venv), so the repo path is baked into Info.plist; it
# can be changed later in the app's Settings.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd .. && pwd)"

swift build -c release
APP=build/Bookmaker.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$(swift build -c release --show-bin-path)/Bookmaker" "$APP/Contents/MacOS/Bookmaker"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Bookmaker</string>
    <key>CFBundleDisplayName</key><string>Bookmaker</string>
    <key>CFBundleIdentifier</key><string>com.hoqqanen.bookmaker</string>
    <key>CFBundleExecutable</key><string>Bookmaker</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
    <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>BMRepoPath</key><string>${REPO}</string>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key><string>EPUB Book</string>
            <key>CFBundleTypeRole</key><string>Viewer</string>
            <key>LSHandlerRank</key><string>Alternate</string>
            <key>LSItemContentTypes</key><array><string>org.idpf.epub-container</string></array>
        </dict>
        <dict>
            <key>CFBundleTypeName</key><string>PDF Document</string>
            <key>CFBundleTypeRole</key><string>Viewer</string>
            <key>LSHandlerRank</key><string>Alternate</string>
            <key>LSItemContentTypes</key><array><string>com.adobe.pdf</string></array>
        </dict>
    </array>
</dict>
</plist>
PLIST

codesign --force --sign - "$APP" >/dev/null
echo "Built $(pwd)/$APP"
