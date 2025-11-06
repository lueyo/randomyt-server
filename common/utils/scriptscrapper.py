import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def obtener_datos_youtube(video_id):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # --- MÉTODO 1: SCRAPING DIRECTO ---
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            scripts = soup.find_all("script")
            yt_data = None

            for script in scripts:
                if "var ytInitialPlayerResponse" in script.text:
                    try:
                        json_text = (
                            script.text.split("var ytInitialPlayerResponse =")[-1]
                            .split("};")[0]
                            + "}"
                        )
                        yt_data = json.loads(json_text)
                        break
                    except Exception:
                        continue

            if yt_data:
                video_details = yt_data.get("videoDetails", {})
                microformat = yt_data.get("microformat", {}).get("playerMicroformatRenderer", {})

                titulo = video_details.get("title", "Desconocido")
                fecha_str = microformat.get("uploadDate", None)
                etiquetas = video_details.get("keywords", [])
                vistas = int(video_details.get("viewCount", 0))

                try:
                    fecha_subida = datetime.fromisoformat(fecha_str.replace("Z", "+00:00")) if fecha_str else datetime.utcnow()
                except Exception:
                    fecha_subida = datetime.utcnow()

                return {
                    "titulo": titulo,
                    "fecha_subida": fecha_subida,
                    "tags": etiquetas,
                    "views": vistas,
                }
    except Exception:
        pass  # Si falla, pasamos al siguiente método

    # --- MÉTODO 2: noembed.com (API pública) ---
    try:
        resp = requests.get(f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            titulo = data.get("title", "Desconocido")
            fecha_subida = datetime.utcnow()  # No lo provee
            etiquetas = []
            vistas = 0
            return {
                "titulo": titulo,
                "fecha_subida": fecha_subida,
                "tags": etiquetas,
                "views": vistas,
            }
    except Exception:
        pass

    # --- MÉTODO 3: oEmbed oficial de YouTube ---
    try:
        resp = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            titulo = data.get("title", "Desconocido")
            fecha_subida = datetime.utcnow()
            etiquetas = []
            vistas = 0
            return {
                "titulo": titulo,
                "fecha_subida": fecha_subida,
                "tags": etiquetas,
                "views": vistas,
            }
    except Exception:
        pass

    # --- MÉTODO 4: API alternativa yt.lemnoslife ---
    try:
        resp = requests.get(f"https://yt.lemnoslife.com/videos?part=snippet,statistics&id={video_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                titulo = snippet.get("title", "Desconocido")
                fecha_str = snippet.get("publishedAt", None)
                etiquetas = snippet.get("tags", [])
                vistas = int(stats.get("viewCount", 0))
                try:
                    fecha_subida = datetime.fromisoformat(fecha_str.replace("Z", "+00:00")) if fecha_str else datetime.utcnow()
                except Exception:
                    fecha_subida = datetime.utcnow()
                return {
                    "titulo": titulo,
                    "fecha_subida": fecha_subida,
                    "tags": etiquetas,
                    "views": vistas,
                }
    except Exception:
        pass

    # Si todo falla
    raise Exception("No se pudo obtener la información del video por ningún método.")


# Ejemplo de uso
if __name__ == "__main__":
    video_id = "dQw4w9WgXcQ"
    datos = obtener_datos_youtube(video_id)
    print(datos)
