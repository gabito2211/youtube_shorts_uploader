#!/usr/bin/env python3
"""
Script para subir videos a YouTube Shorts usando YouTube Data API v3.
Autenticación OAuth 2.0 - Subida manual con metadata.

Uso:
  python3 subir_shorts.py                    # Modo interactivo
  python3 subir_shorts.py --listar           # Listar videos
  python3 subir_shorts.py --subir <número>   # Subir video específico
  python3 subir_shorts.py --todos            # Subir todos los videos
  python3 subir_shorts.py --config           # Configurar metadatos
"""

import os
import sys
import json
import pickle
import argparse
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ============================================================
# COLORES PARA TERMINAL
# ============================================================

class Colores:
    VERDE = '\033[92m'
    AMARILLO = '\033[93m'
    ROJO = '\033[91m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BLANCO = '\033[97m'
    NEGRITA = '\033[1m'
    SUBRAYADO = '\033[4m'
    FIN = '\033[0m'

# Archivo para registrar videos subidos
ARCHIVO_REGISTRO = '/home/eberth/videos_subidos.json'

# ============================================================
# CONFIGURACIÓN - Modifica estos valores
# ============================================================

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secrets.json'

# Carpeta donde están los videos
CARPETA_VIDEOS = '/home/eberth/Escritorio/youtube'

# Metadatos por defecto
TITULO_DEFAULT = None  # None = usar nombre del archivo
DESCRIPCION_DEFAULT = ""  # Descripción vacía por defecto
TAGS_DEFAULT = ["MMA", "UFC", "MARTIAL", "MIX", "ART"]
CATEGORIA_DEFAULT = "22"  # 22 = People & Blogs

# ============================================================
# CONFIGURACIÓN DE CONTENIDO
# ============================================================

VIDEO_STATUS = {
    "privacyStatus": "public",
    "embeddable": True,
    "license": "youtube",
    "publicStatsViewable": True,
    "madeForKids": False,
    "selfDeclaredMadeForKids": False,
}

CONTENT_DETAILS = {
    "licensedContent": False,
    "hasCustomThumbnail": False,
    "allowedRegions": None,
    "contentRating": {
        "acbRating": "acbUnspecified",
        "bbfcRating": "bbfcUnspecified",
        "cbfcRating": "cbfcUnspecified",
        "chvrsRating": "chvrsUnspecified",
        "djctqRating": "djctqUnspecified",
        "eirinRating": "eirinUnspecified",
        "fmocRating": "fmocUnspecified",
        "fskRating": "fskUnspecified",
        "icaaRating": "icaaUnspecified",
        "kmrbRating": "kmrbUnspecified",
        "mpaaRating": "mpaaUnspecified",
        "rtcRating": "rtcUnspecified",
        "tvpgRating": "tvpgUnspecified",
        "ytRating": "ytUnspecified"
    }
}

# ============================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================

def get_authenticated_service():
    """Autentica con YouTube Data API v3 usando OAuth 2.0."""
    credentials = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"\n❌ Error: No se encontró '{CLIENT_SECRETS_FILE}'")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

# ============================================================
# FUNCIONES DE SUBIDA
# ============================================================

def upload_video(youtube, video_path, titulo, descripcion, tags, categoria):
    """Sube un video a YouTube con los metadatos especificados."""
    
    body = {
        'snippet': {
            'title': titulo,
            'description': descripcion,
            'tags': tags,
            'categoryId': categoria,
            'defaultLanguage': 'es',
            'defaultAudioLanguage': 'es',
        },
        'status': VIDEO_STATUS,
        'contentDetails': CONTENT_DETAILS,
    }
    
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    
    response = resumable_upload(insert_request)
    return response

def resumable_upload(insert_request):
    """Sube el video con reanudación si hay errores."""
    response = None
    error = None
    retry = 0
    max_retries = 10
    
    while response is None:
        try:
            print("  📤 Subiendo...", end="")
            status, response = insert_request.next_chunk()
            if response is not None:
                print(" ✅")
                return response
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"Error HTTP {e.resp.status}: {e.content}"
            else:
                raise
        except Exception as e:
            error = str(e)
        
        if error is not None:
            retry += 1
            if retry > max_retries:
                print(f"\n  ❌ Demasiados reintentos. Error: {error}")
                return None
            
            sleep_seconds = 2 ** retry
            print(f"\n  ⚠️  Error, reintentando en {sleep_seconds}s... ({error})")
            import time
            time.sleep(sleep_seconds)
            error = None
    
    return response

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def obtener_videos():
    """Obtiene la lista de videos en la carpeta."""
    carpeta = Path(CARPETA_VIDEOS)
    if not carpeta.exists():
        print(f"\n❌ La carpeta '{CARPETA_VIDEOS}' no existe.")
        return []
    
    extensiones = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
    videos = [f for f in carpeta.iterdir() if f.suffix.lower() in extensiones]
    videos.sort()
    return videos

