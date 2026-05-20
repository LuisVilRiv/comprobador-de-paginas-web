import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# Poner el directorio raíz del proyecto y docker/dashboard/api en sys.path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docker" / "dashboard" / "api"))

from app import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("shared.database.repositories.dashboard.get_settings")
def test_get_settings(mock_get_settings, client):
    # Caso 1: Obtener configuración global
    mock_get_settings.return_value = {
        "cron_active": "0 0 * * *",
        "cron_inactive": "0 12 * * *"
    }
    
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.json() == {
        "cron_active": "0 0 * * *",
        "cron_inactive": "0 12 * * *"
    }
    mock_get_settings.assert_called_once()


@patch("shared.database.repositories.dashboard.update_settings")
def test_update_settings(mock_update_settings, client):
    # Caso 2: Actualizar configuración global
    response = client.put("/settings", json={
        "cron_active": "*/5 * * * *",
        "cron_inactive": "0 0 * * 0"
    })
    
    assert response.status_code == 200
    assert response.json() == {"message": "Configuración actualizada correctamente"}
    mock_update_settings.assert_called_once_with(
        cron_active="*/5 * * * *",
        cron_inactive="0 0 * * 0"
    )


@patch("shared.database.repositories.dashboard.list_clients")
def test_get_clients(mock_list_clients, client):
    # Caso 3: Listar clientes
    mock_list_clients.return_value = [
        {"id": "1", "name": "Luis Vilches", "email": "luis@mail.com"}
    ]
    
    response = client.get("/clients")
    assert response.status_code == 200
    assert response.json() == [
        {"id": "1", "name": "Luis Vilches", "email": "luis@mail.com"}
    ]


@patch("shared.database.repositories.dashboard.create_client")
def test_create_client(mock_create_client, client):
    # Caso 4: Crear cliente
    mock_create_client.return_value = {"id": "2", "name": "Nuevo Cliente"}
    
    response = client.post("/clients", json={
        "name": "Nuevo Cliente",
        "email": "nuevo@mail.com",
        "phone": "123456",
        "company": "Mi Compañía",
        "notes": "Notas",
        "custom_cron": None
    })
    
    assert response.status_code == 200
    assert response.json() == {"id": "2", "name": "Nuevo Cliente"}
    mock_create_client.assert_called_once_with(
        "Nuevo Cliente",
        "nuevo@mail.com",
        "123456",
        "Mi Compañía",
        "Notas",
        None
    )


@patch("shared.database.repositories.dashboard.delete_client")
def test_delete_client(mock_delete_client, client):
    # Caso 5: Eliminar cliente exitosamente
    mock_delete_client.return_value = True
    response = client.delete("/clients/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Cliente eliminado", "client_id": "1"}
    mock_delete_client.assert_called_once_with("1")


@patch("shared.database.repositories.dashboard.list_websites")
def test_get_websites(mock_list_websites, client):
    # Caso 6: Listar websites/sitios web
    mock_list_websites.return_value = [
        {"website_id": "10", "url": "https://test.com", "strategy": "auto"}
    ]
    
    response = client.get("/websites")
    assert response.status_code == 200
    assert response.json() == [
        {"website_id": "10", "url": "https://test.com", "strategy": "auto"}
    ]


@patch("shared.database.repositories.dashboard.create_website")
def test_create_website(mock_create_website, client):
    # Caso 7: Crear website/sitio web
    mock_create_website.return_value = {"id": "15", "url": "https://new-web.com"}
    
    response = client.post("/websites", json={
        "url": "https://new-web.com",
        "label": "Nueva Web",
        "strategy": "beautifulsoup",
        "client_id": "1",
        "active": True,
        "custom_cron": "0 0 * * *"
    })
    
    assert response.status_code == 200
    assert response.json() == {"id": "15", "url": "https://new-web.com"}
    mock_create_website.assert_called_once_with(
        "1",
        "https://new-web.com",
        "Nueva Web",
        "beautifulsoup",
        True,
        "0 0 * * *"
    )


@patch("shared.database.repositories.dashboard.delete_website")
def test_delete_website(mock_delete_website, client):
    # Caso 8: Eliminar website/sitio web exitosamente
    mock_delete_website.return_value = True
    response = client.delete("/websites/10")
    assert response.status_code == 200
    assert response.json() == {"message": "Website eliminado", "website_id": "10"}
    mock_delete_website.assert_called_once_with("10")
