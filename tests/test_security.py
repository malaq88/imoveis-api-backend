"""
Testes de segurança e validação de arquivos
"""
import pytest
import os
import tempfile
from io import BytesIO
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
# PIL pode não estar instalado, vamos usar alternativa
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import atexit

# Configuração de banco de dados de teste (mesma estrutura do test_controllers.py)
# Usa um nome único para evitar conflito com outros arquivos de teste
import uuid
temp_db_path = tempfile.gettempdir() + f"/test_security_{uuid.uuid4().hex}.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{temp_db_path}"

def cleanup_temp_db():
    try:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
    except:
        pass
atexit.register(cleanup_temp_db)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importa database mas NÃO sobrescreve globalmente para evitar conflito com outros testes
import database
from database import Base

# Garante que os modelos sejam importados
from app.models import user_model, imovel_model
Base.metadata.create_all(bind=engine)

# Importa o app
from app.main import app
from app.core.dependencies import get_db, pwd_context
from app.core.config import settings
from app.services import user_service
from app.schemas import user_schema
from app.controllers.imovel_controller import validar_filename, router

# Desabilita rate limiting para testes
settings.RATE_LIMIT_ENABLED = False

def override_get_db():
    """Override da dependência get_db para testes"""
    # Usa o engine local deste arquivo de teste
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Configura o banco de dados para cada teste - garante isolamento"""
    # Cria tabelas se necessário
    Base.metadata.create_all(bind=engine)
    
    # Salva override anterior se existir
    old_override = app.dependency_overrides.get(get_db)
    
    # Configura nosso override
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # Restaura override anterior ou remove o nosso
    if old_override:
        app.dependency_overrides[get_db] = old_override
    else:
        app.dependency_overrides.pop(get_db, None)
    
    # Limpa dados após cada teste
    db_cleanup = TestingSessionLocal()
    try:
        db_cleanup.query(imovel_model.Image).delete()
        db_cleanup.query(imovel_model.Imovel).delete()
        db_cleanup.query(user_model.User).delete()
        db_cleanup.commit()
    except:
        db_cleanup.rollback()
    finally:
        db_cleanup.close()

@pytest.fixture(scope="function")
def client():
    """Cria um cliente de teste"""
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """Cria uma sessão de banco de dados para cada teste"""
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

@pytest.fixture(scope="function")
def admin_user(db_session):
    """Cria um usuário admin para testes"""
    # Sempre cria um novo admin para garantir isolamento
    # Primeiro limpa qualquer admin existente
    existing = user_service.get_user_by_username(db_session, "admin_test")
    if existing:
        db_session.delete(existing)
        db_session.commit()
    
    admin = user_schema.UserCreate(
        username="admin_test",
        email="admin@test.com",
        full_name="Admin Test",
        password="admin123",
        is_admin=True
    )
    created = user_service.create_user(db_session, admin)
    db_session.commit()
    db_session.refresh(created)
    return created

@pytest.fixture(scope="function")
def admin_token(client, admin_user, db_session):
    """Obtém token de autenticação do admin"""
    # Garante que o usuário está commitado e visível
    db_session.commit()
    db_session.refresh(admin_user)
    
    # Força flush para garantir que está disponível
    db_session.flush()
    
    response = client.post(
        "/token",
        data={"username": "admin_test", "password": "admin123"}
    )
    
    if response.status_code != 200:
        # Debug: verifica se o usuário existe no banco
        check_user = user_service.get_user_by_username(db_session, "admin_test")
        if not check_user:
            pytest.fail(f"Admin user not found in database. Response: {response.text}")
        # Verifica se a senha está correta
        from app.core.dependencies import verify_password
        if not verify_password("admin123", check_user.hashed_password):
            pytest.fail(f"Password verification failed. Response: {response.text}")
        pytest.fail(f"Login failed: {response.text}. User exists: {check_user.username}")
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    assert "access_token" in response.json(), f"Response: {response.json()}"
    return response.json()["access_token"]


class TestPathTraversalValidation:
    """Testes para validação de path traversal"""
    
    def test_validar_filename_safe(self):
        """Testa validação com filename seguro"""
        safe_name = validar_filename("imagem.jpg")
        assert safe_name == "imagem.jpg"
    
    def test_validar_filename_with_path_traversal(self):
        """Testa que path traversal é sanitizado"""
        # os.path.basename remove os componentes de caminho
        # Então ../../../etc/passwd vira apenas "passwd"
        safe_name = validar_filename("../../../etc/passwd")
        assert safe_name == "passwd"
        assert ".." not in safe_name
        assert "/" not in safe_name
        
        # Testa com .. no meio - basename também remove isso, mas a validação deve detectar
        # Como basename já removeu os componentes, vamos testar diretamente com um nome que contenha ..
        # Mas após basename, "imagem../test.jpg" vira "test.jpg", então não há mais ..
        # Vamos testar com um nome que contenha .. após basename (que não acontece naturalmente)
        # Na prática, basename já remove tudo, então vamos apenas verificar que funciona
        safe_name2 = validar_filename("imagem../test.jpg")
        # basename remove os componentes, então vira apenas "test.jpg"
        assert ".." not in safe_name2
        assert "/" not in safe_name2
    
    def test_validar_filename_with_slash(self):
        """Testa que barras são removidas por basename"""
        # os.path.basename remove os componentes de caminho
        # Então path/to/file.jpg vira apenas "file.jpg"
        safe_name = validar_filename("path/to/file.jpg")
        assert safe_name == "file.jpg"
        assert "/" not in safe_name
    
    def test_validar_filename_with_backslash(self):
        """Testa que barras invertidas são bloqueadas"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            validar_filename("path\\to\\file.jpg")
        assert exc_info.value.status_code == 400
    
    def test_validar_filename_sanitizes_special_chars(self):
        """Testa que caracteres especiais são removidos"""
        safe_name = validar_filename("imagem@#$%test.jpg")
        # Caracteres especiais devem ser removidos, mas mantém .jpg
        assert ".jpg" in safe_name
        assert "@" not in safe_name
        assert "#" not in safe_name
    
    def test_validar_filename_empty_after_sanitization(self):
        """Testa que filename vazio após sanitização é rejeitado"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            validar_filename("@@@###")
        assert exc_info.value.status_code == 400


class TestFileUploadSecurity:
    """Testes de segurança para upload de arquivos"""
    
    def test_upload_with_path_traversal_filename(self, client, admin_token):
        """Testa que upload com path traversal no filename é sanitizado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Cria um arquivo de imagem fake (JPEG válido mínimo)
        # JPEG header: FF D8 FF E0 00 10 4A 46 49 46 00 01
        jpeg_header = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01])
        img_bytes = BytesIO(jpeg_header + b"fake image data")
        img_bytes.seek(0)
        
        # Tenta fazer upload com filename perigoso
        # O filename será sanitizado, então o upload deve funcionar
        files = [("imagens", ("../../../etc/passwd.jpg", img_bytes, "image/jpeg"))]
        data = {
            "titulo": "Test",
            "descricao": "Test desc",
            "metragem": "80",
            "quartos": "2",
            "distancia_praia": "100m",
            "tipo_aluguel": "Diária",
            "mobilhada": "true",
            "preco": "500.00"
        }
        
        response = client.post("/imoveis", data=data, files=files, headers=headers)
        # O filename será sanitizado e o upload deve funcionar
        # Mas o arquivo salvo terá um nome UUID, não o filename original
        assert response.status_code == 200
    
    def test_serve_image_path_traversal(self, client, admin_token):
        """Testa que servir imagem com path traversal é sanitizado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Tenta acessar com path traversal
        # O filename será sanitizado para apenas "passwd"
        response = client.get("/images/../../../etc/passwd", headers=headers)
        # Como o arquivo não existe, retorna 404 (não 400, pois foi sanitizado)
        assert response.status_code == 404
    
    def test_serve_image_with_slash(self, client, admin_token):
        """Testa que servir imagem com barra é sanitizado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # O filename será sanitizado para apenas "file.jpg"
        response = client.get("/images/path/to/file.jpg", headers=headers)
        # Como o arquivo não existe, retorna 404 (não 400, pois foi sanitizado)
        assert response.status_code == 404


