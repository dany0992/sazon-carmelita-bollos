from app import db
from app import registrar_inventario_inicial

db.create_all()
registrar_inventario_inicial()
print("✅ Tablas creadas correctamente en la base de datos.")