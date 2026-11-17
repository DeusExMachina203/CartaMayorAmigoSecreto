"""Enriquecimiento de enlaces de tiendas online.

Extrae nombre e imagen de la página del producto usando sus etiquetas
Open Graph. Funciona bien con tiendas que no bloquean bots (Falabella,
Paris, Sodimac, etc.). Amazon sí bloquea de forma intermitente, así que
para Amazon esto es best-effort y el usuario completa a mano; cuando
tengamos credenciales de una API oficial (Creators API de Amazon o la
AE Affiliate API de AliExpress) se conectan aquí sin cambiar el resto.
"""

import logging
import re
from html.parser import HTMLParser

import httpx

logger = logging.getLogger("amigosecreto.enrichment")

# Patrones comunes de enlaces de producto de Amazon: /dp/ASIN, /gp/product/ASIN
_ASIN_RE = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})", re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.5",
}


def extract_asin(url: str) -> str:
    """Extrae el ASIN de un enlace de Amazon ('' si no es de Amazon)."""
    m = _ASIN_RE.search(url)
    return m.group(1).upper() if m else ""


def _limpiar_titulo(raw: str) -> str:
    """Quita colas de marca del título, p. ej. '| Falabella Perú'."""
    title = raw.strip()
    title = re.sub(r"\s*[|–]\s*Falabella.*$", "", title)
    title = re.sub(r"^Amazon\.[a-z.]+:\s*", "", title)
    title = re.sub(r"\s*\|\s*Mercado Libre.*$", "", title)
    return title[:255]


class _MetaParser(HTMLParser):
    """Parser mínimo que recolecta las meta etiquetas Open Graph."""

    def __init__(self) -> None:
        super().__init__()
        self.props: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        d = dict(attrs)
        prop = d.get("property") or d.get("name") or ""
        if prop in ("og:title", "og:image") and prop not in self.props:
            content = d.get("content", "")
            if content:
                self.props[prop] = content


def fetch_product_info(url: str, timeout: float = 10.0) -> dict:
    """Devuelve {'name', 'image_url', 'asin'}; campos vacíos si no se pudo.

    Best-effort: si la tienda bloquea o no tiene og-tags, se devuelve vacío
    y el usuario completa los campos a mano.
    """
    result = {"name": "", "image_url": "", "asin": extract_asin(url)}

    try:
        response = httpx.get(url, headers=_HEADERS, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError as exc:
        logger.info("No se pudo obtener la página: %s", exc)
        return result

    if response.status_code != 200 or len(response.text) < 500:
        logger.info("Respuesta inútil de la tienda (%s): %s", response.status_code, url)
        return result

    parser = _MetaParser()
    try:
        parser.feed(response.text[:500_000])
    except Exception:  # HTML malformado: no es fatal
        pass

    if title := parser.props.get("og:title"):
        result["name"] = _limpiar_titulo(title)
    result["image_url"] = parser.props.get("og:image", "")
    return result
