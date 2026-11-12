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
        # Chrome expects manifest.json at ZIP root, not under a wrapper directory.
        # A nested manifest can pass content checks yet produce an uninstallable ZIP.
        if "manifest.json" not in names:
            raise ValueError("Expected exactly one root manifest.json")
        if any(n != "manifest.json" and n.endswith("/manifest.json") for n in names):
            raise ValueError("Unexpected nested manifest.json")
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("name") != "Flind":
            raise ValueError("Wrong extension identity")
        if "externally_connectable" in manifest:
            raise ValueError("External websites must not be trusted by default")
        icons = manifest.get("icons", {})
        action = manifest.get("action", {}).get("default_icon", {})
        if icons.get("128") != "icons/flind-128x128.png" or action.get("128") != icons["128"]:
            raise ValueError("Wrong 128px icon mapping")
        path = icons["128"]
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