def cargar_registro():
    """Carga el registro de videos subidos."""
    if os.path.exists(ARCHIVO_REGISTRO):
        with open(ARCHIVO_REGISTRO, 'r') as f:
            return json.load(f)
    return {}

def guardar_registro(registro):
    """Guarda el registro de videos subidos."""
    with open(ARCHIVO_REGISTRO, 'w') as f:
        json.dump(registro, f, indent=2)

def marcar_como_subido(nombre_archivo, video_id, url):
    """Marca un video como subido en el registro."""
    registro = cargar_registro()
    registro[nombre_archivo] = {
        'video_id': video_id,
        'url': url,
        'fecha': str(Path().stat().st_mtime)
    }
    guardar_registro(registro)

def esta_subido(nombre_archivo):
    """Verifica si un video ya fue subido."""
    registro = cargar_registro()
    return nombre_archivo in registro

def listar_videos():
    """Muestra los videos en la carpeta con colores."""
    videos = obtener_videos()
    
    if not videos:
        print(f"\n❌ No se encontraron videos en '{CARPETA_VIDEOS}'.")
        return
    
    registro = cargar_registro()
    subidos = sum(1 for v in videos if v.name in registro)
    pendientes = len(videos) - subidos
    
    print(f"\n📹 Videos en '{CARPETA_VIDEOS}':")
    print("-" * 60)
    for i, video in enumerate(videos, 1):
        tamaño = video.stat().st_size / (1024 * 1024)
        if video.name in registro:
            print(f"  {Colores.VERDE}{i}. ✅ {video.name} ({tamaño:.1f} MB){Colores.FIN}")
        else:
            print(f"  {Colores.AMARILLO}{i}. ⏳ {video.name} ({tamaño:.1f} MB){Colores.FIN}")
    print("-" * 60)
    print(f"Total: {len(videos)} videos | {Colores.VERDE}Subidos: {subidos}{Colores.FIN} | {Colores.AMARILLO}Pendientes: {pendientes}{Colores.FIN}")

def subir_video_especifico(youtube, numero):
    """Sube un video específico por número."""
    videos = obtener_videos()
    
    if not videos:
        print("\n❌ No se encontraron videos en la carpeta.")
        return
    
    if numero < 1 or numero > len(videos):
        print(f"\n❌ Número inválido. Hay {len(videos)} videos.")
        return
    
    video = videos[numero - 1]
    
    print(f"\n📝 Metadatos para: {video.name}")
    titulo_default = video.stem
    titulo = input(f"Título [{titulo_default}]: ").strip() or titulo_default
    descripcion = input(f"Descripción [{DESCRIPCION_DEFAULT}]: ").strip() or DESCRIPCION_DEFAULT
    tags_input = input(f"Tags [{', '.join(TAGS_DEFAULT)}]: ").strip()
    tags = [t.strip() for t in tags_input.split(',')] if tags_input else TAGS_DEFAULT
    
    print(f"\n📋 Resumen:")
    print(f"  Video: {video.name}")
    print(f"  Título: {titulo}")
    print(f"  Descripción: {descripcion}")
    print(f"  Tags: {', '.join(tags)}")
    
    confirmar = input("\n¿Subir este video? (s/n): ").strip().lower()
    if confirmar != 's':
        print("❌ Cancelado.")
        return
    
    try:
        print(f"\n🚀 Subiendo '{video.name}'...")
        response = upload_video(youtube, str(video), titulo, descripcion, tags, CATEGORIA_DEFAULT)
        
        if response:
            video_id = response['id']
            url = f"https://youtu.be/{video_id}"
            marcar_como_subido(video.name, video_id, url)
            print(f"\n{Colores.VERDE}✅ ¡Video subido exitosamente!{Colores.FIN}")
            print(f"🔗 URL: {url}")
            print(f"📊 ID: {video_id}")
        else:
            print(f"\n{Colores.ROJO}❌ Error al subir el video.{Colores.FIN}")
    except Exception as e:
        print(f"\n{Colores.ROJO}❌ Error: {e}{Colores.FIN}")

def subir_todos_los_videos(youtube):
    """Sube todos los videos de la carpeta."""
    videos = obtener_videos()
    
    if not videos:
        print("\n❌ No se encontraron videos en la carpeta.")
        return
    
    print(f"\n📹 Se encontraron {len(videos)} videos.")
    print(f"📝 Título: nombre del archivo")
    print(f"📝 Descripción: vacía")
    print(f"🏷️  Tags: {', '.join(TAGS_DEFAULT)}")
    
    confirmar = input(f"\n¿Subir todos los {len(videos)} videos? (s/n): ").strip().lower()
    if confirmar != 's':
        print("❌ Cancelado.")
        return
    
    exitos = 0
    fallos = 0
    
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] Procesando: {video.name}")
        
        titulo = video.stem
        
        try:
            response = upload_video(youtube, str(video), titulo, DESCRIPCION_DEFAULT, TAGS_DEFAULT, CATEGORIA_DEFAULT)
            if response:
                video_id = response['id']
                url = f"https://youtu.be/{video_id}"
                marcar_como_subido(video.name, video_id, url)
                print(f"  {Colores.VERDE}✅ Subido: {url}{Colores.FIN}")
                exitos += 1
            else:
                print(f"  {Colores.ROJO}❌ Falló: {video.name}{Colores.FIN}")
                fallos += 1
        except Exception as e:
            print(f"  {Colores.ROJO}❌ Error: {e}{Colores.FIN}")
            fallos += 1
    
    print(f"\n{'=' * 50}")
    print(f"📊 Resumen: {exitos} exitosos, {fallos} fallidos")
    print(f"{'=' * 50}")

