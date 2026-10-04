from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import asyncio
import genshin

from app import create_app
from hoyolab_client import HoYoLABClient
from enka_client import EnkaClient


def test_public_site_ignores_private_config_and_rejects_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOYO_HUB_PUBLIC", "1")
    monkeypatch.setenv("HOYO_HUB_ALLOWED_HOSTS", "archive.example.com")
    monkeypatch.setenv("HOYO_HUB_LTOKEN_V2", "must-not-be-used")
    config = tmp_path / "config.json"
    config.write_text("invalid private configuration")
    with TestClient(create_app(config), base_url="https://archive.example.com") as client:
        assert client.get("/").status_code == 200
        assert 'data-public="true"' in client.get("/").text
        settings = client.get("/api/v1/config").json()["data"]
        assert settings["public_account"]["uid"] == ""
        assert settings["hoyolab"]["configured"] is False
        for method, path in (("PATCH", "/api/v1/config"), ("POST", "/api/v1/auth/hoyolab"),
                             ("GET", "/api/v1/notes"), ("GET", "/api/v1/explore")):
            assert client.request(method, path).status_code == 403
        assert client.post("/api/v1/refresh", json={"source": "notes"},
                           headers={"Origin": "https://archive.example.com"}).status_code == 403
        assert client.post("/api/v1/refresh", json={"source": "showcase", "uid": "invalid"},
                           headers={"Origin": "https://archive.example.com"}).status_code == 400
        assert client.post("/api/v1/refresh", json={},
                           headers={"Origin": "https://other.example.com"}).status_code == 403
        assert client.get("/api/v1/health", headers={"Host": "other.example.com"}).status_code == 400
    assert config.read_text() == "invalid private configuration"


def test_hosted_hoyolab_is_request_scoped_and_checks_account_ownership(monkeypatch, tmp_path):
    monkeypatch.setenv("HOYO_HUB_PUBLIC", "1")
    monkeypatch.setenv("HOYO_HUB_ALLOWED_HOSTS", "archive.example.com")
    seen = []

    class Provider:
        def __init__(self, uid, resin):
            self.uid, self.resin = uid, resin

        async def get_game_accounts(self):
            await asyncio.sleep(0.01)
            return [SimpleNamespace(uid=self.uid, nickname="Private account", server="os_asia",
                                    level=60, game=genshin.Game.GENSHIN)]

        async def get_genshin_notes(self, uid, **kwargs):
            assert uid == int(self.uid)
            await asyncio.sleep(0.01)
            return {"current_resin": self.resin, "max_resin": 200, "expeditions": []}

        async def _request_genshin_record(self, operation, uid, **kwargs):
            assert operation == "index" and uid == int(self.uid)
            return {"world_explorations": []}

    def get_client(adapter):
        token = adapter.settings.cookies["ltoken_v2"].get_secret_value()
        uid, resin = {"first-secret": ("812345678", 11), "second-secret": ("823456789", 22)}[token]
        seen.append(adapter)
        return Provider(uid, resin)

    async def metadata(adapter):
        pass

    monkeypatch.setattr(HoYoLABClient, "get_client", get_client)
    monkeypatch.setattr(EnkaClient, "metadata", metadata)
    config = tmp_path / "config.json"
    headers = {"Origin": "https://archive.example.com"}
    first = {"enabled": True, "game_uid": "812345678", "cookies": {"ltuid_v2": "1", "ltoken_v2": "first-secret"}}
    second = {"enabled": True, "game_uid": "823456789", "cookies": {"ltuid_v2": "2", "ltoken_v2": "second-secret"}}
    app = create_app(config)
    with TestClient(app, base_url="https://archive.example.com") as client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda payload: client.post("/api/v1/hoyolab/notes", json=payload, headers=headers), [first, second]))
        assert [result.status_code for result in results] == [200, 200]
        assert [result.json()["data"]["resin"]["current"] for result in results] == [11, 22]
        assert [result.json()["data"]["uid"] for result in results] == [first["game_uid"], second["game_uid"]]
        assert seen[0] is not seen[1]
        for result in results:
            assert result.headers["cache-control"] == "no-store"
            assert "secret" not in result.text
        assert app.state.hub.settings.hoyolab.cookies == {}
        assert app.state.hub.hoyo.client is None
        assert not app.state.hub.cache.entries
        assert client.get("/api/v1/config").json()["data"]["hoyolab"]["configured"] is False
        accounts = client.post("/api/v1/hoyolab/accounts", json=second, headers=headers)
        assert accounts.json()["data"][0]["uid"] == second["game_uid"]
        exploration = client.post("/api/v1/hoyolab/explore", json=first, headers=headers)
        assert exploration.status_code == 200
        assert exploration.json()["data"]["uid"] == first["game_uid"]
        unauthorized = client.post("/api/v1/hoyolab/notes", json={**first, "game_uid": second["game_uid"]}, headers=headers)
        assert unauthorized.status_code == 400
        assert unauthorized.json()["error"]["code"] == "ACCOUNT_SELECTION_REQUIRED"
        assert "first-secret" not in unauthorized.text
        for payload, expected in (({}, 401), ({**first, "region": "bad"}, 422),
                                  ({**first, "cookies": {**first["cookies"], "other": "secret"}}, 422)):
            invalid = client.post("/api/v1/hoyolab/notes", json=payload, headers=headers)
            assert invalid.status_code == expected
            assert "first-secret" not in invalid.text
        assert client.post("/api/v1/hoyolab/notes", json=first).status_code == 403
        assert client.post("/api/v1/hoyolab/notes", json=first, headers={"Origin": "https://other.example.com"}).status_code == 403
        assert client.get("/api/v1/hoyolab/notes").status_code == 405
        assert client.post("/api/v1/hoyolab/notes", json={**first, "cookies": {"ltuid_v2": "1", "ltoken_v2": "x" * 17000}}, headers=headers).status_code == 413
    assert not config.exists()
