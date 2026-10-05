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
# IMPORTAR RICH
# ============================================================

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.prompt import Prompt, Confirm
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Rich no está instalado. Usando modo básico.")
    print("   Instala con: pip3 install rich")

# ============================================================
# CONFIGURACIÓN
# ============================================================

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secrets.json'

CARPETA_VIDEOS = '/home/eberth/Escritorio/youtube'

TITULO_DEFAULT = None
DESCRIPCION_DEFAULT = ""
TAGS_DEFAULT = ["MMA", "UFC", "MARTIAL", "MIX", "ART"]
CATEGORIA_DEFAULT = "22"

ARCHIVO_REGISTRO = '/home/eberth/videos_subidos.json'

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
# CONSOLA RICH
# ============================================================

console = Console()

def mostrar_titulo():
    """Muestra el título principal con estilo."""
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]🎬 SUBIR SHORTS A YOUTUBE[/bold cyan]\n"
            "[dim]Automatización de subida de videos[/dim]",
            border_style="cyan",
            box=box.DOUBLE
        ))
    else:
        print("\n" + "=" * 50)
        print("   🎬 SUBIR SHORTS A YOUTUBE")
        print("=" * 50)

def mostrar_menu():
    """Muestra el menú principal con estilo."""
    if RICH_AVAILABLE:
        table = Table(
            title="📋 Opciones",
            box=box.ROUNDED,
            border_style="cyan",
            show_header=False,
            padding=(0, 2)
        )
        table.add_column("Opción", style="bold cyan", justify="center")
        table.add_column("Descripción", style="white")
        
        table.add_row("1", "Subir un video")
        table.add_row("2", "Subir todos los videos de la carpeta")
        table.add_row("3", "Ver videos en la carpeta")
        table.add_row("4", "Configurar metadatos por defecto")
        table.add_row("5", "[red]Salir[/red]")
        
        console.print(table)
    else:
        print("\nOpciones:")
        print("  1. Subir un video")
        print("  2. Subir todos los videos de la carpeta")
        print("  3. Ver videos en la carpeta")
        print("  4. Configurar metadatos por defecto")
        print("  5. Salir")

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
                console.print(f"[bold red]❌ Error: No se encontró '{CLIENT_SECRETS_FILE}'[/bold red]")
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
            if RICH_AVAILABLE:
                console.print("  [cyan]📤 Subiendo...[/cyan]", end="")
            else:
                print("  📤 Subiendo...", end="")
            status, response = insert_request.next_chunk()
            if response is not None:
                console.print(" [green]✅[/green]")
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
                console.print(f"\n  [bold red]❌ Demasiados reintentos. Error: {error}[/bold red]")
                return None
            
            sleep_seconds = 2 ** retry
            console.print(f"\n  [yellow]⚠️  Error, reintentando en {sleep_seconds}s... ({error})[/yellow]")
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
        console.print(f"[bold red]❌ La carpeta '{CARPETA_VIDEOS}' no existe.[/bold red]")
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
    """Muestra los videos en la carpeta con estilo."""
    videos = obtener_videos()
    
    if not videos:
        console.print(f"[bold red]❌ No se encontraron videos en '{CARPETA_VIDEOS}'.[/bold red]")
        return
    
    registro = cargar_registro()
    subidos = sum(1 for v in videos if v.name in registro)
    pendientes = len(videos) - subidos
    
    if RICH_AVAILABLE:
        table = Table(
            title=f"📹 Videos en '{CARPETA_VIDEOS}'",
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("#", style="dim", justify="center", width=4)
        table.add_column("Estado", justify="center", width=8)
        table.add_column("Nombre", style="white", min_width=30)
        table.add_column("Tamaño", justify="right", width=10)
        
        for i, video in enumerate(videos, 1):
            tamaño = video.stat().st_size / (1024 * 1024)
            if video.name in registro:
                table.add_row(str(i), "[green]✅ Subido[/green]", video.name, f"{tamaño:.1f} MB")
            else:
                table.add_row(str(i), "[yellow]⏳ Pendiente[/yellow]", video.name, f"{tamaño:.1f} MB")
        
        console.print(table)
        
        # Resumen
        console.print(f"\n[bold]Total:[/bold] {len(videos)} videos | "
                     f"[green]Subidos: {subidos}[/green] | "
                     f"[yellow]Pendientes: {pendientes}[/yellow]")
    else:
        print(f"\n📹 Videos en '{CARPETA_VIDEOS}':")
        print("-" * 60)
        for i, video in enumerate(videos, 1):
            tamaño = video.stat().st_size / (1024 * 1024)
            if video.name in registro:
                print(f"  {i}. ✅ {video.name} ({tamaño:.1f} MB)")
            else:
                print(f"  {i}. ⏳ {video.name} ({tamaño:.1f} MB)")
        print("-" * 60)
        print(f"Total: {len(videos)} videos | Subidos: {subidos} | Pendientes: {pendientes}")

def subir_video_especifico(youtube, numero):
    """Sube un video específico por número."""
    videos = obtener_videos()
    
    if not videos:
        console.print("[bold red]❌ No se encontraron videos en la carpeta.[/bold red]")
        return
    
    if numero < 1 or numero > len(videos):
        console.print(f"[bold red]❌ Número inválido. Hay {len(videos)} videos.[/bold red]")
        return
    
    video = videos[numero - 1]
    
    console.print(f"\n[bold cyan]📝 Metadatos para:[/bold cyan] {video.name}")
    titulo_default = video.stem
    
    if RICH_AVAILABLE:
        titulo = Prompt.ask(f"Título", default=titulo_default)
        descripcion = Prompt.ask("Descripción", default=DESCRIPCION_DEFAULT)
        tags_input = Prompt.ask(f"Tags (separados por coma)", default=", ".join(TAGS_DEFAULT))
    else:
        titulo = input(f"Título [{titulo_default}]: ").strip() or titulo_default
        descripcion = input(f"Descripción [{DESCRIPCION_DEFAULT}]: ").strip() or DESCRIPCION_DEFAULT
        tags_input = input(f"Tags [{', '.join(TAGS_DEFAULT)}]: ").strip()
    
    tags = [t.strip() for t in tags_input.split(',')] if tags_input else TAGS_DEFAULT
    
    if RICH_AVAILABLE:
        console.print(f"\n[bold]📋 Resumen:[/bold]")
        console.print(f"  Video: {video.name}")
        console.print(f"  Título: [cyan]{titulo}[/cyan]")
        console.print(f"  Descripción: {descripcion}")
        console.print(f"  Tags: [green]{', '.join(tags)}[/green]")
        
        if not Confirm.ask("\n¿Subir este video?"):
            console.print("[yellow]❌ Cancelado.[/yellow]")
            return
    else:
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
        console.print(f"\n[bold green]🚀 Subiendo '{video.name}'...[/bold green]")
        response = upload_video(youtube, str(video), titulo, descripcion, tags, CATEGORIA_DEFAULT)
        
        if response:
            video_id = response['id']
            url = f"https://youtu.be/{video_id}"
            marcar_como_subido(video.name, video_id, url)
            console.print(f"\n[bold green]✅ ¡Video subido exitosamente![/bold green]")
            console.print(f"🔗 URL: [link={url}]{url}[/link]")
            console.print(f"📊 ID: {video_id}")
        else:
            console.print(f"\n[bold red]❌ Error al subir el video.[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")

def subir_todos_los_videos(youtube):
    """Sube todos los videos de la carpeta."""
    videos = obtener_videos()
    
    if not videos:
        console.print("[bold red]❌ No se encontraron videos en la carpeta.[/bold red]")
        return
    
    console.print(f"\n[bold cyan]📹 Se encontraron {len(videos)} videos.[/bold cyan]")
    console.print(f"📝 Título: nombre del archivo")
    console.print(f"📝 Descripción: vacía")
    console.print(f"🏷️  Tags: {', '.join(TAGS_DEFAULT)}")
    
    if RICH_AVAILABLE:
        if not Confirm.ask(f"\n¿Subir todos los {len(videos)} videos?"):
            console.print("[yellow]❌ Cancelado.[/yellow]")
            return
    else:
        confirmar = input(f"\n¿Subir todos los {len(videos)} videos? (s/n): ").strip().lower()
        if confirmar != 's':
            print("❌ Cancelado.")
            return
    
    exitos = 0
    fallos = 0
    
    for i, video in enumerate(videos, 1):
        console.print(f"\n[bold cyan][{i}/{len(videos)}][/bold cyan] Procesando: {video.name}")
        
        titulo = video.stem
        
        try:
            response = upload_video(youtube, str(video), titulo, DESCRIPCION_DEFAULT, TAGS_DEFAULT, CATEGORIA_DEFAULT)
            if response:
                video_id = response['id']
                url = f"https://youtu.be/{video_id}"
                marcar_como_subido(video.name, video_id, url)
                console.print(f"  [green]✅ Subido: {url}[/green]")
                exitos += 1
            else:
                console.print(f"  [red]❌ Falló: {video.name}[/red]")
                fallos += 1
        except Exception as e:
            console.print(f"  [red]❌ Error: {e}[/red]")
            fallos += 1
    
    if RICH_AVAILABLE:
        console.print(f"\n[bold]📊 Resumen: {exitos} exitosos, {fallos} fallidos[/bold]")
    else:
        print(f"\n{'=' * 50}")
        print(f"📊 Resumen: {exitos} exitosos, {fallos} fallidos")
        print(f"{'=' * 50}")

def configurar_metadatos():
    """Permite configurar los metadatos por defecto."""
    global TITULO_DEFAULT, DESCRIPCION_DEFAULT, TAGS_DEFAULT, CATEGORIA_DEFAULT
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]⚙️  CONFIGURAR METADATOS POR DEFECTO[/bold cyan]",
            border_style="cyan"
        ))
    else:
        print("\n" + "=" * 50)
        print("   ⚙️  CONFIGURAR METADATOS POR DEFECTO")
        print("=" * 50)
    
    if RICH_AVAILABLE:
        console.print(f"\nTítulo actual: {TITULO_DEFAULT}")
        nuevo = Prompt.ask("Nuevo título (Enter para mantener)", default=str(TITULO_DEFAULT) if TITULO_DEFAULT else "")
        if nuevo:
            TITULO_DEFAULT = nuevo
        
        console.print(f"\nDescripción actual: {DESCRIPCION_DEFAULT}")
        nuevo = Prompt.ask("Nueva descripción (Enter para mantener)", default=DESCRIPCION_DEFAULT)
        if nuevo:
            DESCRIPCION_DEFAULT = nuevo
        
        console.print(f"\nTags actuales: {', '.join(TAGS_DEFAULT)}")
        nuevo = Prompt.ask("Nuevos tags separados por coma (Enter para mantener)", default=", ".join(TAGS_DEFAULT))
        if nuevo:
            TAGS_DEFAULT = [t.strip() for t in nuevo.split(',')]
        
        console.print(f"\nCategoría actual: {CATEGORIA_DEFAULT}")
        console.print("Categorías comunes: 22=People & Blogs, 10=Music, 24=Entertainment")
        nuevo = Prompt.ask("Nueva categoría (Enter para mantener)", default=CATEGORIA_DEFAULT)
        if nuevo:
            CATEGORIA_DEFAULT = nuevo
    else:
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
    
    console.print("\n[green]✅ Metadatos actualizados.[/green]")