def configurar_metadatos():
    """Permite configurar los metadatos por defecto."""
    global TITULO_DEFAULT, DESCRIPCION_DEFAULT, TAGS_DEFAULT, CATEGORIA_DEFAULT
    
    print("\n" + "=" * 50)
    print("   ⚙️  CONFIGURAR METADATOS POR DEFECTO")
    print("=" * 50)
    
    print(f"\nTítulo actual: {TITULO_DEFAULT}")
    nuevo = input("Nuevo título (Enter para mantener): ").strip()
    if nuevo:
        TITULO_DEFAULT = nuevo
    
    print(f"\nDescripción actual: {DESCRIPCION_DEFAULT}")
    nuevo = input("Nueva descripción (Enter para mantener): ").strip()
    if nuevo:
        DESCRIPCION_DEFAULT = nuevo
    
    print(f"\nTags actuales: {', '.join(TAGS_DEFAULT)}")
    nuevo = input("Nuevos tags separados por coma (Enter para mantener): ").strip()
    if nuevo:
        TAGS_DEFAULT = [t.strip() for t in nuevo.split(',')]
    
    print(f"\nCategoría actual: {CATEGORIA_DEFAULT}")
    print("Categorías comunes: 22=People & Blogs, 10=Music, 24=Entertainment")
    nuevo = input("Nueva categoría (Enter para mantener): ").strip()
    if nuevo:
        CATEGORIA_DEFAULT = nuevo
    
    print("\n✅ Metadatos actualizados.")

def modo_interactivo(youtube):
    """Modo interactivo con menú."""
    while True:
        print("\n" + "=" * 50)
        print("   🎬 SUBIR SHORTS A YOUTUBE")
        print("=" * 50)
        print("\n📁 Carpeta de videos:", CARPETA_VIDEOS)
        print("\nOpciones:")
        print("  1. Subir un video")
        print("  2. Subir todos los videos de la carpeta")
        print("  3. Ver videos en la carpeta")
        print("  4. Configurar metadatos por defecto")
        print("  5. Salir")
        print("-" * 50)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == '1':
            videos = obtener_videos()
            if not videos:
                print("\n❌ No se encontraron videos en la carpeta.")
                continue
            
            print("\n📹 Videos disponibles:")
            for i, video in enumerate(videos, 1):
                print(f"  {i}. {video.name}")
            
            try:
                seleccion = int(input("\nSelecciona el número del video: "))
                subir_video_especifico(youtube, seleccion)
            except ValueError:
                print("❌ Entrada inválida.")
        elif opcion == '2':
            subir_todos_los_videos(youtube)
        elif opcion == '3':
            listar_videos()
        elif opcion == '4':
            configurar_metadatos()
        elif opcion == '5':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción inválida.")

# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description='Subir videos a YouTube Shorts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 subir_shorts.py                    # Modo interactivo
  python3 subir_shorts.py --listar           # Listar videos
  python3 subir_shorts.py --subir 1         # Subir video #1
  python3 subir_shorts.py --todos            # Subir todos los videos
  python3 subir_shorts.py --config           # Configurar metadatos
        """
    )
    
    parser.add_argument('--listar', action='store_true', help='Listar videos en la carpeta')
    parser.add_argument('--subir', type=int, metavar='N', help='Subir video número N')
    parser.add_argument('--todos', action='store_true', help='Subir todos los videos')
    parser.add_argument('--config', action='store_true', help='Configurar metadatos por defecto')
    
    args = parser.parse_args()
    
    # Si no hay argumentos, modo interactivo
    if not any([args.listar, args.subir, args.todos, args.config]):
        print("\n🔐 Autenticando con YouTube...")
        try:
            youtube = get_authenticated_service()
            print("✅ Autenticación exitosa!")
        except Exception as e:
            print(f"\n❌ Error de autenticación: {e}")
            sys.exit(1)
        
        modo_interactivo(youtube)
        return
    
    # Modo con argumentos
    print("\n🔐 Autenticando con YouTube...")
    try:
        youtube = get_authenticated_service()
        print("✅ Autenticación exitosa!")
    except Exception as e:
        print(f"\n❌ Error de autenticación: {e}")
        sys.exit(1)
    
    if args.listar:
        listar_videos()
    elif args.subir:
        subir_video_especifico(youtube, args.subir)
    elif args.todos:
        subir_todos_los_videos(youtube)
    elif args.config:
        configurar_metadatos()

if __name__ == '__main__':
    main()
