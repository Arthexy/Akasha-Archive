"""Validated local configuration. Secret values never belong in API responses."""
import json
from ipaddress import IPv4Address, IPv4Network
import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"


def validate_uid(value: str, allow_empty: bool = False) -> str:
    if allow_empty and not value:
        return value
    if not value.isascii() or not value.isdigit() or len(value) not in (9, 10):
        raise ValueError("Genshin UID must contain 9 or 10 ASCII digits.")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicAccount(StrictModel):
    uid: str = ""
    region: Literal["auto"] = "auto"

    @field_validator("uid")
    @classmethod
    def uid_valid(cls, v):
        return validate_uid(v, True)


class AkashaSettings(StrictModel):
    enabled: bool = True


class HoyoSettings(StrictModel):
    enabled: bool = False
    region: Literal["os", "cn"] = "os"
    game_uid: str = ""
    server: str = ""
    cookies: dict[str, SecretStr] = Field(default_factory=dict)

    @field_validator("game_uid")
    @classmethod
    def uid_valid(cls, v):
        return validate_uid(v, True)


def is_tailscale_host(value: str) -> bool:
    """Tailscale uses the CGNAT shared range 100.64.0.0/10."""
    try:
        parts = [int(p) for p in value.split(".")]
    except ValueError:
        return False
    if len(parts) != 4 or any(p < 0 or p > 255 for p in parts):
        return False
    return parts[0] == 100 and 64 <= parts[1] <= 127


LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def is_lan_host(value: str) -> bool:
    """Accept RFC 1918 IPv4 addresses for direct LAN access."""
    try:
        address = IPv4Address(value)
    except ValueError:
        return False
    return any(address in IPv4Network(network) for network in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    ))


def validate_host(value: str) -> str:
    if value in LOOPBACK_HOSTS or is_tailscale_host(value) or is_lan_host(value):
        return value
    raise ValueError(
        "server.host must be loopback, a private LAN IPv4 address, or a Tailscale IP (100.64.0.0/10). "
        "Use this computer's LAN IP for access from another device on the same network."
    )


class ServerSettings(StrictModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    # Extra Host headers to accept, e.g. a Tailscale MagicDNS name.
    allowed_hosts: list[str] = Field(default_factory=list)

    @field_validator("host")
    @classmethod
    def host_valid(cls, v):
        return validate_host(v)

    @property
    def trusted_hosts(self) -> list[str]:
        hosts = set(LOOPBACK_HOSTS) | set(self.allowed_hosts)
        hosts.add(self.host)
        hosts.add("[::1]")
        return sorted(hosts)


class CacheSettings(StrictModel):
    public_ttl_seconds: int = Field(default=300, gt=0)
    ranking_ttl_seconds: int = Field(default=900, gt=0)
    notes_ttl_seconds: int = Field(default=60, gt=0)


class NetworkSettings(StrictModel):
    timeout_seconds: float = Field(default=15, gt=0, le=120)
    max_retries: int = Field(default=2, ge=0, le=3)


class UISettings(StrictModel):
    accent: Literal["amber", "green", "ocean", "violet", "rose"] = "amber"
    language: Literal["id", "en"] = "id"


class Settings(StrictModel):
    schema_version: Literal[1] = 1
    game: Literal["genshin"] = "genshin"
    public_account: PublicAccount = Field(default_factory=PublicAccount)
    akasha: AkashaSettings = Field(default_factory=AkashaSettings)
    hoyolab: HoyoSettings = Field(default_factory=HoyoSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    ui: UISettings = Field(default_factory=UISettings)


def load_config(path: Path = CONFIG_PATH, env: bool = True) -> Settings:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object.")
    if env:
        for name, group, field in (("HOYO_HUB_UID", "public_account", "uid"),
                                   ("HOYO_HUB_HOST", "server", "host"),
                                   ("HOYO_HUB_PORT", "server", "port")):
            if name in os.environ:
                data.setdefault(group, {})[field] = os.environ[name]
        for name, cookie in (("HOYO_HUB_LTUID_V2", "ltuid_v2"), ("HOYO_HUB_LTOKEN_V2", "ltoken_v2")):
            if name in os.environ:
                data.setdefault("hoyolab", {}).setdefault("cookies", {})[cookie] = os.environ[name]
    return Settings.model_validate(data)


def save_config(settings: Settings, path: Path = CONFIG_PATH):
    data = settings.model_dump(mode="json")
    data["hoyolab"]["cookies"] = {k: v.get_secret_value() for k, v in settings.hoyolab.cookies.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".hoyo-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def public_config(settings: Settings) -> dict:
    data = settings.model_dump(mode="json")
    data["hoyolab"].pop("cookies")
    data["hoyolab"]["configured"] = all(
        settings.hoyolab.cookies.get(k) and settings.hoyolab.cookies[k].get_secret_value()
        for k in ("ltuid_v2", "ltoken_v2")
    )
    return data