class TestTransactionRollback:
    """Testes para verificar que rollback funciona corretamente"""
    
    def test_create_user_rollback_on_error(self, db_session):
        """Testa que rollback funciona ao criar usuário com erro"""
        from app.services import user_service
        from app.schemas import user_schema
        from sqlalchemy.exc import IntegrityError
        
        # Cria um usuário válido
        user1 = user_schema.UserCreate(
            username="testuser1",
            email="test1@test.com",
            full_name="Test User 1",
            password="password123",
            is_admin=False
        )
        user_service.create_user(db_session, user1)
        db_session.commit()
        
        # Tenta criar usuário com email duplicado (deve falhar e fazer rollback)
        user2 = user_schema.UserCreate(
            username="testuser2",
            email="test1@test.com",  # Email duplicado
            full_name="Test User 2",
            password="password123",
            is_admin=False
        )
        
        # Deve levantar exceção e fazer rollback
        try:
            user_service.create_user(db_session, user2)
            db_session.commit()
            pytest.fail("Deveria ter levantado exceção")
        except Exception:
            # Verifica que rollback foi chamado (não há commit)
            db_session.rollback()
            # Verifica que o segundo usuário não foi criado
            from app.models import user_model
            user = db_session.query(user_model.User).filter(
                user_model.User.username == "testuser2"
            ).first()
            assert user is None
    
    def test_create_imovel_rollback_on_error(self, db_session):
        """Testa que rollback funciona ao criar imóvel com erro"""
        from app.services import imovel_service
        from app.schemas import imovel_schema
        from app.models import imovel_model
        
        # Cria imóvel válido
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Test Rollback",
            descricao="Desc",
            metragem=80,
            quartos=2,
            distancia_praia="100m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
            disponivel=True
        )
        
        # Simula erro forçando uma exceção durante commit
        # Mock do commit para levantar exceção
        original_commit = db_session.commit
        def failing_commit():
            raise Exception("Database error")
        
        db_session.commit = failing_commit
        
        try:
            try:
                imovel_service.criar_imovel(db_session, imovel_in, image_filenames=["test.jpg"])
                pytest.fail("Deveria ter levantado exceção")
            except Exception:
                # Verifica que rollback foi chamado
                db_session.rollback()
                # Restaura commit original
                db_session.commit = original_commit
                # Verifica que imóvel não foi criado
                imovel = db_session.query(imovel_model.Imovel).filter(
                    imovel_model.Imovel.titulo == "Test Rollback"
                ).first()
                assert imovel is None
        finally:
            # Restaura commit original
            db_session.commit = original_commit


