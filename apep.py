import os
from datetime import datetime, time
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:slqphmYdujODlPicySeFkQkAFfLTlrNt@centerbeam.proxy.rlwy.net:29539/railway').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/ads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

JAMENDO_CLIENT_ID = os.environ.get('JAMENDO_CLIENT_ID', '44c2831a')

# ===================================
# MODELOS DE BASE DE DATOS
# ===================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255))
    album = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    audio_url = db.Column(db.Text, nullable=False)
    cover_url = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlaylistTrack(db.Model):
    __tablename__ = 'playlist_tracks'
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'))
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id', ondelete='CASCADE'))
    position = db.Column(db.Integer, nullable=False)

class Ad(db.Model):
    __tablename__ = 'ads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer)
    ad_type = db.Column(db.String(20), default='commercial')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id', ondelete='CASCADE'))
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class AdConfig(db.Model):
    __tablename__ = 'ad_config'
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(20), nullable=False)
    trigger_value = db.Column(db.Integer, nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey('ads.id', ondelete='CASCADE'))
    priority = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

class PlaybackHistory(db.Model):
    __tablename__ = 'playback_history'
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'))
    ad_id = db.Column(db.Integer)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_played = db.Column(db.Integer)

# ===================================
# DECORADORES Y UTILIDADES
# ===================================

def search_jamendo_tracks(query='', genre='', limit=20):
    try:
        url = 'https://api.jamendo.com/v3.0/tracks/'
        params = {
            'client_id': JAMENDO_CLIENT_ID,
            'format': 'json',
            'limit': limit,
            'audioformat': 'mp32',
            'include': 'musicinfo'
        }
        if query: params['search'] = query
        if genre: params['tags'] = genre

        response = requests.get(url, params=params)
        data = response.json()
        
        # --- LÍNEA DE DEBUG: Mira tu consola de Python cuando busques ---
        print(f"DEBUG: Respuesta Jamendo -> {data}") 

        if 'results' not in data:
            return []

        tracks = []
        for track in data.get('results', []):
            tracks.append({
                'jamendo_id': track['id'],
                'title': track['name'],
                'artist': track['artist_name'],
                'album': track.get('album_name', ''),
                'duration': track['duration'],
                'audio_url': track['audio'],
                'cover_url': track.get('album_image', track.get('image', ''))
            })
        return tracks
    except Exception as e:
        print(f"Error buscando en Jamendo: {e}")
        return []

@app.route('/admin/playlists/<int:playlist_id>/add-jamendo-track', methods=['POST'])
def add_jamendo_track_to_playlist(playlist_id):
    # 1. Crear el track en la DB si no existe
    audio_url = request.form.get('audio_url')
    track = Track.query.filter_by(audio_url=audio_url).first()
    
    if not track:
        track = Track(
            title=request.form.get('title'),
            artist=request.form.get('artist'),
            album=request.form.get('album'),
            duration=int(request.form.get('duration', 0)),
            audio_url=audio_url,
            cover_url=request.form.get('cover_url')
        )
        db.session.add(track)
        db.session.flush() # Para obtener el track.id

    # 2. Vincularlo a la playlist
    last_pos = db.session.query(db.func.max(PlaylistTrack.position)).filter_by(playlist_id=playlist_id).scalar() or 0
    new_rel = PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track.id,
        position=last_pos + 1
    )
    db.session.add(new_rel)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@app.route('/api/tracks/import-jamendo', methods=['POST'])
def import_jamendo_track():
    data = request.json
    # Verificamos si ya existe para no duplicar
    existing_track = Track.query.filter_by(audio_url=data['audio_url']).first()
    
    if not existing_track:
        new_track = Track(
            title=data['title'],
            artist=data['artist'],
            album=data.get('album', ''),
            duration=data['duration'],
            audio_url=data['audio_url'],
            cover_url=data.get('cover_url', '')
        )
        db.session.add(new_track)
        db.session.commit()
        return jsonify({'track_id': new_track.id})
    
    return jsonify({'track_id': existing_track.id})

def get_jamendo_playlists(genre='', limit=20):
    """Obtiene playlists predefinidas de Jamendo"""
    try:
        url = 'https://api.jamendo.com/v3.0/playlists/tracks/'
        params = {
            'client_id': JAMENDO_CLIENT_ID,
            'format': 'json',
            'limit': limit
        }

        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Error obteniendo playlists de Jamendo: {e}")
        return []

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_playlist():
    """Obtiene la playlist actual según día y hora"""
    now = datetime.now()
    day_of_week = now.weekday()  # 0=lunes, 6=domingo
    current_time = now.time()
    
    schedule = Schedule.query.filter(
        Schedule.day_of_week == day_of_week,
        Schedule.start_time <= current_time,
        Schedule.end_time >= current_time,
        Schedule.is_active == True
    ).first()
    
    if schedule:
        return Playlist.query.get(schedule.playlist_id)
    
    # Si no hay horario, devolver playlist por defecto
    return Playlist.query.filter_by(is_active=True).first()

