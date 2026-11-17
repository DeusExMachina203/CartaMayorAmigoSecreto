#!/usr/bin/env bash
# Levanta backend + frontend y los expone en internet con un túnel efímero
# de Cloudflare (trycloudflare.com). La URL se muestra al arrancar.
#
# Uso: ./tunel.sh        (Ctrl+C o SIGTERM detiene todo)
#      ./tunel.sh stop   (detiene una instancia ya corriendo)
set -uo pipefail
cd "$(dirname "$0")"

PIDFILE=/tmp/opencode/amigo-secreto-tunel.pid
LOG=/tmp/opencode/amigo-secreto-tunel.log

verde='\033[0;32m'
amarillo='\033[0;33m'
rojo='\033[0;31m'
sin='\033[0m'

if [ "${1:-}" = "stop" ]; then
  if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Deteniendo túnel y servidores..."
    sleep 1
    echo "Listo."
  else
    echo "No hay instancia corriendo (o no se pudo detener)."
  fi
  exit 0
fi

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo -e "${rojo}Ya hay un túnel corriendo (PID $(cat "$PIDFILE")). Usa ./tunel.sh stop primero.${sin}"
  exit 1
fi
echo $$ > "$PIDFILE"

if [ ! -x backend/.venv/bin/uvicorn ]; then
  echo -e "${rojo}Falta el entorno del backend. Ejecuta primero:${sin}"
  echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
if [ ! -d frontend/node_modules ]; then
  echo -e "${rojo}Faltan dependencias del frontend. Ejecuta primero:${sin}"
  echo "  cd frontend && npm install"
  exit 1
fi
if ! command -v cloudflared >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/cloudflared" ]; then
    PATH="$HOME/.local/bin:$PATH"
  else
    echo -e "${rojo}No está cloudflared. Instálalo o descárgalo a ~/.local/bin/${sin}"
    exit 1
  fi
fi

TUNNEL_LOG=/tmp/opencode/cloudflared.log
mkdir -p "$(dirname "$TUNNEL_LOG")"

# Al salir (Ctrl+C o SIGTERM), matar backend, frontend y túnel
limpiar() {
  echo
  echo -e "${verde}Deteniendo servidores y túnel...${sin}"
  local pid
  for pid in $(jobs -p); do
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  rm -f "$PIDFILE"
}
trap limpiar EXIT INT TERM

echo -e "${verde}🎁 API:      http://localhost:8000  (recarga automática, docs en /docs)${sin}"
echo -e "${verde}🎄 Frontend: http://localhost:4321  (HMR)${sin}"
echo -e "${amarillo}🌍 Solicitando URL pública de Cloudflare...${sin}"

# Túnel efímero hacia el frontend (que a su vez hace proxy de /api al backend)
cloudflared tunnel --url http://localhost:4321 --no-autoupdate > "$TUNNEL_LOG" 2>&1 &

# Esperar a que aparezca la URL en el log del túnel
URL=""
for _ in $(seq 1 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)
  [ -n "$URL" ] && break
  sleep 1
done

if [ -n "$URL" ]; then
  echo
  echo -e "${verde}🌍 Enlace público (compártelo solo con quien quieras):${sin}"
  echo -e "${verde}    $URL${sin}"
  echo -e "${verde}    Panel admin: $URL/admin${sin}"
  echo
else
  echo -e "${rojo}No se obtuvo URL pública tras 30s. Revisa $TUNNEL_LOG${sin}"
fi

# exec: el subshell se convierte en el servidor, así el PID de jobs -p es el
# del servidor mismo y ninguna capa intermedia sobrevive al apagado.
(cd backend && exec .venv/bin/uvicorn app.main:app --reload --port 8000) &
(cd frontend && exec npm run dev -- --host 127.0.0.1) &

wait
