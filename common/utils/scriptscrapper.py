import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def obtener_datos_youtube(video_id):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def safe_int(value, default=0):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def safe_date(value):
        try:
            if value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
        return None

    # --- MÉTODO 1: SCRAPING DIRECTO (original) ---
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

                titulo = video_details.get("title")
                fecha_subida = safe_date(microformat.get("uploadDate"))
                etiquetas = video_details.get("keywords")
                vistas = safe_int(video_details.get("viewCount"))

                if titulo and fecha_subida and vistas:
                    return {
                        "titulo": titulo,
                        "fecha_subida": fecha_subida,
                        "tags": etiquetas or [],
                        "views": vistas,
                    }
    except Exception:
        pass

    # --- MÉTODO 2: Mattw YouTube API (https://ytapi.apps.mattw.io) ---
    try:
        api_url = (
            f"https://ytapi.apps.mattw.io/v3/videos"
            f"?key=foo1"
            f"&quotaUser=ezb2mV0zCUgcJoUiwI6V2qTarCG3uBXX1GBofjgM"
            f"&part=snippet,statistics"
            f"&id={video_id}"
        )
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                titulo = snippet.get("title")
                fecha_subida = safe_date(snippet.get("publishedAt"))
                etiquetas = snippet.get("tags") or []
                vistas = safe_int(stats.get("viewCount"))

                if titulo and fecha_subida and vistas is not None:
                    return {
                        "titulo": titulo,
                        "fecha_subida": fecha_subida,
                        "tags": etiquetas,
                        "views": vistas,
                    }
    except Exception:
        pass

    # --- MÉTODO 3: noembed.com ---
    try:
        resp = requests.get(f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "title" in data:
                return {
                    "titulo": data["title"],
                    "fecha_subida": datetime.utcnow(),
                    "tags": [],
                    "views": 0,
                }
    except Exception:
        pass

    # --- MÉTODO 4: oEmbed oficial ---
    try:
        resp = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "title" in data:
                return {
                    "titulo": data["title"],
                    "fecha_subida": datetime.utcnow(),
                    "tags": [],
                    "views": 0,
                }
    except Exception:
        pass

    # --- MÉTODO 5: yt.lemnoslife ---
    try:
        resp = requests.get(f"https://yt.lemnoslife.com/videos?part=snippet,statistics&id={video_id}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                item = items[0]
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                titulo = snippet.get("title")
                fecha_subida = safe_date(snippet.get("publishedAt"))
                etiquetas = snippet.get("tags") or []
                vistas = safe_int(stats.get("viewCount"))

                if titulo and fecha_subida and vistas is not None:
                    return {
                        "titulo": titulo,
                        "fecha_subida": fecha_subida,
                        "tags": etiquetas,
                        "views": vistas,
                    }
    except Exception:
        

    # --- FALLBACK FINAL: da error ---
        raise ValueError("No se pudieron obtener los datos del video de YouTube.")
    
    


# Ejemplo de uso
if __name__ == "__main__":
    video_id = "jNQXAC9IVRw"
    datos = obtener_datos_youtube(video_id)
    print(datos)
