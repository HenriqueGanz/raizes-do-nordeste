# Raízes do Nordeste - Back-end

API REST da rede de lanchonetes nordestinas **Raízes do Nordeste**: múltiplos canais (app, totem,
balcão, pick-up)

## Stack

Python 3.12 · FastAPI · PostgreSQL 16 · Redis (cache) · RabbitMQ + Celery (filas) · SQLAlchemy 2 · Docker.

## Como executar (Docker)

O `docker-compose` sobe a API e o banco ja conectados, com o schema (`db/schema.sql`) aplicado no
primeiro boot.

```bash
# Sobe API + Postgres (+ Redis/RabbitMQ para o caminho assincrono)
docker-compose up --build
#    API em http://localhost:8000 - documentação interativa em /docs

docker-compose exec api python scripts/seed_db.py

# derruba tudo e zerar o banco:
docker-compose down -v
```

> Quem usa o plugin v2 do Docker pode rodar `docker compose up --build` (mesmo arquivo).

### Credenciais de teste

Criadas pelo seed, para usar em `POST /v1/auth/login`:

| Papel | E-mail | Senha |
|-------|--------|-------|
| ADMIN | `admin@raizesdonordeste.com.br` | `admin123` |
| OPERADOR | `operador@raizesdonordeste.com.br` | `operador123` |
| CLIENTE | `demo@raizesdonordeste.com.br` | `cliente123` (CPF `12345678900`) |

### Rodar sem Docker (opcional)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
psql "$DATABASE_URL" -f db/schema.sql   # cria o schema
uvicorn app.main:app --reload           # sobe a API
```

## Testes

A suíte roda sem infraestrutura (SQLite em memória), pois os modelos usam tipos portáveis do
SQLAlchemy (`Uuid`, `JSON`).

```bash
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Postman

Importe `postman/raizes_do_nordeste_v1.postman_collection.json` no Postman e rode na ordem das
pastas. Tokens, IDs e a chave de idempotência do pagamento são capturados automaticamente entre as
requisições.

## Endpoints

**Públicos:**

| Método | Rota | O que faz |
|--------|------|-----------|
| `POST` | `/v1/auth/login` | Login - devolve o token JWT |
| `POST` | `/v1/clientes` | Auto-cadastro de cliente |
| `GET`  | `/v1/unidades` | Lista as lojas ativas |
| `GET`  | `/v1/unidades/{unidade_id}/cardapio` | Cardápio da unidade (região, sazonalidade, estoque) |
| `POST` | `/v1/pedidos` | Cria pedido no TOTEM/BALCAO/PICKUP; `cpf` opcional vincula o cliente. No canal **APP** exige login |
| `GET`  | `/v1/pedidos/{pedido_id}` | Acompanha o status do pedido |
| `POST` | `/v1/webhooks/pagamento` | Confirmação/negativa do gateway (assinado e idempotente) |

**Cliente autenticado (próprios dados):**

| Método | Rota | O que faz |
|--------|------|-----------|
| `POST` | `/v1/pedidos` | Cria pedido no canal **APP**; vinculado à identidade do token |
| `GET` / `PUT` | `/v1/clientes/{id}` | Consulta/edita o próprio cadastro |
| `DELETE` | `/v1/clientes/{id}` | Anonimização LGPD (direito ao esquecimento) |
| `GET`  | `/v1/clientes/{id}/pedidos` | Histórico de pedidos |
| `POST` / `DELETE` | `/v1/clientes/{id}/consentimentos` | Registra/revoga consentimento LGPD |
| `POST` | `/v1/clientes/{id}/resgates` | Resgata pontos de fidelidade por cupom |

**ADMIN (matriz) e OPERADOR (cozinha):**

| Papel | Método | Rota | O que faz |
|-------|--------|------|-----------|
| ADMIN | `POST/GET/PUT/DELETE` | `/v1/produtos[/{id}]` | CRUD do catálogo central |
| ADMIN | `POST/PUT` | `/v1/unidades[/{id}]` | Cria/edita unidades |
| ADMIN | `PUT/DELETE` | `/v1/unidades/{id}/cardapio/{produto_id}` | Define a oferta local (preço, estoque, vigência) |
| ADMIN | `GET` | `/v1/relatorios/vendas` | Indicadores de vendas por unidade/período |
| OPERADOR | `POST` | `/v1/pedidos/{id}/aceitar\|pronto\|entregar\|cancelar` | Avança/cancela o pedido |
| OPERADOR | `POST` | `/v1/pedidos/{id}/desconto` | Desconto antes do pagamento (auditado) |
| OPERADOR | `GET` | `/v1/unidades/{id}/fila` | Painel da cozinha (KDS) |

> **Autenticação:** envie `Authorization: Bearer <token>` (obtido em `/v1/auth/login`). Operações
> sensíveis (desconto, cancelamento, anonimização, acúmulo/resgate de pontos) geram registro em
> `audit_log`.
