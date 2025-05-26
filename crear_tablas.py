from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from models import db, InventarioBollos, DistribucionGanancias  # ✅ Se agregó esta línea

app = Flask(__name__)

# Configurar conexión a PostgreSQL (Render)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bollos_db_user:tflh1x1YH3bepUYhEfLAHNK1V3LUgQIu@dpg-d0naalpr0fns738q6h30-a.oregon-postgres.render.com/bollos_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Inicializar inventario si no existe
def registrar_inventario_inicial():
    inventario_inicial = {
        "Plátano": 5, "Mango": 5, "Fresa": 5,
        "Coco": 5, "Nuez": 5, "Chocolate": 4,
        "Pay de Limón": 4
    }
    for sabor, cantidad in inventario_inicial.items():
        existente = InventarioBollos.query.filter_by(vendedora="Mary", sabor=sabor).first()
        if not existente:
            nuevo = InventarioBollos(
                vendedora="Mary",
                sabor=sabor,
                cantidad_actual=cantidad
            )
            db.session.add(nuevo)
    db.session.commit()

with app.app_context():
    db.create_all()
    registrar_inventario_inicial()
    print("✅ Tablas creadas correctamente en Render.")