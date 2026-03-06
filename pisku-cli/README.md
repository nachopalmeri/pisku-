# PISKU — Stop wasting tokens on irrelevant context

> **CLI tool para developers que usan LLMs a diario.**
> Seleccioná exactamente qué skills y docs mandarle al modelo. Cero ruido. Hasta 80% menos tokens por sesión.

```
$ pisku init mi-dapp

  📚 Select skills for your context:

  ── BACKEND ──
   1. python-fastapi       (3.2 KB)
   2. postgresql-sqlalchemy (4.1 KB)

  ── WEB3 ──
   3. solidity-base        (5.6 KB)

  Your selection: 1,3

  ✅ Context saved → docs/contexts/mi-dapp_20250306.md
  💰 Tokens saved: ~4,000
```

---

## Tabla de contenidos

- [Instalación](#instalación)
- [Quickstart](#quickstart)
- [Comandos](#comandos)
- [Modelo Freemium](#modelo-freemium)
- [Skills incluidas](#skills-incluidas)
- [Servidor](#servidor)
- [Integración Stripe](#integración-stripe)
- [Deploy en producción](#deploy-en-producción)
- [Estructura del proyecto](#estructura-del-proyecto)

---

## Instalación

**Requisitos:** Python 3.11 o superior.

```bash
pip install pisku
```

Verificá que funciona:

```bash
pisku version
# → PISKU v0.1.0 — 🆓 FREE
```

---

## Quickstart

### 1. Iniciá un proyecto

```bash
pisku init mi-proyecto
```

Aparece un menú numerado con todas tus skills disponibles. Elegís por número (ej: `1,3`) y PISKU arma el archivo de contexto final.

### 2. Listá tus skills

```bash
pisku list
pisku list --category backend    # filtrado por categoría
```

### 3. Agregá una skill propia

```bash
# Crea template vacío
pisku add-skill mi-skill --category backend

# O importá un .md existente
pisku add-skill mi-skill --category backend --file ./mi-doc.md
```

### 4. Usá el contexto generado

El archivo `.md` que genera PISKU lo pegás al inicio de tu conversación con Claude, GPT, Gemini, o cualquier LLM. El modelo recibe solo lo relevante para ese proyecto.

### 5. Ver tus stats (FREE)

```bash
pisku stats
# → Total tokens saved: 12,400
```

---

## Comandos

### Comandos FREE

| Comando | Descripción |
|---------|-------------|
| `pisku init <proyecto>` | Menú interactivo para armar el contexto |
| `pisku list` | Listar skills disponibles |
| `pisku list --category <cat>` | Filtrar por: `backend`, `frontend`, `web3`, `devops` |
| `pisku add-skill <nombre>` | Agregar nueva skill |
| `pisku build-context <proyecto>` | Armar contexto sin menú interactivo |
| `pisku stats` | Ver tokens ahorrados (total) |
| `pisku version` | Ver versión y tier actual |

### Comandos PRO ⚡

| Comando | Descripción |
|---------|-------------|
| `pisku stats --detailed` | Dashboard completo con breakdown por proyecto |
| `pisku stats --csv` | Exportar histórico como CSV |
| `pisku activate-pro <key>` | Activar licencia PRO |

**Ejemplo `build-context` sin menú:**

```bash
pisku build-context mi-api --skills python-fastapi,postgresql-sqlalchemy
```

---

## Modelo Freemium

### 🆓 FREE — $0 para siempre

| Feature | Límite |
|---------|--------|
| Skills | Hasta 10 |
| Proyectos activos | 1 a la vez |
| Stats | Total ahorrado (número simple) |
| Soporte | GitHub Issues |

### ⚡ PRO — $5/mes o $50/año

| Feature | Beneficio |
|---------|-----------|
| Skills | Ilimitadas |
| Proyectos activos | Ilimitados |
| Stats | Dashboard completo + export CSV |
| Token analytics | Desglose por proyecto y skill |
| Soporte | Priority (email) |
| Updates | Beta access |

### Activar PRO

```bash
pisku activate-pro PISKU-PRO-XXXX-XXXX
```

La key se valida online contra el servidor PISKU. Después de la primera validación, se cachea en `config/config.json` y funciona offline.

**Key de demo (30 días):**

```bash
pisku activate-pro PISKU-PRO-DEMO-1234
```

> Requiere tener el servidor corriendo localmente (ver [Servidor](#servidor)).

---

## Skills incluidas

PISKU viene con 5 skills pre-armadas para el stack Python / PostgreSQL / Solidity:

| Skill | Categoría | Contenido |
|-------|-----------|-----------|
| `python-fastapi` | backend | Estructura de proyecto, patrones de rutas, DI, testing |
| `postgresql-sqlalchemy` | backend | ORM 2.0, migraciones Alembic, queries, performance |
| `supabase` | backend | CRUD, RLS, Edge Functions, Auth, Realtime |
| `solidity-base` | web3 | Contratos en Base Network, Hardhat, ethers.js v6, seguridad |
| `bootstrap5-dark` | frontend | Dark mode, glassmorphism, pricing tables, navbar |

### Estructura de una skill

Cada skill es un archivo `.md` en `skills/<categoria>/`:

```
skills/
├── backend/
│   ├── python-fastapi.md
│   ├── postgresql-sqlalchemy.md
│   └── supabase.md
├── frontend/
│   └── bootstrap5-dark.md
└── web3/
    └── solidity-base.md
```

Podés crear los tuyos con `pisku add-skill` o directamente creando el `.md` a mano.

---

## Servidor

El servidor FastAPI hace tres cosas: valida licencias PRO, procesa pagos Stripe, y sirve la landing page.

### Setup local

```bash
# 1. Instalar dependencias del servidor
pip install -r server/requirements.txt

# 2. Copiar el archivo de entorno
cp .env.example .env

# 3. Completar .env con tus keys (ver sección Stripe)

# 4. Levantar
python run_server.py
```

El servidor queda en `http://localhost:8000`.

- **Landing:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/api/docs`
- **Health:** `http://localhost:8000/api/health`

### Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/licenses/validate` | Validar license key (lo llama el CLI) |
| `POST` | `/api/payments/checkout` | Crear sesión de Stripe Checkout |
| `POST` | `/api/payments/webhook` | Webhook de Stripe (pago completado) |
| `GET`  | `/api/payments/success` | Obtener license key post-pago |
| `GET`  | `/api/health` | Health check |

---

## Integración Stripe

### 1. Crear cuenta en Stripe

Ir a [stripe.com](https://stripe.com) y crear una cuenta. No hace falta tarjeta ni datos de empresa para test mode.

### 2. Obtener las API keys

En el dashboard de Stripe, ir a **Developers → API keys**. Copiar:
- `Publishable key` (empieza con `pk_test_...`) — no la usamos en el servidor
- `Secret key` (empieza con `sk_test_...`) — va en el `.env`

### 3. Crear los productos y precios

En **Products → Add product**:

**Producto:** PISKU PRO  
Crear dos precios:
- Mensual: $5 USD, recurrente, cada mes → copiar el `price_ID` (empieza con `price_...`)
- Anual: $50 USD, recurrente, cada año → copiar el `price_ID`

Pegar ambos IDs en el `.env`.

### 4. Configurar el webhook

En **Developers → Webhooks → Add endpoint**:
- URL: `https://tu-dominio.com/api/payments/webhook`
- Eventos a escuchar: `checkout.session.completed`, `customer.subscription.deleted`
- Copiar el `Signing secret` (empieza con `whsec_...`) → va en `.env`

**Para testing local con Stripe CLI:**

```bash
# Instalar Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/api/payments/webhook
```

### 5. Completar el .env

```env
STRIPE_SECRET_KEY=sk_test_TU_KEY_REAL
STRIPE_WEBHOOK_SECRET=whsec_TU_WEBHOOK_SECRET
STRIPE_PRO_MONTHLY_PRICE_ID=price_TU_PRICE_MENSUAL
STRIPE_PRO_YEARLY_PRICE_ID=price_TU_PRICE_ANUAL
```

### Flujo completo de una compra

```
Usuario → Landing → click "Activar PRO"
  → Modal pide email
  → POST /api/payments/checkout
  → Redirige a Stripe Checkout (página oficial de Stripe)
  → Usuario paga con tarjeta de test: 4242 4242 4242 4242
  → Stripe llama POST /api/payments/webhook
  → Servidor genera key: PISKU-PRO-XXXX-XXXX
  → Redirige a /success.html?session_id=...
  → Usuario copia la key
  → pisku activate-pro PISKU-PRO-XXXX-XXXX
  → ⚡ PRO activado
```

**Tarjeta de prueba Stripe:** `4242 4242 4242 4242` · cualquier fecha futura · cualquier CVC.

---

## Deploy en producción

### Opción recomendada: Railway

```bash
# 1. Crear proyecto en railway.app
# 2. Conectar repo de GitHub
# 3. Configurar variables de entorno (las mismas del .env)
# 4. Railway detecta el Procfile o podés configurar el start command:
#    uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

### Procfile (para Railway / Heroku)

```
web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

### Variables de entorno en producción

Las mismas que en `.env`, más:
```env
ENV=production
SUCCESS_URL=https://tu-dominio.com/success.html
CANCEL_URL=https://tu-dominio.com/#pricing
CORS_ORIGINS=["https://tu-dominio.com"]
```

Una vez en producción, actualizá la URL del servidor en el CLI:

```bash
# En config/config.json cambiar:
# "server_url": "https://tu-dominio.com"
```

---

## Estructura del proyecto

```
pisku-cli/
├── cli/
│   ├── main.py              # Typer: todos los comandos
│   ├── skills_manager.py    # CRUD + menú interactivo
│   ├── context_builder.py   # Ensambla el .md final
│   ├── token_calculator.py  # Estimación de ahorro
│   ├── license_manager.py   # Validación online + caché
│   └── stats_tracker.py     # FREE stats / PRO dashboard
├── server/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings desde .env
│   ├── db.py                # JSON store de licencias
│   └── routers/
│       ├── licenses.py      # POST /api/licenses/validate
│       ├── payments.py      # Stripe checkout + webhook
│       └── health.py        # GET /api/health
├── skills/
│   ├── backend/             # python-fastapi, postgresql, supabase
│   ├── frontend/            # bootstrap5-dark
│   └── web3/                # solidity-base
├── landing/
│   ├── index.html           # Landing page completa
│   └── success.html         # Post-pago: muestra license key
├── config/
│   ├── config.json          # User settings + tier + license
│   └── licenses.json        # (auto-generado) Store de keys
├── docs/
│   └── contexts/            # Contextos generados por pisku init
├── .env.example             # Template de variables de entorno
├── run_server.py            # python run_server.py para dev
├── pyproject.toml           # pip install -e . / pip install pisku
├── requirements.txt         # CLI deps
└── server/requirements.txt  # Server deps
```

---

## License

MIT — hacé lo que quieras con esto.
