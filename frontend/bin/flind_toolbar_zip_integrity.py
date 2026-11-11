"""Check the exact distributable Chrome ZIP, not just unpacked build output."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile


def verify_archive(archive: Path, icon_source: Path) -> None:
    with ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        if any(n.startswith("/") or ".." in n.split("/") or "\\" in n for n in names):
            raise ValueError("Unsafe ZIP paths")
        manifests = [n for n in names if n == "manifest.json" or n.endswith("/manifest.json")]
        if len(manifests) != 1:
            raise ValueError("Expected exactly one manifest.json")
        prefix = manifests[0][:-len("manifest.json")]
        manifest = json.loads(z.read(manifests[0]))
        if manifest.get("name") != "Flind":
            raise ValueError("Wrong extension identity")
        if "externally_connectable" in manifest:
            raise ValueError("External websites must not be trusted by default")
        icons = manifest.get("icons", {})
        action = manifest.get("action", {}).get("default_icon", {})
        if icons.get("128") != "icons/flind-128x128.png" or action.get("128") != icons["128"]:
            raise ValueError("Wrong 128px icon mapping")
        path = prefix + icons["128"]
        if path not in names:
            raise ValueError("Branded icon missing from ZIP")
        icon = z.read(path)
        if icon != icon_source.read_bytes():
            raise ValueError("ZIP icon differs from committed asset")
        if not icon.startswith(bytes.fromhex("89504e470d0a1a0a")) or (int.from_bytes(icon[16:20], "big"), int.from_bytes(icon[20:24], "big")) != (128, 128):
            raise ValueError("Invalid 128x128 PNG")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    p.add_argument("--icon", type=Path, default=Path("frontend/public/icons/flind-128x128.png"))
    args = p.parse_args()
    verify_archive(args.archive, args.icon)
    print("PASS Flind distributable Chrome ZIP:", args.archive)
