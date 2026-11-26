# Guía para agentes (AGENTS.md)

Documento de contexto para agentes de código que trabajen en este proyecto.
Léelo completo antes de hacer cambios.

## Qué es

**CartaMayorAmigoSecreto** — sitio privado para organizar un Amigo Secreto
entre un grupo de amigos peruanos. Todo el contenido visible está **en español**.

- **Backend:** FastAPI + SQLite (SQLAlchemy 2.0) en `backend/`
- **Frontend:** Astro estático con JS vanilla, en `frontend/`
- **Repo:** https://github.com/DeusExMachina203/CartaMayorAmigoSecreto (rama `main`)

## Estado actual (nov 2026)

Funciona y está probado de punta a punta:

- ✅ Auth por código de 6 dígitos enviado por correo (sin contraseñas), JWT en cookie HttpOnly
- ✅ Auto-registro con **enlace de invitación** (`/ingresar?inv=CODIGO`): los amigos se registran solos con nombre + correo; NO hay botón "Ingresar" en la UI (decisión del usuario: la entrada es solo por el enlace de invitación)
- ✅ Wishlist CRUD + vista previa de imagen + **subida de imágenes desde el dispositivo** (blobs en la BD, límite 50 MB, servidas por `/api/imagenes/{id}`)
- ✅ **Sorteo individual por clic** (`POST /api/sortear`): con el primer clic de cualquier participante se genera en secreto un derangement completo (nadie se auto-regala, ningún receptor se repite); cada clic solo REVELA la asignación ya creada (`assignments.revealed_at`). `GET /api/mi-amigo` da 404 hasta que el participante haya tocado "Realizar mi sorteo". El admin puede pre-generar o deshacer/rehacer desde el panel.
- ✅ Panel admin (contraseña en `ADMIN_PASSWORD`): participantes, presupuesto, fecha, sorteo, enlace de invitación
- ✅ Emails reales vía SMTP de Proton (configurado en `backend/.env`, ver abajo)
- ✅ Rediseño con el mockup del usuario (PSD en capas): sidebar verde, fondo beige `#CAC1A5`, Playfair Display + Jost. El muñeco de nieve fue reemplazado por **Adrian** (foto real del amigo en `~/Pictures/friends/adrianhe.jpg`, editada con IA: gorro de Santa + integración en el trineo; original con permiso del grupo)

## Cómo correr

```bash
# La primera vez:
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd ../frontend && npm install

# Desarrollo (backend + frontend juntos, con recarga automática):
./dev.sh            # solo local
./tunel.sh          # + URL pública efímera de Cloudflare (trycloudflare.com)
./tunel.sh stop     # detener

# Pruebas:
cd backend && .venv/bin/python scripts/smoke_test.py       # flujo completo (usa su propia BD: data/smoke.db)
.venv/bin/python scripts/prueba_correo.py TU@CORREO.com    # prueba SMTP real
```

**Importante:** solo una instancia a la vez. Si el usuario corre `dev.sh`/`tunel.sh`
en SU terminal, NO mates ni inicies procesos del servidor sin preguntar
(los puertos 8000/4321 chocan y las instancias pelean). El URL del túnel cambia en cada arranque.

## Credenciales y secretos

- `backend/.env` tiene la config real (SMTP de Proton incluida) y va **gitignored** — NUNCA subir secretos.
  - SMTP: `smtp.protonmail.ch:587` STARTTLS, token de `dex@ernestodeloayza.com` (revocable desde Ajustes → IMAP/SMTP → Tokens SMTP en Proton)
  - Sin `.env`, los códigos de acceso se imprimen en la consola del servidor (modo dev)
- Admin password de dev: `admin-dev`
- Commits hechos con identidad `dex <dex@local>`; la cuenta de GitHub es `DeusExMachina203` (gh CLI autenticado)

## Decisiones de diseño (no revertir sin consultar)

