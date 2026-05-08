import json
import pytest
from pathlib import Path
from utils.url_loader import UrlLoader


@pytest.fixture
def valid_json(tmp_path: Path) -> Path:
    data = {
        "urls": [
            {"id": 1, "url": "https://a.com", "strategy": "selenium",       "active": True},
            {"id": 2, "url": "https://b.com", "strategy": "beautifulsoup",  "active": True},
            {"id": 3, "url": "https://c.com", "strategy": "selenium",       "active": False},
        ]
    }
    p = tmp_path / "urls.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def loader(valid_json: Path) -> UrlLoader:
    return UrlLoader(path=valid_json)


class TestUrlLoaderLoad:
    def test_carga_solo_activas_por_defecto(self, loader):
        entries = loader.load()
        assert len(entries) == 2

    def test_carga_todas_si_only_active_false(self, loader):
        entries = loader.load(only_active=False)
        assert len(entries) == 3

    def test_devuelve_lista_de_dicts(self, loader):
        entries = loader.load()
        assert all(isinstance(e, dict) for e in entries)


class TestUrlLoaderValidation:
    def test_ignora_url_invalida(self, tmp_path):
        data = {"urls": [{"url": "no-es-url", "strategy": "selenium"}]}
        p = tmp_path / "urls.json"
        p.write_text(json.dumps(data))
        assert UrlLoader(p).load() == []

    def test_ignora_estrategia_desconocida(self, tmp_path):
        data = {"urls": [{"url": "https://x.com", "strategy": "phantomjs"}]}
        p = tmp_path / "urls.json"
        p.write_text(json.dumps(data))
        assert UrlLoader(p).load() == []

    def test_lanza_si_fichero_no_existe(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            UrlLoader(tmp_path / "nope.json").load()

    def test_lanza_si_json_malformado(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ValueError):
            UrlLoader(p).load()

    def test_lanza_si_falta_clave_urls(self, tmp_path):
        p = tmp_path / "no_urls.json"
        p.write_text(json.dumps({"data": []}))
        with pytest.raises(ValueError):
            UrlLoader(p).load()


class TestUrlLoaderByStrategy:
    def test_filtra_por_estrategia(self, loader):
        entries = loader.load_by_strategy("selenium")
        assert all(e["strategy"] == "selenium" for e in entries)

    def test_devuelve_vacio_si_no_hay_coincidencias(self, loader):
        assert loader.load_by_strategy("phantomjs") == []
