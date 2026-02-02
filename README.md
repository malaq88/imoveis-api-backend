# Imóveis API Backend

API RESTful para gerenciamento de imóveis de temporada e usuários, construída com FastAPI, SQLAlchemy e JWT.

## 📦 Tecnologias

* **Python 3.12+**  
* **FastAPI**: framework web  
* **SQLAlchemy**: ORM  
* **Pydantic**: validação de dados  
* **SQLite / PostgreSQL** (via `DATABASE_URL`)  
* **python-multipart + aiofiles**: upload de imagens  
* **JWT (jose)**: autenticação baseada em token  
* **passlib (bcrypt)**: hashing de senhas  

## 🚀 Funcionalidades

* **Autenticação** via JWT (com seed automático de usuário admin)  
* CRUD de **usuários** (apenas admin pode criar, deletar e listar usuários)  
* CRUD de **imóveis** (usuário autenticado)  
* **Flag de disponibilidade** nos imóveis  
* **Listagem pública** de imóveis disponíveis com filtros por distância, quartos e tipo de aluguel  
* **Listagem de imóveis indisponíveis** (usuário autenticado)  
* **Alternar disponibilidade** de um imóvel (usuário autenticado)  
* **Upload** e associação de imagens a imóveis  
* **Servir** imagens por rota protegida  
* **CORS** configurável  
* **Rate limiting** configurável  
* **Cache** de consultas frequentes  
* **Health checks** para monitoramento  

## 🔧 Instalação e Configuração

1. Clone o repositório:

   ```bash
   git clone https://github.com/seu-usuario/imoveis-api-backend.git
   cd imoveis-api-backend
   ```

2. Crie um ambiente virtual e instale dependências:

   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/macOS
   venv\Scripts\activate       # Windows
   pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` na raiz do projeto. Use o arquivo `.env.example` como referência:

   ```bash
   cp .env.example .env
   ```

   Edite o arquivo `.env` e configure as variáveis necessárias (veja seção de Configuração abaixo).

4. Inicie o servidor:

   ```bash
   uvicorn app.main:app --reload
   ```

   Acesse a documentação interativa em `http://127.0.0.1:8000/docs`.

## ⚙️ Configuração

### Variáveis de Ambiente

O arquivo `.env.example` contém todas as variáveis de ambiente necessárias. Principais configurações:

#### Obrigatórias
- `SECRET_KEY`: Chave secreta para assinatura de tokens JWT (gere uma chave forte)
- `DATABASE_URL`: URL de conexão com o banco de dados
- `ADMIN_USERNAME`: Username do usuário admin
- `ADMIN_EMAIL`: Email do usuário admin
- `ADMIN_PASSWORD`: Senha do usuário admin

#### Opcionais
- `ENVIRONMENT`: Ambiente de execução (`development` ou `production`)
- `CORS_ORIGINS`: Origens permitidas para CORS (`*` para todas ou lista separada por vírgulas)
- `LOG_FILE`: Caminho do arquivo de log (padrão: `app.log`)
- `LOG_LEVEL`: Nível de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `RATE_LIMIT_ENABLED`: Habilitar rate limiting (`true`/`false`)
- `RATE_LIMIT_PER_MINUTE`: Limite de requisições por minuto
- `CACHE_ENABLED`: Habilitar cache (`true`/`false`)
- `CACHE_TTL_SECONDS`: Tempo de vida do cache em segundos

Veja o arquivo `.env.example` para todas as opções disponíveis.

## 🛠️ Endpoints Principais

| Método | Rota                                   | Descrição                                         |
| ------ | -------------------------------------- | ------------------------------------------------- |
| POST   | `/token`                               | Gera JWT a partir de username e senha             |
| POST   | `/users/`                              | Cria usuário (admin apenas)                       |
| GET    | `/users/`                              | Lista usuários com paginação (admin apenas)       |
| GET    | `/users/me`                            | Retorna dados do usuário autenticado              |
| DELETE | `/users/{user_id}`                     | Deleta usuário por ID (admin apenas)              |
| GET    | `/imoveis`                             | Lista imóveis disponíveis com paginação e filtros  |
| GET    | `/imoveis_indisponiveis`               | Lista imóveis indisponíveis (usuário autenticado) |
| POST   | `/imoveis`                             | Cria imóvel (usuário autenticado)                 |
| PUT    | `/imoveis/{imovel_id}`                 | Atualiza imóvel (usuário autenticado)             |
| PATCH  | `/imoveis/{imovel_id}/disponibilidade` | Alterna disponibilidade do imóvel (usuário autenticado) |
| POST   | `/imoveis/{imovel_id}/images`          | Faz upload e associa imagens a imóvel (usuário autenticado) |
| GET    | `/images/{filename}`                   | Retorna a imagem (usuário autenticado)            |
| GET    | `/health/`                             | Health check da API                                |
| GET    | `/health/ready`                        | Readiness check (Kubernetes)                      |
| GET    | `/health/live`                         | Liveness check (Kubernetes)                       |

### 📄 Paginação

Todos os endpoints de listagem suportam paginação através dos parâmetros de query:
- `page`: Número da página (padrão: 1)
- `page_size`: Itens por página (padrão: 10, máximo: 100)

Exemplo: `/users/?page=1&page_size=20`

A resposta inclui:
```json
{
  "items": [...],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

### 🔍 Filtros

O endpoint `/imoveis` suporta os seguintes filtros:
- `distancia_praia`: Filtrar por distância da praia
- `quartos`: Filtrar por número mínimo de quartos
- `tipo_aluguel`: Filtrar por tipo de aluguel
- `page`: Número da página
- `page_size`: Itens por página

Exemplo: `/imoveis?quartos=2&distancia_praia=500m&page=1&page_size=10`

### 🚦 Rate Limiting

A API possui rate limiting configurável para proteger contra abuso:
- **Login**: 10 requisições por minuto
- **Criação de usuários**: 5 requisições por minuto
- **Listagem de usuários**: 30 requisições por minuto
- **Listagem de imóveis**: 60 requisições por minuto
- **Health checks**: Sem limite

Configure via variáveis de ambiente:
```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

