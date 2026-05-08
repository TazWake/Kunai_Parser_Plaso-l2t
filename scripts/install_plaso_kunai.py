"""Install the Kunai Plaso plugin into the active Plaso Python environment."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


IMPORT_LINES = {
    "parsers": "from plaso.parsers import kunai",
    "jsonl_plugins": "from plaso.parsers.jsonl_plugins import kunai",
}


def _copy_path(source: Path, destination: Path, dry_run: bool = False) -> None:
    """Copy a file or directory."""

    print(f"copy {source} -> {destination}")
    if dry_run:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _append_once(path: Path, line: str, dry_run: bool = False) -> None:
    """Append a line to a text file if it is not already present."""

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line in text:
        return

    print(f"append {line!r} to {path}")
    if dry_run:
        return

    with path.open("a", encoding="utf-8") as file_object:
        if text and not text.endswith("\n"):
            file_object.write("\n")
        file_object.write(f"{line}\n")


def _append_yaml_once(path: Path, source: Path, marker: str, dry_run: bool = False) -> None:
    """Append YAML content if a marker is not already present."""

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return

    print(f"append {source} to {path}")
    if dry_run:
        return

    with path.open("a", encoding="utf-8") as file_object:
        if text and not text.endswith("\n"):
            file_object.write("\n")
        file_object.write(source.read_text(encoding="utf-8"))
        file_object.write("\n")


def _find_plaso_package() -> Path:
    """Find the active Plaso package directory."""

    specification = importlib.util.find_spec("plaso")
    if not specification or not specification.origin:
        raise RuntimeError("Unable to import plaso in this Python environment.")
    return Path(specification.origin).resolve().parent


def _find_data_directory(plaso_package: Path) -> Path:
    """Find a Plaso data directory containing timeliner.yaml."""

    candidates = [
        Path(sys.prefix) / "share" / "plaso",
        Path("/usr/share/plaso"),
        Path("/usr/local/share/plaso"),
        plaso_package.parent / "data",
        plaso_package / "data",
    ]

    for candidate in candidates:
        if (candidate / "timeliner.yaml").exists():
            return candidate

    raise RuntimeError(
        "Unable to find Plaso timeliner.yaml. Use --data-dir to specify it."
    )


def install(data_dir: Path | None = None, dry_run: bool = False) -> None:
    """Install parser, standalone helpers, timeliner mapping, and formatter."""

    plaso_package = _find_plaso_package()
    data_dir = data_dir or _find_data_directory(plaso_package)
    site_packages = plaso_package.parent

    print(f"Plaso package: {plaso_package}")
    print(f"Plaso data:    {data_dir}")
    print(f"Python libs:   {site_packages}")

    _copy_path(
        REPO_ROOT / "standalone_parser",
        site_packages / "standalone_parser",
        dry_run=dry_run,
    )
    _copy_path(
        REPO_ROOT / "plaso_plugin" / "parsers" / "kunai.py",
        plaso_package / "parsers" / "kunai.py",
        dry_run=dry_run,
    )
    _copy_path(
        REPO_ROOT / "plaso_plugin" / "jsonl_plugins" / "kunai.py",
        plaso_package / "parsers" / "jsonl_plugins" / "kunai.py",
        dry_run=dry_run,
    )

    _append_once(
        plaso_package / "parsers" / "__init__.py",
        IMPORT_LINES["parsers"],
        dry_run=dry_run,
    )
    _append_once(
        plaso_package / "parsers" / "jsonl_plugins" / "__init__.py",
        IMPORT_LINES["jsonl_plugins"],
        dry_run=dry_run,
    )

    timeliner_path = data_dir / "timeliner.yaml"
    formatter_dir = data_dir / "formatters"
    if not dry_run:
        formatter_dir.mkdir(parents=True, exist_ok=True)
    _append_yaml_once(
        timeliner_path,
        REPO_ROOT / "plaso_plugin" / "data" / "timeliner_kunai.yaml",
        "linux:kunai:event",
        dry_run=dry_run,
    )
    _copy_path(
        REPO_ROOT / "plaso_plugin" / "data" / "formatter_kunai.yaml",
        formatter_dir / "kunai.yaml",
        dry_run=dry_run,
    )


def main() -> int:
    """Run the installer."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Plaso data directory containing timeliner.yaml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without changing files.",
    )
    args = parser.parse_args()

    try:
        install(data_dir=args.data_dir, dry_run=args.dry_run)
    except RuntimeError as exception:
        print(f"error: {exception}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
