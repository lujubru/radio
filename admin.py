from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Buscamos si ya existe el usuario
    admin = User.query.filter_by(username='admin').first()
    
    if admin:
        print("Actualizando contraseña de admin existente...")
        admin.password_hash = generate_password_hash('admin123')
        admin.is_active = True
    else:
        print("Creando nuevo usuario administrador...")
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            email='admin@radio.com',
            is_active=True
        )
        db.session.add(admin)
    
    db.session.commit()
    print("¡Usuario admin configurado con éxito!")
    print("Username: admin")
    print("Password: admin123")