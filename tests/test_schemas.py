"""
Testes para schemas e validações
"""
import pytest
from pydantic import ValidationError
from app.schemas import user_schema, imovel_schema, pagination_schema


class TestUserSchemas:
    """Testes para schemas de usuário"""
    
    def test_user_create_valid(self):
        """Testa criação de schema de usuário válido"""
        user = user_schema.UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            is_admin=False
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.password == "password123"
        assert user.is_admin is False
    
    def test_user_create_invalid_email(self):
        """Testa criação de schema com email inválido"""
        with pytest.raises(ValidationError):
            user_schema.UserCreate(
                username="testuser",
                email="invalid_email",
                full_name="Test User",
                password="password123",
                is_admin=False
            )
    
    def test_user_create_missing_required(self):
        """Testa criação de schema com campos obrigatórios faltando"""
        with pytest.raises(ValidationError):
            user_schema.UserCreate(
                username="testuser",
                # email faltando
                full_name="Test User",
                password="password123"
            )


class TestImovelSchemas:
    """Testes para schemas de imóvel"""
    
    def test_imovel_create_valid(self):
        """Testa criação de schema de imóvel válido"""
        imovel = imovel_schema.ImovelCreate(
            titulo="Apartamento Teste",
            descricao="Descrição do apartamento",
            metragem=80,
            quartos=2,
            distancia_praia="200m",
            tipo_aluguel="Diária",
            mobilhada=True,
            preco="500.00",
            disponivel=True
        )
        assert imovel.titulo == "Apartamento Teste"
        assert imovel.metragem == 80
        assert imovel.quartos == 2
        assert imovel.preco == "500.00"
    
    def test_imovel_create_invalid_metragem(self):
        """Testa criação de schema com metragem inválida (negativa)"""
        with pytest.raises(ValidationError):
            imovel_schema.ImovelCreate(
                titulo="Apartamento Teste",
                descricao="Descrição",
                metragem=-10,  # Inválido
                quartos=2,
                distancia_praia="200m",
                tipo_aluguel="Diária",
                mobilhada=True,
                preco="500.00"
            )
    
    def test_imovel_create_invalid_quartos(self):
        """Testa criação de schema com quartos inválido (negativo)"""
        with pytest.raises(ValidationError):
            imovel_schema.ImovelCreate(
                titulo="Apartamento Teste",
                descricao="Descrição",
                metragem=80,
                quartos=-1,  # Inválido
                distancia_praia="200m",
                tipo_aluguel="Diária",
                mobilhada=True,
                preco="500.00"
            )
    
    def test_imovel_create_empty_titulo(self):
        """Testa criação de schema com título vazio"""
        with pytest.raises(ValidationError):
            imovel_schema.ImovelCreate(
                titulo="",  # Inválido (min_length=1)
                descricao="Descrição",
                metragem=80,
                quartos=2,
                distancia_praia="200m",
                tipo_aluguel="Diária",
                mobilhada=True,
                preco="500.00"
            )
    
    def test_imovel_update_partial(self):
        """Testa atualização parcial de imóvel"""
        imovel = imovel_schema.ImovelUpdate(
            titulo="Novo Título",
            metragem=100
        )
        assert imovel.titulo == "Novo Título"
        assert imovel.metragem == 100
        assert imovel.quartos is None
        assert imovel.descricao is None
    
    def test_imovel_update_all_none(self):
        """Testa atualização com todos os campos None"""
        imovel = imovel_schema.ImovelUpdate()
        assert imovel.titulo is None
        assert imovel.metragem is None
        assert imovel.quartos is None


class TestPaginationSchemas:
    """Testes para schemas de paginação"""
    
    def test_paginated_response_create(self):
        """Testa criação de resposta paginada"""
        items = [1, 2, 3, 4, 5]
        total = 10
        page = 1
        page_size = 5
        
        response = pagination_schema.PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
        
        assert response.items == items
        assert response.total == total
        assert response.page == page
        assert response.page_size == page_size
        assert response.total_pages == 2  # 10 / 5 = 2
    
    def test_paginated_response_empty(self):
        """Testa resposta paginada vazia"""
        response = pagination_schema.PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=10
        )
        
        assert len(response.items) == 0
        assert response.total == 0
        assert response.total_pages == 0
    
    def test_paginated_response_last_page(self):
        """Testa última página da paginação"""
        items = [6, 7, 8]
        total = 8
        page = 2
        page_size = 5
        
        response = pagination_schema.PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
        
        assert len(response.items) == 3
        assert response.total_pages == 2

