#!/usr/bin/env bash
# Publish the pack folder to the public pack repository that every player's launcher updates from.
#
#   pack/tools/release.sh            push pack/ (committed state of main) to github.com/renatillas/minerpg-pack
#
# Players' Prism instances run packwiz-installer before every launch against PACK_URL below, so a push here
# updates every client on its next start. The server does NOT update itself: rebuild and upload it in the same
# sitting (pack/tools/build_server.sh, then docs/server-setup.md "Updating"), or players can't join.
#
# It also rebuilds and uploads the client zip for official-launcher players (pack/tools/build_client.sh).
#
# Before running: bump `version` in pack/pack.toml, `packwiz refresh`, commit on main.
set -euo pipefail

REPO_URL="https://github.com/renatillas/minerpg-pack.git"
# Authenticate the push with the GitHub CLI login (no SSH key or global git config needed).
GIT_PUSH=(git -c credential.helper= -c "credential.helper=!gh auth git-credential" push)
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"

if [ -n "$(git status --porcelain pack)" ]; then
  echo "pack/ has uncommitted changes; commit them first." >&2
  exit 1
fi

# KubeJS scripts that break at run time in Rhino (const/let in a try block or a loop) look fine on a test boot.
python3 pack/tools/check_scripts.py || { echo "Fix the scripts above first." >&2; exit 1; }

# The index must match the files, or installers reject the pack with hash errors.
(cd pack && ~/go/bin/packwiz refresh >/dev/null)
if [ -n "$(git status --porcelain pack)" ]; then
  echo "packwiz refresh changed pack/ (index was stale); review and commit, then rerun." >&2
  exit 1
fi

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pack/pack.toml)"
SPLIT="$(git subtree split --prefix pack HEAD 2>/dev/null)"
"${GIT_PUSH[@]}" "$REPO_URL" "$SPLIT:refs/heads/main"
"${GIT_PUSH[@]}" "$REPO_URL" "$SPLIT:refs/tags/v$VERSION"
echo "Published minerpg $VERSION ($SPLIT)."
# The ready-made zip for players on the official Minecraft Launcher (Prism players update by themselves).
pack/tools/build_client.sh --upload
echo "Now update the server: pack/tools/build_server.sh"
