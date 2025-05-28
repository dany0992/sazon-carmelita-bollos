from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.dialects.postgresql import ENUM
from datetime import datetime
import pytz

db = SQLAlchemy()

def fecha_monterrey():
    return datetime.now(pytz.timezone('America/Monterrey'))

# -----------------------------
# 📦 Inventario actual por vendedora y sabor
# -----------------------------
class InventarioBollos(db.Model):
    __tablename__ = 'inventario_bollos'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)
    sabor = Column(String(50), nullable=False)
    cantidad_actual = Column(Integer, default=0)
    fecha_asignacion = Column(Date, nullable=False, default=lambda: fecha_monterrey().date())

# -----------------------------
# 🧾 Registro individual de ventas por bollo
# -----------------------------
class VentasBollos(db.Model):
    __tablename__ = 'ventas_bollos'

    id = Column(Integer, primary_key=True)
    sabor = Column(String(50), nullable=False)
    vendedora = Column(String(50), nullable=False)
    fecha_venta = Column(DateTime, nullable=False, default=fecha_monterrey)
    grupo_venta = Column(String(100), nullable=True)

# -----------------------------
# 📋 Historial completo de movimientos de inventario
# -----------------------------
class MovimientosInventario(db.Model):
    __tablename__ = 'movimientos_inventario'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)
    sabor = Column(String(50), nullable=False)
    tipo = Column(ENUM('entrada', 'salida', 'ajuste', name='tipo_movimiento', create_type=True), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(200), nullable=True)
    fecha_movimiento = Column(DateTime, default=fecha_monterrey)

# -----------------------------
# 💰 Historial de distribución de ganancias
# -----------------------------
class DistribucionGanancias(db.Model):
    __tablename__ = 'distribucion_ganancias'

    id = db.Column(db.Integer, primary_key=True)
    fecha_distribucion = db.Column(db.Date, nullable=False)
    total_ventas = db.Column(db.Float, nullable=False)
    porcentaje_banco = db.Column(db.Float, nullable=False)
    monto_banco = db.Column(db.Float, nullable=False)
    monto_a_dividir = db.Column(db.Float, nullable=False)  # <- renombrado aquí
    monto_carmen = db.Column(db.Float, nullable=False)
    monto_mary = db.Column(db.Float, nullable=False)
    observaciones = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Distribucion {self.fecha_distribucion} - Total: ${self.total_ventas}>"