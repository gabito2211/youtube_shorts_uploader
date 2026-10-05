# 🎬 Subir Shorts a YouTube - Guía de Inicio Rápido

## 📋 Requisitos Previos

1. **Python 3.7+** instalado
2. **Cuenta de Google** con canal de YouTube
3. **Credenciales de API** de Google Cloud

---

## 🔑 Paso 1: Obtener Credenciales de Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. En el menú lateral, ve a **APIs y servicios** → **Biblioteca**
4. Busca **"YouTube Data API v3"** y haz clic en **Habilitar**
5. Ve a **APIs y servicios** → **Credenciales**
6. Haz clic en **Crear credenciales** → **ID de cliente OAuth**
7. Configura la pantalla de consentimiento:
   - Tipo: **Externo**
   - Nombre de la app: **Subir Shorts** (o el que prefieras)
   - Agrega tu email en **Usuarios de prueba**
8. Tipo de cliente: **Aplicación de escritorio**
9. Descarga el archivo JSON y guárdalo como **`client_secrets.json`** en la misma carpeta que el script

---

## 📁 Paso 2: Preparar los Videos

1. Coloca tus videos en la carpeta: `/home/eberth/Escritorio/youtube`
2. Formatos soportados: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`
3. Los videos deben ser verticales (9:16) para Shorts

---

## 🚀 Paso 3: Ejecutar el Script

```bash
cd /home/eberth
python3 subir_shorts.py
```

### Primera ejecución:
- Se abrirá una ventana del navegador para autorizar la aplicación
- Inicia sesión con tu cuenta de Google
- Acepta los permisos de YouTube
- Las credenciales se guardarán automáticamente en `token.pickle`

### Ejecuciones posteriores:
- No necesitas autorizar de nuevo (a menos que el token expire)

---

## ⚙️ Configuración del Script

Edita estas variables en `subir_shorts.py`:

```python
CARPETA_VIDEOS = '/home/eberth/Escritorio/youtube'  # Carpeta de videos
TITULO_DEFAULT = "Short #{numero}"                  # Título por defecto
DESCRIPCION_DEFAULT = "Remix de audio generado por IA"  # Descripción
TAGS_DEFAULT = ["shorts", "remix", "audio", "ia"]   # Tags
CATEGORIA_DEFAULT = "22"                            # Categoría (22 = People & Blogs)
```

---

## 📊 Opciones del Script

| Opción | Descripción |
|--------|-------------|
| 1 | Subir un video específico con metadatos personalizados |
| 2 | Subir todos los videos de la carpeta automáticamente |
| 3 | Ver lista de videos en la carpeta |
| 4 | Configurar metadatos por defecto |
| 5 | Salir |

---

## ⚠️ Notas Importantes

- **Límite de cuota**: YouTube Data API tiene un límite de ~10,000 unidades por día
  - Cada subida cuesta ~1,600 unidades
  - Puedes subir ~6 videos por día con la cuota estándar
- **Token de acceso**: Expira después de 7 días (se renueva automáticamente)
- **Videos privados**: El script sube videos como **públicos** por defecto

---

## 🔧 Solución de Problemas

### Error: "client_secrets.json not found"
- Asegúrate de que el archivo está en la misma carpeta que el script
- Verifica que el nombre sea exactamente `client_secrets.json`

### Error: "Access blocked"
- Agrega tu email en **Usuarios de prueba** en Google Cloud Console
- Asegúrate de que YouTube Data API v3 esté habilitado

### Error: "Quota exceeded"
- Espera 24 horas para que se renueve la cuota
- Solicita aumento de cuota en Google Cloud Console

---

## 📞 Soporte

Si tienes problemas, revisa:
1. Que todas las dependencias estén instaladas
2. Que las credenciales sean válidas
3. Que la carpeta de videos exista y contenga videos
