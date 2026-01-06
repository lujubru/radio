# Cambios Realizados en la Radio Online

## Problemas Solucionados

### 1. Bug de Reproducción Arreglado
- Se corrigió el error en `app.py` línea 307 donde se usaba la variable `final_url` que no existía
- Se eliminó la referencia duplicada a `audio_url`
- Ahora el botón de reproducción funciona correctamente

### 2. Integración con Jamendo API
- Se reemplazó YouTube/yt-dlp con Jamendo API (música libre y gratuita)
- Se agregó la función `search_jamendo_tracks()` para buscar música
- Se agregó el endpoint `/api/jamendo/search` para búsquedas desde el admin
- Todas las canciones ahora vienen de Jamendo con URLs directas de MP3

### 3. Gestión Mejorada de Playlists
- Nueva interfaz visual para gestionar playlists en `/admin/playlists/<id>/manage`
- Búsqueda en tiempo real de música de Jamendo
- Filtros por género (Rock, Pop, Jazz, Electrónica, etc.)
- Vista previa con carátulas de las canciones
- Botón "Agregar" para añadir canciones directamente desde Jamendo a la playlist
- Visualización de duración total de la playlist
- Orden de canciones visible con posición (#1, #2, etc.)

## Nuevas Funcionalidades

### Búsqueda de Jamendo en Playlist Manager
- Barra de búsqueda para encontrar canciones por nombre o artista
- Chips de género para filtrar música fácilmente
- Grid de resultados con:
  - Carátula del álbum
  - Nombre de la canción
  - Artista
  - Duración
  - Botón para agregar directamente

### Visualización de Duración
- Badge mostrando el tiempo total de cada playlist
- Formato MM:SS para fácil lectura
- Actualización automática al agregar/quitar canciones

## Archivos Modificados

1. **app.py**
   - Eliminado yt-dlp
   - Agregado requests para API de Jamendo
   - Nueva función `search_jamendo_tracks()`
   - Nuevo endpoint `/api/jamendo/search`
   - Bug fix en `api_current_track()`
   - Cálculo de duración total en `manage_playlist()`

2. **requirements.txt**
   - Eliminado yt-dlp
   - Agregado requests==2.31.0

3. **templates/playlist_manage.html**
   - Rediseño completo de la interfaz
   - Integración con Jamendo API
   - Grid de resultados responsive
   - Filtros de género interactivos
   - JavaScript para búsqueda en tiempo real

4. **templates/ads.html**
   - Creado nuevo template para gestión de publicidades

## Cómo Usar las Nuevas Funciones

### Agregar Canciones desde Jamendo
1. Ir a `/admin/playlists`
2. Clic en "Gestionar" en cualquier playlist
3. Usar la barra de búsqueda o seleccionar un género
4. Hacer clic en "Buscar"
5. Clic en "+ Agregar" en cualquier canción
6. La canción se agrega automáticamente a la playlist

### Organizar Programas Radiales
1. Crear playlists temáticas (Rock Mañana, Pop Tarde, etc.)
2. Ver la duración total en tiempo real
3. Ajustar contenido según duración del programa
4. Configurar horarios en `/admin/schedule`

## Cómo Iniciar el Proyecto

```bash
# Instalar dependencias
pip install -r requirements.txt

# Crear la base de datos
python admin.py

# Iniciar el servidor
python app.py
```

Luego acceder a:
- Radio: http://localhost:5000
- Admin: http://localhost:5000/admin
  - Usuario: admin
  - Password: admin123

## API de Jamendo

La aplicación usa Jamendo API con el client_id público `da67e0d3`.
No requiere configuración adicional ni claves de API privadas.

## Notas Importantes

- Todas las canciones de Jamendo están bajo licencias Creative Commons
- Las URLs de audio son MP3 directos, no requieren procesamiento
- La búsqueda puede devolver hasta 20 resultados por petición
- Los géneros disponibles incluyen: rock, pop, electronic, jazz, classical, ambient
