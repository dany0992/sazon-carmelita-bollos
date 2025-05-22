from app import db, app, registrar_inventario_inicial

with app.app_context():
    db.create_all()
    registrar_inventario_inicial()
    print("✅ Tablas creadas correctamente.")