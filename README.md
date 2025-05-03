# Imóveis API Backend

API RESTful para gerenciamento de imóveis de temporada e usuários, construída com FastAPI, SQLAlchemy e JWT.

## 📦 Tecnologias

* **Python 3.13**
* **FastAPI**: framework web
* **SQLAlchemy**: ORM
* **Pydantic**: validação de dados
* **SQLite / PostgreSQL** (via `DATABASE_URL`)
* **python-multipart + aiofiles**: upload de imagens
* **JWT (jose)**: autenticação baseada em token
* **passlib (bcrypt)**: hashing de senhas

## 🚀 Funcionalidades

* **Autenticação** via JWT (com seed automático de usuário admin)
* CRUD de **usuários** (apenas admin pode criar outros usuários)
* CRUD de **imóveis** (admin)
* **Listagem pública** de imóveis com filtros por distância, quartos e tipo de aluguel
* **Upload** e associação de imagens a imóveis
* **Servir** imagens por rota protegida
* **CORS** habilitado para todos os domínios

## 🔧 Instalação e configuração

1. Clone o repositório:

   ```bash
   git clone https://github.com/seu-usuario/imoveis-api-backend.git
   cd imoveis-api-backend
   ```
2. Crie um ambiente virtual e instale dependências:

   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/macOS
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```
3. Crie um arquivo `.env` na raiz do projeto com as variáveis:

   ```dotenv
   # settings.py
   SECRET_KEY=uma_chave_secreta
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # database.py
   DATABASE_URL=sqlite:///./dev.db       # ou URL de PostgreSQL

   # seed do admin (lifespan)
   ADMIN_USERNAME=admin
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=senha_admin
   ```
4. Inicie o servidor:

   ```bash
   uvicorn app.main:app --reload
   ```

   Acesse a documentação interativa em `http://127.0.0.1:8000/docs`.

## 🛠️ Endpoints principais

| Método | Rota                          | Descrição                             |
| ------ | ----------------------------- | ------------------------------------- |
| POST   | `/token`                      | Gera JWT a partir de username e senha |
| POST   | `/users/`                     | Cria usuário (admin apenas)           |
| GET    | `/users/me`                   | Retorna dados do usuário autenticado  |
| GET    | `/imoveis`                    | Lista imóveis (público, com filtros)  |
| POST   | `/imoveis`                    | Cria imóvel (admin)                   |
| PUT    | `/imoveis/{imovel_id}`        | Atualiza imóvel (admin)               |
| POST   | `/imoveis/{imovel_id}/images` | Faz upload e associa imagens (admin)  |
| GET    | `/images/{filename}`          | Retorna a imagem (admin)              |

## ✅ Testes

Usamos **pytest** para testes de unidade (*crud*) e integração (*rotas básicas*). Para executar:

```bash
pytest
```

