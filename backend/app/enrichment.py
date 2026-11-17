"""Enriquecimiento de enlaces de Amazon.

Intenta obtener nombre e imagen de un producto de Amazon sin credenciales:
extrae el ASIN del enlace y lee las etiquetas Open Graph de la página.

Es "best-effort": si Amazon bloquea el pedido, se devuelve vacío y el usuario
completa los datos a mano. Si en el futuro se obtiene acceso a la Creators API
de Amazon, este módulo se reemplaza por GetItems sin cambiar el resto de la app.
"""

import logging
import re
from html.parser import HTMLParser

import httpx

logger = logging.getLogger("amigosecreto.enrichment")

# Patrones comunes de enlaces de producto: /dp/ASIN, /gp/product/ASIN
_ASIN_RE = re.compile(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})", re.IGNORECASE)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.5",
}


def extract_asin(url: str) -> str:
    """Extrae el ASIN de un enlace de Amazon ('' si no se encuentra)."""
    m = _ASIN_RE.search(url)
    return m.group(1).upper() if m else ""


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
        if prop in ("og:title", "og:image", "twitter:title", "twitter:image", "title"):
            content = d.get("content", "")
            if content and prop not in self.props:
                self.props[prop] = content


def _clean_title(raw: str) -> str:
    # Los títulos de Amazon suelen ser larguísimos: recortar un poco.
    title = raw.strip()
    for sep in (" - ", " | ", " : "):
        if sep in title and len(title) > 90:
            title = title.split(sep)[0]
            break
    return title[:255]


def fetch_product_info(url: str, timeout: float = 8.0) -> dict:
    """Devuelve {'name', 'image_url', 'asin'}; campos vacíos si no se pudo."""
    result = {"name": "", "image_url": "", "asin": extract_asin(url)}
    if "amazon." not in url:
        return result

    try:
        response = httpx.get(url, headers=_HEADERS, timeout=timeout, follow_redirects=True)
        if response.status_code != 200 or len(response.text) < 500:
            logger.info("Amazon devolvió %s para %s", response.status_code, url)
            return result
    except httpx.HTTPError as exc:
        logger.info("No se pudo obtener la página de Amazon: %s", exc)
        return result

    parser = _MetaParser()
    try:
        parser.feed(response.text[:200_000])  # las meta etiquetas están al inicio
    except Exception:  # HTML malformado: no es fatal
        pass

    if title := parser.props.get("og:title") or parser.props.get("twitter:title"):
        result["name"] = _clean_title(title)
    result["image_url"] = parser.props.get("og:image") or parser.props.get("twitter:image", "")
    return result
