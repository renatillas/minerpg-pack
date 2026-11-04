#!/usr/bin/env bash
# Build the ready-made client zip, for players who use the official Minecraft Launcher instead of Prism.
#
#   pack/tools/build_client.sh            build dist/minerpg-client-<version>.zip from this checkout's pack/
#   pack/tools/build_client.sh --upload   also replace the asset on the GitHub release "client" of
#                                         renatillas/minerpg-pack, so CLIENT_URL below always serves the latest
#
# release.sh runs this with --upload after every publish. The zip unzips straight into the player's game directory
# (mods, config, kubejs, patchouli_books, resourcepacks, plus README.txt). Unlike the Prism instance it does not
# update itself: players download it again after every release (README.txt says how).
set -euo pipefail

JAVA="/Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home/bin/java"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
REPO="renatillas/minerpg-pack"
CLIENT_URL="https://github.com/$REPO/releases/download/client/minerpg-client.zip"

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
DIST="$ROOT/dist"
CLI="$DIST/client"
# The checkout, not the published URL: raw.githubusercontent caches for minutes right after release.sh pushes.
PACK_URL="file://$ROOT/pack/pack.toml"

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pack/pack.toml")"
MC="$(sed -n 's/^minecraft = "\(.*\)"/\1/p' "$ROOT/pack/pack.toml")"
NEOFORGE="$(sed -n 's/^neoforge = "\(.*\)"/\1/p' "$ROOT/pack/pack.toml")"

mkdir -p "$CLI"
cd "$CLI"
[ -f packwiz-installer-bootstrap.jar ] || curl -fsSL -o packwiz-installer-bootstrap.jar "$BOOTSTRAP_URL"
# Fresh pack folders every build, so mods removed from the pack don't linger.
rm -rf mods config kubejs patchouli_books resourcepacks packwiz.json
"$JAVA" -jar packwiz-installer-bootstrap.jar -g -s client "$PACK_URL"

cat > README.txt <<EOF
minerpg $VERSION (Minecraft $MC, NeoForge $NEOFORGE)

You need a paid Minecraft Java account to join the server.

First time
1. Install NeoForge $NEOFORGE: download the installer from
   https://maven.neoforged.net/releases/net/neoforged/neoforge/$NEOFORGE/neoforge-$NEOFORGE-installer.jar
   run it and choose "Install client".
2. In the Minecraft Launcher, open Installations > New installation:
   - Version: neoforge-$NEOFORGE
   - Game directory: a new empty folder, for example "minerpg"
   - More options > JVM arguments: change -Xmx2G to -Xmx6G
3. Unzip this file into that folder, so it holds mods, config, kubejs and the rest.
4. Launch the installation.

After every update
The server only lets you in with the same version it runs. When there's a new version:
1. Download the zip again: $CLIENT_URL
2. Delete the mods, config, kubejs, patchouli_books and resourcepacks folders from your minerpg folder.
   (Your worlds, screenshots and settings are elsewhere in that folder and stay.)
3. Unzip the new zip into the folder.
EOF

ZIP="$DIST/minerpg-client-$VERSION.zip"
rm -f "$ZIP"
zip -qr "$ZIP" README.txt mods config kubejs patchouli_books resourcepacks
echo "Client zip: $ZIP ($(du -h "$ZIP" | cut -f1))"

if [ "${1:-}" = "--upload" ]; then
  gh release view client -R "$REPO" >/dev/null 2>&1 \
    || gh release create client -R "$REPO" --title "Client zip (official Minecraft Launcher)" \
         --notes "Ready-made client files for the official Minecraft Launcher. Instructions are in README.txt inside the zip. Prism players don't need this."
  cp "$ZIP" "$DIST/minerpg-client.zip"
  gh release upload client "$DIST/minerpg-client.zip" --clobber -R "$REPO"
  gh release edit client -R "$REPO" --title "Client zip $VERSION (official Minecraft Launcher)" >/dev/null
  echo "Players download: $CLIENT_URL"
fi
