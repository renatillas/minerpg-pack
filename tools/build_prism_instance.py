#!/usr/bin/env python3
"""Build the Prism Launcher instance that players import once: dist/minerpg-prism.zip.

The instance holds no mods. Its pre-launch command runs packwiz-installer against the public pack repository, so
the first launch downloads the whole pack and every later launch picks up whatever release.sh last published.
Only rebuild this zip when something in it changes (pack URL, memory, NeoForge/Minecraft version); pack releases
alone don't need a new one. It is attached to the GitHub release "instance" of renatillas/minerpg-pack, so players
can paste INSTANCE_URL straight into Prism's Import dialog.

  python3 pack/tools/build_prism_instance.py
"""

import io
import json
import os
import re
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
import gen_brand_pack  # noqa: E402  (the instance icon is the pack's gold "M")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'dist', 'minerpg-prism.zip')

PACK_URL = 'https://raw.githubusercontent.com/renatillas/minerpg-pack/main/pack.toml'
INSTANCE_URL = 'https://github.com/renatillas/minerpg-pack/releases/download/instance/minerpg-prism.zip'
BOOTSTRAP_URL = 'https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar'

# 6 GB is what the pack needs with Excalibur and ~130 mods; players with 8 GB machines can lower it in Prism.
MIN_MEM_MB = 2048
MAX_MEM_MB = 6144


def pack_versions():
    with open(os.path.join(ROOT, 'pack', 'pack.toml')) as f:
        text = f.read()
    mc = re.search(r'^minecraft = "(.+)"', text, re.M).group(1)
    neo = re.search(r'^neoforge = "(.+)"', text, re.M).group(1)
    return mc, neo


def main():
    mc, neo = pack_versions()
    instance_cfg = '\n'.join([
        '[General]',
        'ConfigVersion=1.2',
        'InstanceType=OneSix',
        'name=minerpg',
        'iconKey=minerpg',
        # Runs in the instance's .minecraft folder, where the bootstrap jar lives. $INST_JAVA is the Java Prism
        # picked for 1.21.1 (it downloads Java 21 itself if the player has none).
        'OverrideCommands=true',
        f'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar {PACK_URL}',
        'OverrideMemory=true',
        f'MinMemAlloc={MIN_MEM_MB}',
        f'MaxMemAlloc={MAX_MEM_MB}',
        '',
    ])
    mmc_pack = {
        'formatVersion': 1,
        'components': [
            {'uid': 'net.minecraft', 'version': mc, 'important': True},
            {'uid': 'net.neoforged', 'version': neo},
        ],
    }
    with urllib.request.urlopen(BOOTSTRAP_URL) as r:
        bootstrap = r.read()

    files = {
        'minerpg/instance.cfg': instance_cfg.encode(),
        'minerpg/mmc-pack.json': json.dumps(mmc_pack, indent=2).encode(),
        'minerpg/minerpg.png': gen_brand_pack.icon().png(),
        'minerpg/.minecraft/packwiz-installer-bootstrap.jar': bootstrap,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(buf.getvalue())
    print(f'{OUT}: Minecraft {mc}, NeoForge {neo}, {len(buf.getvalue())} bytes')
    print(f'Upload: gh release upload instance {OUT} --clobber -R renatillas/minerpg-pack')
    print(f'Players import: {INSTANCE_URL}')


if __name__ == '__main__':
    main()