class TestFileOperationErrors:
    """Testes para tratamento de erros em operações de arquivo"""
    
    def test_upload_file_io_error(self, client, admin_token):
        """Testa tratamento de erro de I/O ao fazer upload"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Cria um arquivo de imagem fake (JPEG válido mínimo)
        jpeg_header = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01])
        img_bytes = BytesIO(jpeg_header + b"fake image data")
        img_bytes.seek(0)
        
        files = [("imagens", ("test.jpg", img_bytes, "image/jpeg"))]
        data = {
            "titulo": "Test",
            "descricao": "Test desc",
            "metragem": "80",
            "quartos": "2",
            "distancia_praia": "100m",
            "tipo_aluguel": "Diária",
            "mobilhada": "true",
            "preco": "500.00"
        }
        
        # Mock para simular erro de I/O
        with patch('aiofiles.open', side_effect=OSError("Disk full")):
            response = client.post("/imoveis", data=data, files=files, headers=headers)
            # Deve retornar erro 500 e limpar arquivos salvos
            assert response.status_code == 500
            assert "Erro ao salvar arquivo" in response.json()["detail"]
    
    def test_serve_image_not_found(self, client, admin_token):
        """Testa que servir imagem inexistente retorna 404"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = client.get("/images/naoexiste.jpg", headers=headers)
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"]
    
    def test_serve_image_io_error(self, client, admin_token, db_session):
        """Testa tratamento de erro de I/O ao servir imagem"""
        from app.models import imovel_model
        from app.services import imovel_service
        from app.schemas import imovel_schema
        from app.core.config import settings
        import os
        
        # Cria imóvel com imagem
        imovel_in = imovel_schema.ImovelCreate(
            titulo="Test",
            descricao="Desc",
            metragem=80,
            quartos=2,
            distancia_praia="100m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
            disponivel=True
        )
        imovel = imovel_service.criar_imovel(db_session, imovel_in, image_filenames=["test.jpg"])
        db_session.commit()
        
        # Cria um arquivo fake para simular o arquivo existente
        images_dir = settings.IMAGES_DIR
        os.makedirs(images_dir, exist_ok=True)
        test_file_path = os.path.join(images_dir, "test.jpg")
        with open(test_file_path, "wb") as f:
            f.write(b"fake image data")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Mock para simular erro de I/O ao ler arquivo
        # Como FileResponse é usado diretamente, vamos mockar os.path.isfile para retornar True
        # e depois mockar FileResponse para levantar erro
        with patch('os.path.isfile', return_value=True):
            with patch('fastapi.responses.FileResponse', side_effect=OSError("Cannot read file")):
                response = client.get("/images/test.jpg", headers=headers)
                # Deve retornar erro 500
                assert response.status_code == 500
        
        # Limpa o arquivo de teste
        try:
            os.remove(test_file_path)
        except:
            pass


class TestFileValidation:
    """Testes para validação de tipos e tamanhos de arquivo"""
    
    def test_upload_invalid_file_type(self, client, admin_token):
        """Testa que tipo de arquivo inválido é rejeitado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Cria um arquivo que não é imagem
        files = [("imagens", ("test.txt", BytesIO(b"not an image"), "text/plain"))]
        data = {
            "titulo": "Test",
            "descricao": "Test desc",
            "metragem": "80",
            "quartos": "2",
            "distancia_praia": "100m",
            "tipo_aluguel": "Diária",
            "mobilhada": "true",
            "preco": "500.00"
        }
        
        response = client.post("/imoveis", data=data, files=files, headers=headers)
        assert response.status_code == 400
        assert "JPEG ou PNG" in response.json()["detail"]
    
    def test_upload_file_too_large(self, client, admin_token):
        """Testa que arquivo muito grande é rejeitado"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Cria um arquivo muito grande (simulado)
        large_file = BytesIO(b"x" * (15 * 1024 * 1024))  # 15MB
        
        files = [("imagens", ("large.jpg", large_file, "image/jpeg"))]
        data = {
            "titulo": "Test",
            "descricao": "Test desc",
            "metragem": "80",
            "quartos": "2",
            "distancia_praia": "100m",
            "tipo_aluguel": "Diária",
            "mobilhada": "true",
            "preco": "500.00"
        }
        
        response = client.post("/imoveis", data=data, files=files, headers=headers)
        assert response.status_code == 400
        assert "muito grande" in response.json()["detail"]