def modo_interactivo(youtube):
    """Modo interactivo con menú."""
    while True:
        mostrar_titulo()
        console.print(f"\n[dim]📁 Carpeta de videos:[/dim] [cyan]{CARPETA_VIDEOS}[/cyan]")
        mostrar_menu()
        
        if RICH_AVAILABLE:
            opcion = Prompt.ask("\n[bold]Selecciona una opción[/bold]", choices=["1", "2", "3", "4", "5"], default="5")
        else:
            opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == '1':
            videos = obtener_videos()
            if not videos:
                console.print("[bold red]❌ No se encontraron videos en la carpeta.[/bold red]")
                continue
            
            if RICH_AVAILABLE:
                table = Table(title="📹 Videos disponibles", box=box.ROUNDED, border_style="cyan")
                table.add_column("#", style="dim", justify="center", width=4)
                table.add_column("Nombre", style="white")
                
                for i, video in enumerate(videos, 1):
                    table.add_row(str(i), video.name)
                
                console.print(table)
                
                seleccion = int(Prompt.ask("\nSelecciona el número del video", default="1"))
                subir_video_especifico(youtube, seleccion)
            else:
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
            console.print("\n[bold yellow]👋 ¡Hasta luego![/bold yellow]")
            break
        else:
            console.print("[bold red]❌ Opción inválida.[/bold red]")

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
        console.print("\n[bold cyan]🔐 Autenticando con YouTube...[/bold cyan]")
        try:
            youtube = get_authenticated_service()
            console.print("[green]✅ Autenticación exitosa![/green]")
        except Exception as e:
            console.print(f"\n[bold red]❌ Error de autenticación: {e}[/bold red]")
            sys.exit(1)
        
        modo_interactivo(youtube)
        return
    
    # Modo con argumentos
    console.print("\n[bold cyan]🔐 Autenticando con YouTube...[/bold cyan]")
    try:
        youtube = get_authenticated_service()
        console.print("[green]✅ Autenticación exitosa![/green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error de autenticación: {e}[/bold red]")
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
