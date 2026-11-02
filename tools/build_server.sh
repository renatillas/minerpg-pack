#!/usr/bin/env bash
# Build the dedicated server for the current pack version, plus the zip that gets uploaded to the host.
#
#   pack/tools/build_server.sh            install from the published pack (what players' launchers download)
#   pack/tools/build_server.sh --local    install from this checkout's pack/ (testing before release.sh)
#
# Output (dist/ is git-ignored):
#   dist/server/                          a complete, runnable server (NeoForge + pack + our settings), no world
#   dist/minerpg-server-<version>.zip     only the pack's folders (mods, config, kubejs, patchouli_books); upload
#                                         and unzip it on the host (docs/server-setup.md). server.properties is not
#                                         in it, so updates never undo the admin's settings; the first setup uploads
#                                         dist/server/server.properties once.
#
# The world is NOT built here; pregenerate it in dist/server with Chunky (docs/server-setup.md section 4).
# An existing dist/server keeps its world/ and server settings files; only the pack's folders are replaced.
set -euo pipefail

JAVA="/Library/Java/JavaVirtualMachines/zulu-21.jdk/Contents/Home/bin/java"
PACK_URL="https://raw.githubusercontent.com/renatillas/minerpg-pack/main/pack.toml"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
TOOLS="$ROOT/pack/tools"
DIST="$ROOT/dist"
SRV="$DIST/server"
if [ "${1:-}" = "--local" ]; then
  PACK_URL="file://$ROOT/pack/pack.toml"
fi

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pack/pack.toml")"
NEOFORGE="$(sed -n 's/^neoforge = "\(.*\)"/\1/p' "$ROOT/pack/pack.toml")"
python3 "$ROOT/pack/tools/check_scripts.py" || { echo "Fix the scripts above first." >&2; exit 1; }
mkdir -p "$SRV"
cd "$SRV"

if [ ! -f "libraries/net/neoforged/neoforge/$NEOFORGE/unix_args.txt" ]; then
  curl -fsSL -o neoforge-installer.jar \
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/$NEOFORGE/neoforge-$NEOFORGE-installer.jar"
  "$JAVA" -jar neoforge-installer.jar --installServer >/dev/null
  rm -f neoforge-installer.jar neoforge-installer.jar.log
fi
[ -f packwiz-installer-bootstrap.jar ] || curl -fsSL -o packwiz-installer-bootstrap.jar "$BOOTSTRAP_URL"

# Fresh pack folders every build, so mods removed from the pack don't linger.
rm -rf mods config kubejs patchouli_books packwiz.json
"$JAVA" -jar packwiz-installer-bootstrap.jar -g -s server "$PACK_URL"

# Our settings: never overwrite a server.properties that an admin has edited since the last build.
[ -f server.properties ] || cp "$TOOLS/server/server.properties" server.properties
cp "$TOOLS/server/user_jvm_args.txt" user_jvm_args.txt

ZIP="$DIST/minerpg-server-$VERSION.zip"
rm -f "$ZIP"
zip -qr "$ZIP" mods config kubejs patchouli_books
echo "Server: $SRV (minerpg $VERSION, NeoForge $NEOFORGE)"
echo "Upload zip: $ZIP ($(du -h "$ZIP" | cut -f1))"
