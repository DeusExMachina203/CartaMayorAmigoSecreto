# Amigo Secreto 🎁

Organizador de intercambio de regalos para el grupo. Backend en FastAPI,
frontend en Astro. Todo en español.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# (opcional) configurar SMTP de Proton; sin .env los códigos van a la consola
cp .env.example .env  # y editar

.venv/bin/uvicorn app.main:app --reload
```

- Documentación interactiva: http://localhost:8000/docs
- Salud: http://localhost:8000/api/salud
- Contraseña admin por defecto en dev: `admin-dev` (variable `ADMIN_PASSWORD`)

### Probar el flujo completo (backend)

```bash
cd backend
.venv/bin/python scripts/smoke_test.py
```

Crea 3 participantes de ejemplo, entra con códigos, edita listas de deseos,
hace el sorteo y valida que nadie se regale a sí mismo.

## Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:4321
```

Páginas: `/` (inicio), `/ingresar` (login por código), `/mi-lista`,
`/mi-amigo`, `/participantes`, `/admin`.

La URL de la API se configura con `PUBLIC_API_URL` (por defecto
`http://localhost:8000`). Para producción se sirve el build estático
(`npm run build`) y se pone la API bajo el mismo dominio.

## Estructura

```
backend/
├── app/
│   ├── main.py          # App FastAPI y montaje de routers
│   ├── config.py        # Configuración por .env (pydantic-settings)
│   ├── database.py      # SQLite + SQLAlchemy (WAL)
│   ├── models.py        # Player, LoginCode, WishlistItem, Assignment, Setting
│   ├── schemas.py       # Esquemas Pydantic
│   ├── security.py      # JWT en cookie, códigos hasheados, dependencias
│   ├── emailer.py       # Envío del código (SMTP Proton o consola en dev)
│   ├── draw.py          # Sorteo tipo derangement
│   ├── enrichment.py    # ASIN + og-tags de Amazon (best-effort, reemplazable)
│   └── routers/
│       ├── auth.py          # solicitar-codigo / verificar / salir / yo
│       ├── wishlist.py      # CRUD de mi lista + enriquecer enlace
│       ├── participants.py  # lista pública + presupuesto/fecha
│       ├── me.py            # mi amigo asignado (post-sorteo)
│       └── admin.py         # gestión de participantes, config y sorteo
├── scripts/smoke_test.py
frontend/
├── src/
│   ├── layouts/Layout.astro   # estilos globales y navegación
│   ├── lib/api.js             # cliente de la API (cookies incluidas)
│   └── pages/                 # index, ingresar, mi-lista, mi-amigo,
│                              # participantes, admin
└── astro.config.mjs
```

## Flujo

1. El admin registra a cada amigo (correo + nombre) en el panel `/admin`.
2. Cada amigo entra, pone su correo y recibe un código de 6 dígitos por correo.
3. Con el código obtiene sesión (cookie JWT) y arma su lista de deseos.
4. El admin fija presupuesto/fecha y lanza el sorteo: nadie se regala a sí mismo.
5. Cada quien ve solo a quién le regala, con la lista de esa persona.

