import json
import yt_dlp
import requests
import time
import re
import argparse
import sys
import os
import asyncio

from common.config import SEARCH_NUMBER

# --- 1. CONFIGURACIÓN Y UTILIDADES ---

INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
]

def limpiar_nombre_archivo(texto):
    """
    Limpia la palabra clave para que pueda ser usada como un nombre de archivo válido.
    """
    # Reemplaza caracteres no alfanuméricos por espacios, elimina espacios extra y une con guiones
    texto_limpio = re.sub(r'[^\w\s-]', '', texto).strip()
    return re.sub(r'[-\s]+', '-', texto_limpio).lower()


# --- 2. ESTRATEGIAS DE BÚSQUEDA ---

def estrategia_ytdlp(busqueda, cantidad):
    print(f"🔹 [Nivel 1] Buscando con yt-dlp: '{busqueda}'")
    ydl_opts = {"quiet": True, "extract_flat": True, "force_generic_extractor": False}
    query = f"ytsearch{cantidad}:{busqueda}"
    links = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(query, download=False)
        if "entries" in result:
            for entry in result["entries"]:
                if "url" in entry:
                    links.append(entry["url"])
                elif "id" in entry:
                    links.append(f"https://www.youtube.com/watch?v={entry['id']}")
    return links


def estrategia_libreria_python(busqueda, cantidad):
    print(f"🔸 [Nivel 2] Buscando con youtube-search-python: '{busqueda}'")
    try:
        from youtubesearchpython import VideosSearch
    except ImportError:
        print("⚠️ Librería youtubesearchpython no instalada.")
        return []

    search = VideosSearch(busqueda, limit=cantidad)
    links = []
    intentos = 0
    while len(links) < cantidad and intentos < 10:
        results = search.result().get("result", [])
        if not results:
            break
        for video in results:
            links.append(video["link"])
            
        if len(links) < cantidad:
            try:
                search.next()
                intentos += 1
                time.sleep(0.20)
            except:
                break
    return links


def estrategia_invidious(busqueda, cantidad):
    print(f"🔻 [Nivel 3] Buscando con API Invidious: '{busqueda}'")
    links = []
    for instance in INVIDIOUS_INSTANCES:
        try:
            page = 1
            more_results = True
            while len(links) < cantidad and more_results:
                response = requests.get(
                    f"{instance}/api/v1/search",
                    params={
                        "q": busqueda,
                        "page": page,
                        "type": "video",
                        "sort": "relevance",
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        more_results = False
                        break
                    for video in data:
                        if video.get("videoId"):
                            links.append(
                                f"https://www.youtube.com/watch?v={video.get('videoId')}"
                            )
                    page += 1
                    if page > 10:
                        more_results = False
                else:
                    raise Exception("Status error")
            return links
        except:
            continue
    raise Exception("Fallo total en Invidious")


# --- 3. ENVÍO AL SERVIDOR ---

async def enviar_ids_al_servidor(lista_urls, videoService):
    from models.controller.input.publish_video_request import PublishVideoRequest
    
    patron_regex = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    print(f"🚀 Enviando {len(lista_urls)} IDs al servidor...")

    enviados = 0

    for url_video in lista_urls:
        match = re.search(patron_regex, url_video)
        if match:
            video_id = match.group(1)
            request = PublishVideoRequest(video_id=video_id)

            try:
                await videoService.publish_video(request)
                enviados += 1
                print(f"Insertado video con ID: {video_id}")
            except Exception as e:
                print(f"   ❌ Error ID {video_id}: {e}")

            await asyncio.sleep(0.05)
        else:
            print(f"   ❓ URL sin ID válido: {url_video}")

    print(f"🏁 Resumen API: {enviados} éxitos de {len(lista_urls)} intentos.")


# --- 4. PROCESO ÚNICO ---

async def buscar_y_procesar(palabra_clave, videoService):
    """Ejecuta el ciclo completo para UNA palabra clave específica"""
    nombre_limpio = limpiar_nombre_archivo(palabra_clave)
    nombre_fichero = f"archives/yt-{nombre_limpio}.json"
    
    links_resultantes = []

    try:
        links_resultantes = estrategia_ytdlp(palabra_clave, SEARCH_NUMBER)
    except Exception:
        pass

    if not links_resultantes:
        try:
            links_resultantes = estrategia_libreria_python(palabra_clave, SEARCH_NUMBER)
        except Exception:
            pass

    if not links_resultantes:
        try:
            links_resultantes = estrategia_invidious(palabra_clave, SEARCH_NUMBER)
        except Exception:
            pass

    links_resultantes = list(dict.fromkeys(links_resultantes)).reverse()


    if links_resultantes:
        await enviar_ids_al_servidor(links_resultantes, videoService)
    else:
        print(f"⚠️ Sin videos encontrados para la búsqueda: '{palabra_clave}'")


# --- 5. GESTOR DE BUCLE Y LECTURA DE ARCHIVO ---

def procesar_lista_palabras(ruta_archivo):
    """
    Lee un archivo de texto línea por línea y realiza la búsqueda para cada término.
    """
    if not os.path.exists(ruta_archivo):
        print(f"❌ Error: No se ha encontrado el archivo '{ruta_archivo}'.")
        print("Crea el archivo y pon una palabra clave o frase por línea.")
        sys.exit(1)

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    palabras_clave = [linea.strip() for linea in lineas if linea.strip()]

    if not palabras_clave:
        print(f"⚠️ El archivo '{ruta_archivo}' está vacío.")
        sys.exit(1)

    print(f"\n📢 --- INICIANDO PROCESO DESDE ARCHIVO ---")
    print(f"📄 Archivo: {ruta_archivo}")
    print(f"🔍 Palabras a procesar: {len(palabras_clave)}")
    print("--------------------------------------------------\n")

    for palabra in palabras_clave:
        print(f"\n📆 >>> Procesando búsqueda: '{palabra}'")
        buscar_y_procesar(palabra)
        print("⏳ Esperando 2 segundos antes de la siguiente búsqueda...")
        time.sleep(2)

    print("\n✅ Proceso completado. Se han leído todas las líneas del archivo.")