def should_play_ad():
    """Determina si debe reproducirse una publicidad"""
    # Contar canciones reproducidas desde último ad
    last_ad = PlaybackHistory.query.filter(
        PlaybackHistory.ad_id.isnot(None)
    ).order_by(PlaybackHistory.played_at.desc()).first()
    
    if not last_ad:
        tracks_since_ad = PlaybackHistory.query.filter(
            PlaybackHistory.track_id.isnot(None)
        ).count()
    else:
        tracks_since_ad = PlaybackHistory.query.filter(
            PlaybackHistory.track_id.isnot(None),
            PlaybackHistory.played_at > last_ad.played_at
        ).count()
    
    # Buscar configuración activa
    ad_configs = AdConfig.query.filter(
        AdConfig.is_active == True,
        AdConfig.trigger_type == 'track_count'
    ).all()
    
    for config in ad_configs:
        if tracks_since_ad >= config.trigger_value:
            return Ad.query.get(config.ad_id)
    
    return None

# ===================================
# RUTAS PÚBLICAS
# ===================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('index'))

# ===================================
# API DE REPRODUCCIÓN
# ===================================

@app.route('/api/current-track')
def api_current_track():
    """Devuelve la siguiente canción o publicidad a reproducir"""
    
    # Verificar si debe reproducirse un ad
    ad = should_play_ad()
    if ad:
        # Registrar reproducción del ad
        history = PlaybackHistory(ad_id=ad.id, duration_played=ad.duration)
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'type': 'ad',
            'id': ad.id,
            'title': ad.title,
            'audio_url': url_for('static', filename=f'ads/{ad.filename}'),
            'duration': ad.duration
        })
    
    # Obtener playlist actual
    playlist = get_current_playlist()
    if not playlist:
        return jsonify({'error': 'No hay playlist activa'}), 404
    
    # Obtener tracks de la playlist ordenados por posición
    playlist_tracks = PlaylistTrack.query.filter_by(
        playlist_id=playlist.id
    ).order_by(PlaylistTrack.position).all()
    
    if not playlist_tracks:
        return jsonify({'error': 'Playlist vacía'}), 404
    
    # Obtener último track reproducido de esta playlist
    last_history = PlaybackHistory.query.join(
        Track
    ).join(
        PlaylistTrack, PlaylistTrack.track_id == Track.id
    ).filter(
        PlaylistTrack.playlist_id == playlist.id
    ).order_by(PlaybackHistory.played_at.desc()).first()
    
    # Determinar siguiente track
    if last_history:
        last_track_id = last_history.track_id
        current_index = next((i for i, pt in enumerate(playlist_tracks) if pt.track_id == last_track_id), -1)
        next_index = (current_index + 1) % len(playlist_tracks)
    else:
        next_index = 0
    
    next_track_id = playlist_tracks[next_index].track_id
    track = Track.query.get(next_track_id)

    # Registrar reproducción
    history = PlaybackHistory(track_id=track.id, duration_played=track.duration)
    db.session.add(history)
    db.session.commit()

    return jsonify({
        'type': 'track',
        'id': track.id,
        'title': track.title,
        'artist': track.artist,
        'album': track.album,
        'audio_url': track.audio_url,
        'cover_url': track.cover_url,
        'duration': track.duration,
        'playlist': playlist.name
    })

@app.route('/api/now-playing')
def api_now_playing():
    """Devuelve información de la reproducción actual"""
    last_played = PlaybackHistory.query.order_by(
        PlaybackHistory.played_at.desc()
    ).first()
    
    if not last_played:
        return jsonify({'error': 'No hay reproducción actual'}), 404
    
    if last_played.track_id:
        track = Track.query.get(last_played.track_id)
        return jsonify({
            'type': 'track',
            'title': track.title,
            'artist': track.artist,
            'cover_url': track.cover_url,
            'played_at': last_played.played_at.isoformat()
        })
    else:
        ad = Ad.query.get(last_played.ad_id)
        return jsonify({
            'type': 'ad',
            'title': ad.title,
            'played_at': last_played.played_at.isoformat()
        })

# ===================================
# PANEL DE ADMINISTRACIÓN
# ===================================

@app.route('/admin')
@login_required
def admin_dashboard():
    playlists = Playlist.query.filter_by(is_active=True).all()
    tracks_count = Track.query.filter_by(is_active=True).count()
    ads_count = Ad.query.filter_by(is_active=True).count()
    
    return render_template('admin.html', 
                         playlists=playlists,
                         tracks_count=tracks_count,
                         ads_count=ads_count)

@app.route('/admin/playlists')
@login_required
def admin_playlists():
    playlists = Playlist.query.all()
    return render_template('playlists.html', playlists=playlists)

@app.route('/admin/schedule')
@login_required
def admin_schedule():
    # Obtenemos los horarios y las playlists para el formulario
    schedules = Schedule.query.order_by(Schedule.day_of_week, Schedule.start_time).all()
    playlists = Playlist.query.filter_by(is_active=True).all()
    
    # Mapeo de días para mostrar nombres en lugar de números
    days_map = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
    
    return render_template('schedule.html', 
                         schedules=schedules, 
                         playlists=playlists, 
                         days_map=days_map)

