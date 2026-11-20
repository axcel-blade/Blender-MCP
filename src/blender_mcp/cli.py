"""Command-line interface for Blender MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import zipfile
from pathlib import Path

from blender_mcp import __version__
from blender_mcp.config import load_settings
from blender_mcp.logging_config import setup_logging
from blender_mcp.protocol.client import BlenderBridgeClient


def _addon_source_dir() -> Path:
    # Development checkout
    repo_addon = Path(__file__).resolve().parents[2] / "blender_addon"
    if repo_addon.is_dir() and (repo_addon / "__init__.py").exists():
        return repo_addon
    # Installed wheel bundled copy
    bundled = Path(__file__).resolve().parent / "bundled_addon"
    if bundled.is_dir():
        return bundled
    raise FileNotFoundError("Could not locate blender_addon package")


def cmd_run(_: argparse.Namespace) -> int:
    from blender_mcp.server import main as server_main

    server_main()
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


async def _diagnose() -> dict:
    settings = load_settings()
    client = BlenderBridgeClient(settings.bridge())
    return await client.diagnose()


def cmd_diagnose(_: argparse.Namespace) -> int:
    setup_logging(load_settings().log_level)
    result = asyncio.run(_diagnose())
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("connected") else 1


def _blender_addon_dirs() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []
    # Windows
    candidates.append(home / "AppData" / "Roaming" / "Blender Foundation" / "Blender")
    # Linux
    candidates.append(home / ".config" / "blender")
    # macOS
    candidates.append(home / "Library" / "Application Support" / "Blender")
    found: list[Path] = []
    for base in candidates:
        if not base.is_dir():
            continue
        for child in base.iterdir():
            scripts = child / "scripts" / "addons"
            if scripts.is_dir():
                found.append(scripts)
            # Blender 4.2+ extensions still support legacy addons path
            legacy = child / "scripts" / "addons"
            if legacy.is_dir() and legacy not in found:
                found.append(legacy)
    return found


def cmd_install_addon(args: argparse.Namespace) -> int:
    source = _addon_source_dir()
    targets = _blender_addon_dirs()
    if args.target:
        targets = [Path(args.target)]
    if not targets:
        print("No Blender addons directories found. Pass --target PATH", file=sys.stderr)
        return 1

    for target_root in targets:
        dest = target_root / "blender_mcp_addon"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
        print(f"Installed addon to {dest}")

    print("Enable the addon in Blender: Edit > Preferences > Add-ons > Blender MCP")
    return 0


def cmd_pack_addon(args: argparse.Namespace) -> int:
    source = _addon_source_dir()
    out = Path(args.output or "blender_mcp_addon.zip")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                arc = Path("blender_mcp_addon") / path.relative_to(source)
                zf.write(path, arcname=str(arc))
    print(f"Wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blender-mcp", description="Blender MCP server CLI")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run the MCP server on stdio (default)")
    run_p.set_defaults(func=cmd_run)

    ver_p = sub.add_parser("version", help="Print version")
    ver_p.set_defaults(func=cmd_version)

    diag_p = sub.add_parser("diagnose", help="Diagnose Blender bridge connectivity")
    diag_p.set_defaults(func=cmd_diagnose)

    inst_p = sub.add_parser(
        "install-addon", help="Install the Blender addon into detected Blender paths"
    )
    inst_p.add_argument("--target", help="Explicit Blender addons directory")
    inst_p.set_defaults(func=cmd_install_addon)

    pack_p = sub.add_parser("pack-addon", help="Pack the addon into a zip for manual install")
    pack_p.add_argument("-o", "--output", help="Output zip path")
    pack_p.set_defaults(func=cmd_pack_addon)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # Default to MCP stdio server for MCP client configs that call the console script.
        raise SystemExit(cmd_run(argparse.Namespace()))
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
