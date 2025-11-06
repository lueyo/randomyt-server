import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime


def obtener_datos_youtube(id):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://www.youtube.com/watch?v={id}"
    # Descargar HTML del video
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error al acceder a la página: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Buscar el bloque de datos en el script
    scripts = soup.find_all("script")
    yt_data = None

    for script in scripts:
        if "var ytInitialPlayerResponse" in script.text:
            try:
                json_text = (
                    script.text.split("var ytInitialPlayerResponse =")[-1].split("};")[
                        0
                    ]
                    + "}"
                )
                yt_data = json.loads(json_text)
                break
            except Exception:
                continue

    if not yt_data:
        raise Exception("No se pudo encontrar la información del video.")

    # Extraer información del JSON
    video_details = yt_data.get("videoDetails", {})
    microformat = yt_data.get("microformat", {}).get("playerMicroformatRenderer", {})

    titulo = video_details.get("title", "Desconocido")
    fecha_str = microformat.get("uploadDate", "Desconocida")
    etiquetas = video_details.get("keywords", [])
    vistas = int(video_details.get("viewCount", 0))

    # Parse fecha_subida to datetime
    try:
        fecha_subida = datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
    except ValueError:
        fecha_subida = datetime.utcnow()  # fallback

    return {
        "titulo": titulo,
        "fecha_subida": fecha_subida,
        "tags": etiquetas,
        "views": vistas,
    }


# Ejemplo de uso
if __name__ == "__main__":
    url_video = "dQw4w9WgXcQ"
    datos = obtener_datos_youtube(url_video)
    print(datos)
