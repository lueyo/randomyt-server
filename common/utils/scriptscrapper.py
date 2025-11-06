import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Optional, Tuple

def _safe_int_convert(value) -> Optional[int]:
    """Convierte en int si el valor es convertible, sino devuelve None."""
    try:
        if value is None:
            return None
        # A veces viene como dict, lista, etc. Aseguramos string primero.
        s = str(value).strip()
        if s == "":
            return None
        return int(s)
    except (ValueError, TypeError):
        return None

def _safe_parse_date(value) -> Optional[datetime]:
    """Intenta parsear ISO date o RFC; devuelve None si no puede."""
    if not value:
        return None
    # Intentos simples
    try:
        # formato ISO esperado "YYYY-MM-DD" o "YYYY-MM-DDTHH:MM:SSZ"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        pass
    # Como fallback, intentar parseos básicos (sin dependencia externa)
    try:
        # intentar solo fecha YYYY-MM-DD
        return datetime.strptime(value.split("T")[0], "%Y-%m-%d")
    except Exception:
        return None

def _is_list_like(x):
    return isinstance(x, (list, tuple))

def obtener_datos_youtube(video_id: str):
    """
    Intenta múltiples métodos en orden:
      1) Scraping directo de la página (ytInitialPlayerResponse)
      2) noembed.com
      3) YouTube oEmbed
      4) yt.lemnoslife (API no oficial que replica Data API)
    Devuelve tan pronto encuentre un método que proporcione explícitamente:
      - title (string)
      - upload date (parseable a datetime)
      - viewCount (convertible a int, puede ser 0)
      - tags: si la fuente tiene 'tags' lo aceptamos (puede ser lista vacía)
    Si ningún método proporciona todos los campos, devuelve valores por defecto.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    timeout = 10

    # Helper que normaliza y decide si el resultado es "completo"
    def build_and_check(title, fecha_val, tags_val, views_val,
                        provided_title: bool, provided_date: bool,
                        provided_tags: bool, provided_views: bool):
        """
        Si provided_* indica que el método entregó explícitamente ese campo.
        Solo consideramos éxito si provided_title, provided_date y provided_views son True,
        y provided_tags True o False (las tags pueden ser lista vacía, PERO tienen que haber sido provistas explícitamente).
        """
        if not provided_title or not provided_date or not provided_views:
            return None  # no es completo: seguir probando otras fuentes

        # Normalizar tipos (fecha ya parseada, views int o None)
        fecha = fecha_val  # datetime
        tags = tags_val if provided_tags else []  # si no vinieron tags, dejar lista vacía pero no aceptar como informado
        views = views_val if views_val is not None else 0

        return {
            "titulo": title if title is not None else "Desconocido",
            "fecha_subida": fecha,
            "tags": tags,
            "views": views,
        }

    # ---------------------------
    # MÉTODO 1: SCRAPING DIRECTO
    # ---------------------------
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            scripts = soup.find_all("script")
            yt_data = None
            for script in scripts:
                txt = script.string or script.text or ""
                if "var ytInitialPlayerResponse" in txt:
                    try:
                        json_text = txt.split("var ytInitialPlayerResponse =")[-1].split("};")[0] + "}"
                        yt_data = json.loads(json_text)
                        break
                    except Exception:
                        continue

            if yt_data:
                video_details = yt_data.get("videoDetails", {})
                microformat = yt_data.get("microformat", {}).get("playerMicroformatRenderer", {})

                # Comprobamos si las claves existen (para saber si la fuente *proporcionó* el campo)
                provided_title = "title" in video_details
                provided_views = "viewCount" in video_details
                provided_tags = "keywords" in video_details
                provided_date = "uploadDate" in microformat

                title = video_details.get("title") if provided_title else None
                views = _safe_int_convert(video_details.get("viewCount")) if provided_views else None
                tags = video_details.get("keywords") if provided_tags else None
                date_dt = _safe_parse_date(microformat.get("uploadDate")) if provided_date else None

                resultado = build_and_check(title, date_dt, tags, views,
                                            provided_title, provided_date, provided_tags, provided_views)
                if resultado:
                    return resultado
    except Exception:
        # no hacemos nada: seguimos a la siguiente fuente
        pass

    # ---------------------------
    # MÉTODO 2: noembed.com
    # ---------------------------
    try:
        resp = requests.get(f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            # noembed suele dar 'title' pero no fecha ni views ni tags.
            provided_title = "title" in data
            provided_date = False
            provided_tags = False
            provided_views = False

            title = data.get("title") if provided_title else None
            date_dt = None
            tags = None
            views = None

            resultado = build_and_check(title, date_dt, tags, views,
                                        provided_title, provided_date, provided_tags, provided_views)
            if resultado:
                return resultado
            # como noembed no da fecha ni views, no será completo, seguimos
    except Exception:
        pass

    # ---------------------------
    # MÉTODO 3: YouTube oEmbed
    # ---------------------------
    try:
        resp = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            # oEmbed oficial también suele dar título, pero no fecha ni views ni tags.
            provided_title = "title" in data
            provided_date = False
            provided_tags = False
            provided_views = False

            title = data.get("title") if provided_title else None
            date_dt = None
            tags = None
            views = None

            resultado = build_and_check(title, date_dt, tags, views,
                                        provided_title, provided_date, provided_tags, provided_views)
            if resultado:
                return resultado
    except Exception:
        pass

    # ---------------------------
    # MÉTODO 4: yt.lemnoslife (API no oficial)
    # ---------------------------
    try:
        resp = requests.get(f"https://yt.lemnoslife.com/videos?part=snippet,statistics&id={video_id}", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                provided_title = "title" in snippet
                provided_date = "publishedAt" in snippet
                provided_tags = "tags" in snippet
                provided_views = "viewCount" in stats

                title = snippet.get("title") if provided_title else None
                date_dt = _safe_parse_date(snippet.get("publishedAt")) if provided_date else None
                tags = snippet.get("tags") if provided_tags else None
                views = _safe_int_convert(stats.get("viewCount")) if provided_views else None

                resultado = build_and_check(title, date_dt, tags, views,
                                            provided_title, provided_date, provided_tags, provided_views)
                if resultado:
                    return resultado
    except Exception:
        pass

    # ---------------------------
    # Si llegamos aquí, NINGÚN método devolvió todos los campos requeridos.
    # Devolvemos valores por defecto seguros (solo en este punto).
    # ---------------------------
    return {
        "titulo": "Desconocido",
        "fecha_subida": datetime.utcnow(),
        "tags": [],
        "views": 0,
    }


# Ejemplo de uso
if __name__ == "__main__":
    video_id = "dQw4w9WgXcQ"
    datos = obtener_datos_youtube(video_id)
    print(datos)
