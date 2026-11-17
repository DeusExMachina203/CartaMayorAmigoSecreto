"""Prueba de humo de la API: recorre el flujo completo sin servidor real.

Uso: .venv/bin/python scripts/smoke_test.py
"""

import logging
import re

from fastapi.testclient import TestClient

from app.main import app
from app.models import Assignment

# Captura los códigos "enviados por correo" (modo consola del emailer)
codigos: dict[str, str] = {}


class CapturaCodigos(logging.Handler):
    def emit(self, record):
        m = re.search(r"([\w.]+@[^\s)]+).*?: (\d{6})", record.getMessage())
        if m:
            codigos[m.group(1)] = m.group(2)


logging.getLogger("amigosecreto.email").addHandler(CapturaCodigos())
logging.getLogger("amigosecreto.email").setLevel(logging.WARNING)

AMIGOS = [
    ("Diana Quispe", "diana@example.com"),
    ("Carlos Mendoza", "carlos@example.com"),
    ("María Torres", "maria@example.com"),
]


def pedir_y_verificar_codigo(client, email, codigo):
    r = client.post("/api/auth/verificar", json={"email": email, "code": codigo})
    assert r.status_code == 200, f"verificar: {r.status_code} {r.text}"
    return r.json()


def pedir_y_verificar_registro(client, email, nombre, invitacion):
    """Se registra con invitación, captura el código del log y entra."""
    r = client.post(
        "/api/auth/solicitar-codigo",
        json={"email": email, "name": nombre, "invite_code": invitacion},
    )
    assert r.status_code == 202, f"solicitar-codigo: {r.status_code} {r.text}"
    assert email in codigos, f"no se capturó código para {email}"
    return pedir_y_verificar_codigo(client, email, codigos[email])


def pedir_y_verificar(client, email):
    """Pide un código, lo captura del log y canjea el código por sesión."""
    r = client.post("/api/auth/solicitar-codigo", json={"email": email})
    assert r.status_code == 202, f"solicitar-codigo: {r.status_code} {r.text}"
    assert email in codigos, f"no se capturó código para {email}"
    return pedir_y_verificar_codigo(client, email, codigos[email])


