from fastapi.testclient import TestClient

from app import create_app


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
