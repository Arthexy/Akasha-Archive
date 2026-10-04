import argparse
import asyncio
import getpass
import json
import os

from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from rich.text import Text

from config import HoyoSettings, is_tailscale_host, load_config, save_config, validate_host, validate_uid
from errors import HubError
from services import HubService


def render(console, value, title="HoYo-Akasha Hub"):
    """Structured, recursive Rich output without interpreting provider markup."""
    if isinstance(value, dict):
        table = Table(title=title, show_header=False, expand=False)
        table.add_column("Field", style="dim")
        table.add_column("Value", overflow="fold")
        nested = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                nested.append((key, item))
            else:
                table.add_row(Text(key.replace("_", " ")), Text("-" if item is None else str(item)))
        if table.row_count:
            console.print(table)
        for key, item in nested:
            render(console, item, key.replace("_", " ").title())
    elif isinstance(value, list):
        if not value:
            console.print(f"{title}: No data available.")
        elif all(isinstance(v, dict) and not any(isinstance(x, (list, dict)) for x in v.values()) for v in value):
            columns = list(dict.fromkeys(k for row in value for k in row))
            if console.width < 80 and len(columns) > 4:
                for index, row in enumerate(value):
                    render(console, row, f"{title} / {index + 1}")
                return
            table = Table(title=title)
            for key in columns:
                numeric = any(isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool) for row in value)
                table.add_column(key.replace("_", " "), justify="right" if numeric else "left", overflow="fold")
            for row in value:
                table.add_row(*(Text("-" if row.get(k) is None else str(row[k])) for k in columns))
            console.print(table)
        else:
            for index, row in enumerate(value):
                render(console, row, f"{title} / {index + 1}")


async def run(args):
    hub = HubService()
    try:
        if args.command == "status":
            return hub.status()
        if args.command == "notes":
            return await hub.fetch("notes", refresh=args.refresh)
        result = await hub.fetch("rankings" if args.command == "rankings" else "showcase", args.uid, args.refresh)
        if args.command == "profile":
            result = {**result, "data": result["data"]["profile"]}
        elif args.command == "character":
            selected = next((c for c in result["data"]["characters"] if c["id"] == args.character_id), None)
            if selected is None:
                raise HubError("CHARACTER_NOT_FOUND", "Character not in showcase.", status=404)
            result = {**result, "data": selected}
        return result
    finally:
        await hub.close()


def main():
    parser = argparse.ArgumentParser(description="HoYo-Akasha Hub - local Genshin dashboard")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("profile", "showcase", "character", "rankings", "notes", "status"):
        command = commands.add_parser(name)
        command.add_argument("--uid")
        command.add_argument("--refresh", action="store_true")
        command.add_argument("--json", action="store_true")
        command.add_argument("--no-color", action="store_true")
        if name == "character":
            command.add_argument("character_id", type=int)
    commands.add_parser("setup")
    server = commands.add_parser("serve")
    server.add_argument("--host", help="loopback, private LAN IPv4 address, or Tailscale IP")
    server.add_argument("--port", type=int)
    args = parser.parse_args()
    no_color = getattr(args, "no_color", False) or "NO_COLOR" in os.environ
    console = Console(no_color=no_color, markup=False, highlight=False)
    try:
        if args.command == "setup":
            settings = load_config(env=False)
            settings.public_account.uid = validate_uid(input("Public Genshin UID: ").strip())
            if input("Connect HoYoLAB? [y/N]: ").strip().lower() == "y":
                settings.hoyolab = HoyoSettings(enabled=True, cookies={
                    "ltuid_v2": getpass.getpass("ltuid_v2 (hidden): "),
                    "ltoken_v2": getpass.getpass("ltoken_v2 (hidden): ")})
            save_config(settings)
            console.print("Saved config.json. Run: python cli.py serve")
        elif args.command == "serve":
            import uvicorn
            if args.host:
                # Environment override so app.py's startup reads the same host
                # when uvicorn imports "app:app" as a fresh module.
                os.environ["HOYO_HUB_HOST"] = validate_host(args.host)
            if args.port is not None:
                os.environ["HOYO_HUB_PORT"] = str(args.port)
            settings = load_config()
            port = settings.server.port
            if not 1 <= port <= 65535:
                raise ValueError("Port must be between 1 and 65535.")
            host = settings.server.host
            console.print(f"HoYo-Akasha Hub -> http://{host}:{port}")
            if is_tailscale_host(host):
                console.print("Reachable from any device logged into your tailnet. LAN devices cannot reach it.")
            elif host in ("127.0.0.1", "localhost", "::1"):
                console.print("Loopback only. Add --host <LAN-IP> to preview from another device.")
            else:
                console.print("Open this URL from another device on the same network.")
            uvicorn.run("app:app", host=host, port=port, access_log=False)
        else:
            result = asyncio.run(run(args))
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            else:
                render(console, result["data"])
                if "meta" in result:
                    render(console, result["meta"], "Source / Freshness")
                if "warning" in result:
                    console.print("Warning: " + result["warning"]["message"])
    except HubError as exc:
        if getattr(args, "json", False):
            print(json.dumps(exc.payload()))
        else:
            Console(stderr=True, markup=False).print(f"{exc.code}: {exc.message}")
        raise SystemExit(5 if exc.status == 429 else 3 if exc.source == "hoyolab" and exc.status in (401, 403) else 2 if exc.status in (400, 422) else 4)
    except ValidationError:
        Console(stderr=True, markup=False).print("Invalid configuration. Check config.json and command inputs.")
        raise SystemExit(2)
    except ValueError as exc:
        Console(stderr=True, markup=False).print(str(exc))
        raise SystemExit(2)
    except OSError:
        Console(stderr=True, markup=False).print("Could not access configuration files. Check config.json permissions.")
        raise SystemExit(2)
    except KeyboardInterrupt:
        raise SystemExit(130)


if __name__ == "__main__":
    main()