@app.route('/admin/schedule/create', methods=['POST'])
@login_required
def create_schedule():
    playlist_id = request.form.get('playlist_id')
    day = int(request.form.get('day_of_week'))
    # Convertir strings de hora (HH:MM) a objetos time
    start = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
    end = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
    
    new_schedule = Schedule(
        playlist_id=playlist_id,
        day_of_week=day,
        start_time=start,
        end_time=end
    )
    db.session.add(new_schedule)
    db.session.commit()
    
    flash('Horario programado con éxito', 'success')
    return redirect(url_for('admin_schedule'))

@app.route('/admin/playlists/create', methods=['POST'])
@login_required
def create_playlist():
    name = request.form.get('name')
    description = request.form.get('description')
    
    playlist = Playlist(name=name, description=description)
    db.session.add(playlist)
    db.session.commit()
    
    flash('Playlist creada exitosamente', 'success')
    return redirect(url_for('admin_playlists'))

@app.route('/admin/playlists/<int:playlist_id>/delete', methods=['POST'])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    playlist.is_active = False
    db.session.commit()
    
    flash('Playlist eliminada exitosamente', 'success')
    return redirect(url_for('admin_playlists'))

@app.route('/admin/tracks')
@login_required
def admin_tracks():
    tracks = Track.query.filter_by(is_active=True).all()
    return render_template('tracks.html', tracks=tracks)

@app.route('/admin/tracks/create', methods=['POST'])
@login_required
def create_track():
    track = Track(
        title=request.form.get('title'),
        artist=request.form.get('artist'),
        album=request.form.get('album'),
        duration=int(request.form.get('duration', 0)),
        audio_url=request.form.get('audio_url'),
        cover_url=request.form.get('cover_url')
    )

    db.session.add(track)
    db.session.commit()
    flash('Canción agregada con éxito', 'success')
    return redirect(url_for('admin_tracks'))

@app.route('/api/jamendo/search')
@login_required
def jamendo_search():
    query = request.args.get('q', '')
    genre = request.args.get('genre', '')
    tracks = search_jamendo_tracks(query=query, genre=genre)
    return jsonify({'tracks': tracks})

@app.route('/admin/ads')
@login_required
def admin_ads():
    ads = Ad.query.filter_by(is_active=True).all()
    return render_template('ads.html', ads=ads)

@app.route('/admin/ads/upload', methods=['POST'])
@login_required
def upload_ad():
    if 'file' not in request.files:
        flash('No se seleccionó archivo', 'error')
        return redirect(url_for('admin_ads'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó archivo', 'error')
        return redirect(url_for('admin_ads'))
    
    if file and file.filename.endswith('.mp3'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        ad = Ad(
            title=request.form.get('title'),
            filename=filename,
            duration=int(request.form.get('duration', 30)),
            ad_type=request.form.get('ad_type', 'commercial')
        )
        db.session.add(ad)
        db.session.commit()
        
        flash('Publicidad subida exitosamente', 'success')
    else:
        flash('Solo se permiten archivos MP3', 'error')
    
    return redirect(url_for('admin_ads'))

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Radio Online",
        "short_name": "Radio",
        "description": "Radio online con rock y pop",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a1a",
        "theme_color": "#e50914",
        "icons": [
            {
                "src": "/static/images/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/images/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/admin/playlists/<int:playlist_id>/manage')
@login_required
def manage_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    current_tracks = db.session.query(Track, PlaylistTrack.position).join(
        PlaylistTrack, Track.id == PlaylistTrack.track_id
    ).filter(PlaylistTrack.playlist_id == playlist_id).order_by(PlaylistTrack.position).all()

    all_tracks = Track.query.filter_by(is_active=True).all()

    total_duration = sum([track[0].duration for track in current_tracks])

    return render_template('playlist_manage.html',
                         playlist=playlist,
                         current_tracks=current_tracks,
                         all_tracks=all_tracks,
                         total_duration=total_duration)

@app.route('/admin/playlists/<int:playlist_id>/add-track', methods=['POST'])
@login_required
def add_track_to_playlist(playlist_id):
    track_id = request.form.get('track_id')
    
    # Calcular la siguiente posición
    last_pos = db.session.query(db.func.max(PlaylistTrack.position)).filter_by(playlist_id=playlist_id).scalar() or 0
    
    new_rel = PlaylistTrack(
        playlist_id=playlist_id,
        track_id=track_id,
        position=last_pos + 1
    )
    db.session.add(new_rel)
    db.session.commit()
    
    flash('Canción añadida a la playlist', 'success')
    return redirect(url_for('manage_playlist', playlist_id=playlist_id))

@app.route('/admin/playlists/<int:playlist_id>/remove-track/<int:track_id>', methods=['POST'])
@login_required
def remove_track_from_playlist(playlist_id, track_id):
    PlaylistTrack.query.filter_by(
        playlist_id=playlist_id, 
        track_id=track_id
    ).delete()
    db.session.commit()
    
    flash('Canción removida de la playlist', 'success')
    return redirect(url_for('manage_playlist', playlist_id=playlist_id))

if __name__ == '__main__':
    app.run(debug=True)