### 💾 Cache

Consultas frequentes são cacheadas automaticamente para melhor performance:
- Listagem de imóveis com filtros
- TTL configurável (padrão: 5 minutos)
- Cache é limpo automaticamente quando imóveis são criados/atualizados

Configure via variáveis de ambiente:
```env
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
```

### 🏥 Health Checks

A API fornece endpoints para monitoramento:

- **GET `/health/`**: Health check completo com status de banco, cache e rate limiting
- **GET `/health/ready`**: Readiness check (usado por Kubernetes)
- **GET `/health/live`**: Liveness check (usado por Kubernetes)

## ✅ Testes

Usamos **pytest** para testes de unidade e integração. Para executar:

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/test_security.py -v
pytest tests/test_controllers.py -v
pytest tests/test_services.py -v

# Com verbose
pytest -v
```

### Estrutura de Testes

- `test_crud.py`: Testes unitários básicos dos services (CRUD)
- `test_services.py`: Testes completos dos services
- `test_controllers.py`: Testes de integração dos endpoints da API
- `test_dependencies.py`: Testes de autenticação e dependências
- `test_schemas.py`: Testes de validação de schemas
- `test_security.py`: Testes de segurança (path traversal, rollback, validações)
- `test_main.py`: Testes básicos da aplicação
- `test_rate_limit.py`: Testes de rate limiting

### Cobertura de Testes

Os testes cobrem:
- ✅ CRUD completo de usuários e imóveis
- ✅ Autenticação e autorização (JWT)
- ✅ Paginação e filtros
- ✅ Validação de schemas
- ✅ Casos de erro (404, 401, 403, 400)
- ✅ Edge cases (usuários desabilitados, tokens expirados, etc)
- ✅ Health checks
- ✅ Rate limiting
- ✅ Cache
- ✅ Segurança (path traversal, validação de arquivos)
- ✅ Rollback de transações
- ✅ Tratamento de erros em operações de arquivo

**Total: 95 testes** (todos passando)

### Configuração para Testes

Os testes usam banco de dados em memória (SQLite) e desabilitam automaticamente:
- Rate limiting
- Cache

Isso garante testes rápidos e isolados.

## 🔒 Segurança e Melhorias Implementadas

### Segurança
- ✅ Autenticação JWT implementada
- ✅ Senhas hasheadas com bcrypt
- ✅ Rate limiting configurável
- ✅ Validação de tipos de arquivo (apenas JPEG/PNG)
- ✅ Validação de tamanho de arquivo
- ✅ **Validação de path traversal em uploads** (prevenção de ataques)
- ✅ **Sanitização de nomes de arquivo**
- ✅ CORS configurável
- ✅ **Tratamento de erros em operações de arquivo com limpeza automática**

### Confiabilidade
- ✅ **Tratamento de transações com rollback** em todas as operações de banco
- ✅ **Tratamento adequado de erros de I/O**
- ✅ **Limpeza automática de arquivos em caso de erro**
- ✅ Validação de dados com Pydantic
- ✅ Tratamento de erros melhorado

### Performance
- ✅ Paginação em todas as listagens
- ✅ Índices no banco de dados para campos filtrados
- ✅ Índices compostos para consultas comuns
- ✅ Cache em memória com TTL
- ✅ Cache automático de consultas frequentes
- ✅ Invalidação automática em atualizações

### Qualidade de Código
- ✅ Sistema de logging configurável via variáveis de ambiente
- ✅ Remoção de código duplicado
- ✅ Substituição de métodos obsoletos do SQLAlchemy
- ✅ Separação de responsabilidades (controllers, services, models)

### Monitoramento
- ✅ Health check endpoint
- ✅ Readiness check para Kubernetes
- ✅ Liveness check para Kubernetes
- ✅ Métricas de cache e rate limiting

### Documentação
- ✅ OpenAPI/Swagger melhorado
- ✅ Exemplos de requisições e respostas
- ✅ Descrições detalhadas de endpoints
- ✅ Documentação de erros
- ✅ Arquivo `.env.example` completo

## 📋 Checklist para Produção

### ✅ Concluído
- ✅ Tratamento de transações com rollback
- ✅ Validação de path traversal em uploads
- ✅ Tratamento de erros em operações de arquivo
- ✅ Logging configurável via variáveis de ambiente
- ✅ Arquivo `.env.example` criado
- ✅ Testes de segurança implementados
- ✅ Isolamento adequado entre testes

### ⚠️ Recomendado antes de Produção
- [ ] Migrar de SQLite para PostgreSQL/MySQL
- [ ] Configurar HTTPS obrigatório
- [ ] Adicionar headers de segurança (HSTS, CSP, etc.)
- [ ] Configurar monitoramento e alertas (Sentry, DataDog, etc.)
- [ ] Implementar estratégia de backup do banco de dados
- [ ] Configurar connection pooling otimizado
- [ ] Considerar cache distribuído (Redis) para alta carga
- [ ] Adicionar versionamento de API (`/api/v1/`)

## 🚨 Observação Importante

**SQLite não é recomendado para produção**. Para produção, migre para PostgreSQL ou MySQL antes do deploy. Configure adequadamente:
- Connection pooling
- Backup automático
- Monitoramento de performance

## 📝 Licença

MIT License - veja arquivo `LICENSE` para detalhes.
