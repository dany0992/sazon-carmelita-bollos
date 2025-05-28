from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from models import db, InventarioBollos, MovimientosInventario, DistribucionGanancias

app = Flask(__name__)

# Conexión a la base de datos en Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://punto_venta_bwhe_user:U8cjidADjeuWDOLLp6F3Js7gkWCHPIlC@dpg-d0r4vqbe5dus73fkb280-a.oregon-postgres.render.com/punto_venta_bwhe?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def registrar_inventario_inicial():
    inventario_inicial = {
        "Plátano": 5, "Mango": 5, "Fresa": 5,
        "Coco": 5, "Nuez": 5, "Chocolate": 4,
        "Pay de Limón": 4, "Mangonada": 0
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

def agregar_columna_monto_a_dividir():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE distribucion_ganancias
                ADD COLUMN IF NOT EXISTS monto_a_dividir FLOAT DEFAULT 0;
            """))
            print("✅ Columna 'monto_a_dividir' agregada o ya existente.")
    except Exception as e:
        print("❌ Error al modificar la tabla:", e)

with app.app_context():
    db.create_all()
    agregar_columna_monto_a_dividir()
    registrar_inventario_inicial()
    print("✅ Tablas verificadas y datos iniciales aplicados.")