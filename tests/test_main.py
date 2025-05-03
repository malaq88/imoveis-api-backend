# tests/test_main.py
import pytest
from fastapi import FastAPI
from app.main import app


def test_app_instance():
    """
    Verifica que a aplicação FastAPI foi criada corretamente.
    """
    assert isinstance(app, FastAPI)


def test_endpoints_registered():
    """
    Verifica que as rotas principais estão registradas na aplicação.
    """
    paths = {route.path for route in app.router.routes}
    expected = {
        "/token",
        "/imoveis",
        "/imoveis/{imovel_id}",
        "/imoveis/{imovel_id}/images",
        "/images/{filename}",
        "/users/",
        "/users/me",
    }
    for path in expected:
        assert path in paths, f"Rota {path} não registrada"


def test_dependency_functions_exist():
    """
    Verifica que as dependências de autenticação estão definidas.
    """
    from app.main import verify_password, authenticate_user, get_current_user
    # Funções devem existir e ser chamáveis (sem executar lógica)
    assert callable(verify_password)
    assert callable(authenticate_user)
    assert callable(get_current_user)