1. **SQLite** es suficiente (grupo de amigos, escrituras ocasionales). WAL activado. Fechas **naive UTC** en la BD (SQLite mezcla aware/naive mal).
2. **Registro solo por enlace de invitación**: el código vive en la tabla `settings` (1 fila, id=1), regenerable desde el panel admin. Bloquea registro tras el sorteo.
3. **Sin botón "Ingresar"** en la UI: el mismo enlace de invitación sirve para registrarse y para volver a entrar.
4. **Imágenes como blobs** en la tabla `imagenes`; la URL devuelta se guarda en `wishlist_items.image_url` (así preview/tarjetas/"mi amigo" no distinguen entre URL externa o blob). Las imágenes de blobs son públicas si se conoce el ID (aceptado por ahora).
5. **Enriquecimiento de enlaces** (`backend/app/enrichment.py`): og-tags de la página del producto, funciona con **cualquier tienda sin anti-bot** (Falabella ✅ probado, Paris, Sodimac...). NO intentar rodear el muro de bots de Amazon: el usuario lo prohibió explícitamente. Amazon queda manual hasta tener credenciales oficiales.

## Pendientes (siguiente trabajo, en orden)

1. **Despliegue al VPS** — IP `82.165.214.172`, usuario `dex`:
   - El usuario DEBE correr primero `ssh-copy-id -i ~/.ssh/amigo_secreto dex@82.165.214.172` (la llave privada ya existe en este equipo). Sin esa llave no hay acceso: ssh interactivo con contraseña NO es posible desde el agente.
   - Plan: Docker Compose (Caddy para TLS + API + volumen SQLite), clonar desde GitHub, `.env` real en el VPS, dominio `ernestodeloayza.com` (o subdominio) vía Cloudflare → VPS.
   - El frontend llama a la API con rutas relativas (`/api/...`): detrás de Caddy debe convivir mismo dominio (proxy `/api` → uvicorn).
   - IMPORTANTE en producción: cookies `secure=True` en `backend/app/security.py` (ahora está en False para HTTP local) y cambiar `SECRET_KEY`/`ADMIN_PASSWORD`.
2. **AliExpress**: el usuario se registrará en el programa de afiliados (portal AliExpress, requiere aprobación de perfil). Cuando dé credenciales (`AE_APP_KEY`, `AE_APP_SECRET`), añadir `aliexpress.affiliate.productdetail.get` a `enrichment.py` (devuelve título+imagen+precio por ID de producto; IDs numéricos en las URLs de AliExpress). Sin requisito de ventas, a diferencia de Amazon.
3. **Amazon Creators API**: solo tras 10 ventas calificadas en 30 días vía enlaces de afiliado del sitio (el caso de uso del Amigo Secreto las genera naturalmente). Módulo `enrichment.py` ya está aislado para hacer el swap sin tocar el resto.
4. Limpieza de datos de prueba (`foto*@test.com`, smoke test deja Carlos/Diana/María) cuando el usuario lo pida.

## Gotchas aprendidos

- **Astro se come las barras invertidas en atributos**: `pattern="\d{6}"` llega al HTML como `d{6}`. Usar clases de caracteres: `pattern="[0-9]{6}"`.
- **pkill con -f puede matar el propio shell** del agente si el patrón coincide con el comando (usar corchetes: `pkill -f "astro [d]ev"`).
- El muro de bots de Amazon es **intermitente** (a veces pasa a la primera) — no por eso añadir reintentos en bucle: decisión del usuario.
- `playwright` está instalado en `frontend/node_modules` (con `--no-save`) para capturas de verificación visual: `npx playwright screenshot --viewport-size "390,844" URL archivo.png`. Si haces `npm install` limpio, desaparece.
- Los códigos de login tienen cooldown de 60 s solo si el anterior sigue sin usar (no bloquea reingresos con código usado).
- Tras el sorteo no se puede borrar participantes ni registrar nuevos (409) — deshacer el sorteo primero.
