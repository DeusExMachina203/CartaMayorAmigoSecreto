#!/usr/bin/env bash
# Levanta el backend (FastAPI) y el frontend (Astro) juntos para desarrollo.
# Ctrl+C detiene los dos. Uso: ./dev.sh
set -euo pipefail
cd "$(dirname "$0")"

verde='\033[0;32m'
rojo='\033[0;31m'
sin='\033[0m'

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

# Al salir (Ctrl+C incluido), matar backend y frontend y todo lo que hayan
# creado (npm -> astro, uvicorn --reload -> reloader hijo).
limpiar() {
  echo
  echo -e "${verde}Deteniendo servidores... ¡hasta la próxima! 🎁${sin}"
  local pid
  for pid in $(jobs -p); do
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill -TERM "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap limpiar EXIT INT TERM

echo -e "${verde}🎄 Frontend: http://localhost:4321${sin}"
echo -e "${verde}🎁 API:      http://localhost:8000  (docs: /docs)${sin}"
echo

# exec: el subshell se convierte en el servidor, así el PID de jobs -p es el
# del servidor mismo y ninguna capa intermedia sobrevive al apagado.
(cd backend && exec .venv/bin/uvicorn app.main:app --reload --port 8000) &
(cd frontend && exec npm run dev) &

wait