def main():
    with TestClient(app) as c:
        print("== Salud ==", c.get("/api/salud").json())

        # ---- Admin ----
        r = c.post("/api/admin/login", json={"password": "mal"})
        assert r.status_code == 401, "contraseña incorrecta debió ser rechazada"
        r = c.post("/api/admin/login", json={"password": "admin-dev"})
        assert r.status_code == 200, r.text
        print("== Login admin OK ==")

        # ---- Participantes (creados por el admin, p. ej. para enviarles el código directo) ----
        for nombre, email in AMIGOS[:2]:
            r = c.post("/api/admin/participantes", json={"name": nombre, "email": email})
            assert r.status_code == 201, r.text
        r = c.post(
            "/api/admin/participantes", json={"name": "Dup", "email": "diana@example.com"}
        )
        assert r.status_code == 409, "correo duplicado debió dar 409"
        print("== 2 participantes creados por admin, duplicado rechazado ==")

        # ---- Auto-registro con código de invitación ----
        r = c.get("/api/admin/config")
        assert r.status_code == 200 and r.json()["invite_code"], r.text
        invitacion = r.json()["invite_code"]

        # Sin invitación no se puede registrar
        r = c.post("/api/auth/solicitar-codigo", json={"email": "maria@example.com"})
        assert r.status_code == 403, r.text
        # Invitación inválida tampoco
        r = c.post(
            "/api/auth/solicitar-codigo",
            json={"email": "maria@example.com", "name": "María", "invite_code": "malo"},
        )
        assert r.status_code == 403, r.text
        # Con invitación válida sí (y falta de nombre da 422)
        r = c.post(
            "/api/auth/solicitar-codigo",
            json={"email": "maria@example.com", "invite_code": invitacion},
        )
        assert r.status_code == 422, "falta el nombre, debió dar 422"
        maria = pedir_y_verificar_registro(
            c, "maria@example.com", "María Torres", invitacion
        )
        assert maria["name"] == "María Torres"
        print("== Auto-registro con invitación OK (inválida y sin nombre rechazadas) ==")

        # Regenerar la invitación invalida la anterior
        r = c.post("/api/admin/config/invitacion")
        nueva_invitacion = r.json()["invite_code"]
        assert nueva_invitacion != invitacion
        r = c.post(
            "/api/auth/solicitar-codigo",
            json={"email": "otro@example.com", "name": "X", "invite_code": invitacion},
        )
        assert r.status_code == 403, "la invitación vieja debió dejar de servir"
        print("== Regeneración de invitación OK ==")

        # ---- Config ----
        r = c.put(
            "/api/admin/config", json={"budget_min": 20, "budget_max": 50, "event_date": "2026-12-19"}
        )
        assert r.status_code == 200, r.text
        r = c.put("/api/admin/config", json={"budget_min": 90, "budget_max": 50, "event_date": ""})
        assert r.status_code == 422, "presupuesto invertido debió dar 422"
        print("== Config OK (S/ 20 - S/ 50, 2026-12-19) ==")

        # ---- Login de Diana con código ----
        diana = pedir_y_verificar(c, "diana@example.com")
        assert diana["name"] == "Diana Quispe"
        print("== Código de acceso verificado, sesión:", diana["name"], "==")

        # Código incorrecto (no consume el código real: solo suma un intento)
        c.post("/api/auth/salir")
        c.post("/api/auth/solicitar-codigo", json={"email": "carlos@example.com"})
        r = c.post(
            "/api/auth/verificar",
            json={"email": "carlos@example.com", "code": "000000"},
        )
        assert r.status_code == 401, "código erróneo debió dar 401"
        carlos = pedir_y_verificar_codigo(c, "carlos@example.com", codigos["carlos@example.com"])
        print("== Código erróneo rechazado; Carlos logueado ==")

        # ---- Lista de deseos ----
        r = c.post(
            "/api/mi-lista",
            json={
                "name": "Audífonos inalámbricos",
                "price_hint": "S/ 45",
                "amazon_url": "https://www.amazon.com/-/dp/B08N5WRWNW?th=1",
                "notes": "Color negro, sirve cualquier marca similar",
            },
        )
        assert r.status_code == 201, r.text
        item = r.json()
        assert item["asin"] == "B08N5WRWNW", item
        r = c.post("/api/mi-lista", json={"name": "Caja de chocotejas", "price_hint": "S/ 25"})
        assert r.status_code == 201, r.text
        lista = c.get("/api/mi-lista").json()
        assert len(lista) == 2, lista
        print(f"== Lista de Carlos: {len(lista)} regalos, ASIN extraído OK ==")

        # Editar y borrar
        r = c.patch(f"/api/mi-lista/{item['id']}", json={"name": "Audífonos negros", "notes": "", "price_hint": "", "image_url": "", "amazon_url": ""})
        assert r.status_code == 200 and r.json()["name"] == "Audífonos negros", r.text

        # Otro usuario no puede tocar la lista ajena
        c.post("/api/auth/salir")
        pedir_y_verificar(c, "diana@example.com")
        r = c.patch(f"/api/mi-lista/{item['id']}", json={"name": "hack", "notes": "", "price_hint": "", "image_url": "", "amazon_url": ""})
        assert r.status_code == 404, "editar lista ajena debió dar 404"
        r = c.get("/api/mi-amigo")
        assert r.status_code == 404, "mi-amigo antes del sorteo debió dar 404"
        print("== Aislamiento entre usuarios OK ==")

        # Enriquecimiento de enlace de Amazon (best-effort: puede fallar sin red)
        r = c.post("/api/mi-lista/enriquecer", json={"url": "https://www.amazon.com/dp/B08N5WRWNW"})
        assert r.status_code == 200, r.text
        print("== Enriquecer (og-tags):", r.json(), "==")

        # ---- Sorteo ----
        # Sin sesión de admin debe rechazar (quitamos la cookie primero)
        c.cookies.delete("admin_sesion")
        r = c.post("/api/admin/sorteo")
        assert r.status_code == 401, "sorteo sin admin debió dar 401"
        c.post("/api/admin/login", json={"password": "admin-dev"})
        r = c.post("/api/admin/sorteo")
        assert r.status_code == 200, r.text
        print("== Sorteo:", r.json(), "==")
        r = c.post("/api/admin/sorteo")
        assert r.status_code == 409, "sorteo doble debió dar 409"

        # Verificar derangement y unicidad en la BD
        from app.database import SessionLocal
        db = SessionLocal()
        asignaciones = db.query(Assignment).all()
        assert len(asignaciones) == 3
        assert all(a.giver_id != a.receiver_id for a in asignaciones), "alguien se regaló a sí mismo"
        assert len({a.giver_id for a in asignaciones}) == 3
        assert len({a.receiver_id for a in asignaciones}) == 3
        db.close()

        # Cada quien ve solo a su asignado
        for _, email in AMIGOS:
            c.post("/api/auth/salir")
            pedir_y_verificar(c, email)
            r = c.get("/api/mi-amigo")
            assert r.status_code == 200, r.text
            amigo = r.json()
            print(f"   {email} regala a -> {amigo['name']} ({len(amigo['wishlist'])} deseos)")

        # ---- Público ----
        part = c.get("/api/participantes").json()
        assert len(part) == 3 and all("email" not in p for p in part), part
        cfg = c.get("/api/participantes/config").json()
        assert cfg["budget_max"] == 50 and cfg["draw_done"] is True, cfg
        print("== Participantes públicos sin correos; config pública OK ==")

        # ---- Deshacer y rehacer ----
        r = c.delete("/api/admin/sorteo")
        assert r.status_code == 204, r.text
        r = c.post("/api/admin/sorteo")
        assert r.status_code == 200, "rehacer sorteo debió funcionar"
        print("== Deshacer/rehacer sorteo OK ==")

    print()
    print("✔ TODAS LAS PRUEBAS PASARON")


if __name__ == "__main__":
    main()
