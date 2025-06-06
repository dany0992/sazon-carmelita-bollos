from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, make_response
from models import db, InventarioBollos, VentasBollos, MovimientosInventario, DistribucionGanancias
from datetime import datetime, date, timedelta
from sqlalchemy import func, case, and_
import webbrowser
import threading
from uuid import uuid4
from collections import defaultdict
import os
import subprocess
from fpdf import FPDF
from io import BytesIO
from xhtml2pdf import pisa
import io
import pytz

app = Flask(__name__)
# Detectar si está corriendo en Render
if os.environ.get('RENDER', '').lower() == 'true':
    # Conexión en línea (Render)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://punto_venta_bwhe_user:U8cjidADjeuWDOLLp6F3Js7gkWCHPIlC@dpg-d0r4vqbe5dus73fkb280-a.oregon-postgres.render.com/punto_venta_bwhe'
else:
    # Conexión local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://punto_venta_bwhe_user:U8cjidADjeuWDOLLp6F3Js7gkWCHPIlC@dpg-d0r4vqbe5dus73fkb280-a.oregon-postgres.render.com/punto_venta_bwhe'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def fecha_monterrey():
    return datetime.now(pytz.timezone('America/Monterrey'))

# ------------------------------
# RUTA: INICIO
# ------------------------------
@app.route('/')
def inicio():
    return render_template('inicio.html')

# ------------------------------
# RUTA: VENTAS (con visualización de inventario)
# ------------------------------
@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    vendedora = "Mary"

    precios = {
        "Plátano": 15, "Fresa": 15, "Mango": 15, "Coco": 15,
        "Chocolate": 15, "Nuez": 17, "Pay de Limón": 17, "Mangonada": 17
    }

    personajes = {
        "Plátano": "Platamelita.png",
        "Fresa": "Fresmelita.png",
        "Mango": "Manguelito.png",
        "Coco": "Carmeloco.png",
        "Chocolate": "Chocomelito.png",
        "Nuez": "Nuelito.png",
        "Pay de Limón": "Paymelito.png",
        "Mangonada": "mangonada.jpg"
    }

    if request.method == 'POST':
        sabor = request.form['sabor']
        venta = VentasBollos(
            vendedora=vendedora,
            sabor=sabor,
            fecha_venta=datetime.now(),
            grupo_venta=str(uuid4())
        )
        db.session.add(venta)

        item = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=sabor).first()
        if item and item.cantidad_actual > 0:
            item.cantidad_actual -= 1
        db.session.commit()
        return redirect('/ventas')

    inventario = {
        item.sabor: item.cantidad_actual
        for item in InventarioBollos.query.filter_by(vendedora=vendedora).all()
    }

    return render_template('ventas.html', inventario=inventario, personajes=personajes, precios=precios)

# ------------------------------
# RUTA: REGISTRAR VENTA (AJAX)
# ------------------------------
@app.route('/registrar_venta', methods=['POST'])
def registrar_venta():
    data = request.get_json()
    vendedora = "Mary"
    grupo_id = str(uuid4())

    try:
        for sabor, cantidad in data.items():
            for _ in range(cantidad):
                venta = VentasBollos(
                    vendedora=vendedora,
                    sabor=sabor,
                    fecha_venta=fecha_monterrey(),
                    grupo_venta=grupo_id
                )
                db.session.add(venta)

                item = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=sabor).first()

                if item:
                    if item.cantidad_actual > 0:
                        item.cantidad_actual -= 1
                    else:
                        print(f"⚠️ Sin inventario para {sabor}", flush=True)
                    movimiento = MovimientosInventario(
                        vendedora=vendedora,
                        sabor=sabor,
                        tipo='salida',
                        cantidad=1,
                        motivo='Venta AJAX'
                    )
                    db.session.add(movimiento)
                else:
                    print(f"❌ ERROR: No se encontró '{sabor}' en inventario", flush=True)
                    raise Exception(f"Sabor '{sabor}' no encontrado en inventario.")

        db.session.commit()

        inventario_actual = {
            item.sabor: item.cantidad_actual
            for item in InventarioBollos.query.filter_by(vendedora=vendedora).all()
        }

        return jsonify({"mensaje": "Ventas registradas correctamente.", "inventario": inventario_actual}), 200

    except Exception as e:
        print("ERROR:", e, flush=True)
        db.session.rollback()
        return jsonify({"error": "No se pudo registrar la venta."}), 500

# ------------------------------
# RUTA: CORTE DEL DÍA
# ------------------------------
@app.route('/resumen_ventas')
def resumen_ventas():
    from datetime import timedelta
    vendedora = "Mary"
    hoy = date.today()

    sabores = [
        {"nombre": "Plátano", "precio": 15},
        {"nombre": "Fresa", "precio": 15},
        {"nombre": "Mango", "precio": 15},
        {"nombre": "Coco", "precio": 15},
        {"nombre": "Chocolate", "precio": 15},
        {"nombre": "Nuez", "precio": 17},
        {"nombre": "Pay de Limón", "precio": 17},
        {"nombre": "Mangonada", "precio": 17},
    ]

    # Semana actual
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    resumen = []
    total_vendidos = 0
    total_ingresos = 0
    ventas_por_sabor = {}
    sabores_sin_ventas = []
    sabores_bajo_inventario = []

    for s in sabores:
        nombre = s["nombre"]
        precio = s["precio"]

        vendidos = db.session.query(func.count(VentasBollos.id)).filter(
            VentasBollos.vendedora == vendedora,
            VentasBollos.sabor == nombre,
            func.date(VentasBollos.fecha_venta).between(lunes, domingo)
        ).scalar() or 0

        ingresos = vendidos * precio
        total_vendidos += vendidos
        total_ingresos += ingresos

        ventas_por_sabor[nombre] = vendidos

        inventario = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=nombre).first()
        cantidad_restante = inventario.cantidad_actual if inventario else 0

        if vendidos == 0:
            sabores_sin_ventas.append(nombre)

        if cantidad_restante <= 3:
            sabores_bajo_inventario.append({
                "sabor": nombre,
                "restantes": cantidad_restante
            })

        resumen.append({
            "sabor": nombre,
            "vendidos": vendidos,
            "ingresos": ingresos,
            "precio": precio,
            "restantes": cantidad_restante
        })

    resumen_ordenado = sorted(resumen, key=lambda x: x["vendidos"], reverse=True)
    top_sabores = resumen_ordenado[:5]

    top_sabores_nombres = [s["sabor"] for s in top_sabores]
    top_sabores_valores = [s["vendidos"] for s in top_sabores]

    # Historial acumulado
    historial = db.session.query(VentasBollos).filter_by(vendedora=vendedora).all()
    ventas_historial = {}
    for v in historial:
        fecha = v.fecha_venta.date()
        semana = (fecha - timedelta(days=fecha.weekday()), fecha + timedelta(days=(6 - fecha.weekday())))
        if semana not in ventas_historial:
            ventas_historial[semana] = {"total": 0, "detalles": {}}
        ventas_historial[semana]["total"] += 17 if v.sabor in ["Nuez", "Pay de Limón"] else 15
        if v.sabor not in ventas_historial[semana]["detalles"]:
            ventas_historial[semana]["detalles"][v.sabor] = 0
        ventas_historial[semana]["detalles"][v.sabor] += 1

    historial_resumen = []
    for semana, data in sorted(ventas_historial.items(), key=lambda x: x[0], reverse=True):
        inicio, fin = semana
        historial_resumen.append({
            "semana": f"{inicio.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}",
            "total": data["total"],
            "detalles": data["detalles"]
        })

    return render_template(
        'resumen_ventas.html',
        fecha=f"{lunes.strftime('%d/%m/%Y')} - {domingo.strftime('%d/%m/%Y')}",
        vendedora=vendedora,
        total_vendidos=total_vendidos,
        total_ingresos=total_ingresos,
        resumen=resumen,
        top_sabores=top_sabores,
        sabores_no_vendidos=sabores_sin_ventas,
        inventario_bajo=sabores_bajo_inventario,
        top_sabores_nombres=top_sabores_nombres,
        top_sabores_valores=top_sabores_valores,
        historial_resumen=historial_resumen
    )

# ------------------------------
# RUTA: HISTORIAL DE VENTAS AGRUPADAS
# ------------------------------
@app.route('/historial_ventas')
def historial_ventas():
    from pytz import timezone
    zona_monterrey = timezone('America/Monterrey')

    ventas = VentasBollos.query.order_by(VentasBollos.fecha_venta.desc()).all()

    agrupado = defaultdict(list)
    resumen_sabores = defaultdict(int)
    total_general = 0

    for venta in ventas:
        agrupado[venta.grupo_venta].append(venta)
        resumen_sabores[venta.sabor] += 1
        total_general += 17 if venta.sabor in ['Nuez', 'Pay de Limón'] else 15

    grupos = []

    for grupo_id, lista in agrupado.items():
        if not lista:
            continue  # Previene errores si la lista está vacía

        ventas_detalle = []
        total = 0
        for v in lista:
            ventas_detalle.append({"id": v.id, "sabor": v.sabor})
            total += 17 if v.sabor in ['Nuez', 'Pay de Limón'] else 15

        # Asegurar que la fecha tenga zona UTC antes de convertirla
        fecha_venta = lista[0].fecha_venta
        if fecha_venta.tzinfo is None:
            fecha_venta = fecha_venta.replace(tzinfo=pytz.utc)

        fecha_local = fecha_venta.astimezone(zona_monterrey)

        grupos.append({
            "grupo": grupo_id,
            "fecha": fecha_local.strftime('%Y-%m-%d %H:%M'),
            "ventas": ventas_detalle,
            "total": total,
            "vendedora": lista[0].vendedora
        })

    return render_template('historial_ventas.html',
                           grupos=grupos,
                           resumen_sabores=resumen_sabores,
                           total_general=total_general)

# ------------------------------
# RUTAS DE EDICIÓN Y ELIMINACIÓN
# ------------------------------
@app.route('/editar_venta/<int:id>', methods=['POST'])
def editar_venta(id):
    nueva_sabor = request.json.get('sabor')
    venta = VentasBollos.query.get(id)
    if venta:
        venta.sabor = nueva_sabor
        db.session.commit()
        return jsonify({"mensaje": "Venta actualizada"}), 200
    return jsonify({"error": "Venta no encontrada"}), 404

@app.route('/eliminar_venta/<int:id>', methods=['POST'])
def eliminar_venta(id):
    venta = VentasBollos.query.get(id)
    if venta:
        item = InventarioBollos.query.filter_by(vendedora=venta.vendedora, sabor=venta.sabor).first()
        if item:
            item.cantidad_actual += 1
        db.session.delete(venta)
        db.session.commit()
        return jsonify({"mensaje": "Venta eliminada"}), 200
    return jsonify({"error": "Venta no encontrada"}), 404

@app.route('/editar_grupo_venta/<grupo_id>', methods=['POST'])
def editar_grupo_venta(grupo_id):
    data = request.get_json()
    vendedora = "Mary"

    ventas_existentes = VentasBollos.query.filter_by(grupo_venta=grupo_id).all()
    for venta in ventas_existentes:
        item = InventarioBollos.query.filter_by(vendedora=venta.vendedora, sabor=venta.sabor).first()
        if item:
            item.cantidad_actual += 1
        db.session.delete(venta)

    try:
        for sabor, cantidad in data.items():
            for _ in range(cantidad):
                nueva_venta = VentasBollos(
                    vendedora=vendedora,
                    sabor=sabor,
                    fecha_venta=datetime.now(),
                    grupo_venta=grupo_id
                )
                db.session.add(nueva_venta)

                item = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=sabor).first()
                if item and item.cantidad_actual > 0:
                    item.cantidad_actual -= 1

        db.session.commit()
        return jsonify({"mensaje": "Grupo de venta actualizado"}), 200

    except Exception as e:
        db.session.rollback()
        print("ERROR al editar grupo:", e)
        return jsonify({"error": "No se pudo editar el grupo de venta"}), 500

@app.route('/eliminar_grupo_venta/<grupo_id>', methods=['POST'])
def eliminar_grupo_venta(grupo_id):
    ventas = VentasBollos.query.filter_by(grupo_venta=grupo_id).all()
    if ventas:
        for venta in ventas:
            item = InventarioBollos.query.filter_by(vendedora=venta.vendedora, sabor=venta.sabor).first()
            if item:
                item.cantidad_actual += 1
            db.session.delete(venta)
        db.session.commit()
        return jsonify({"mensaje": "Grupo de venta eliminado"}), 200
    return jsonify({"error": "Grupo no encontrado"}), 404

# ------------------------------
# INVENTARIO INICIAL Y ACTUALIZACIÓN
# ------------------------------
def registrar_inventario_inicial():
    inventario_inicial = {
        "Plátano": 5,
        "Mango": 5,
        "Fresa": 5,
        "Coco": 5,
        "Nuez": 5,
        "Chocolate": 4,
        "Pay de Limón": 4,
        "Mangonada": 5
    }
    for sabor, cantidad in inventario_inicial.items():
        existente = InventarioBollos.query.filter_by(vendedora="Mary", sabor=sabor).first()
        if not existente:
            nuevo = InventarioBollos(
                vendedora="Mary",
                sabor=sabor,
                cantidad_actual=cantidad,
                fecha_asignacion=date.today()
            )
            db.session.add(nuevo)
    db.session.commit()

from pytz import timezone

@app.route('/inventario', methods=['GET', 'POST'])
def inventario():
    from datetime import date
    import pytz

    vendedora = "Mary"
    mensaje = None
    sabores = ["Plátano", "Fresa", "Mango", "Coco", "Chocolate", "Nuez", "Pay de Limón", "Mangonada"]

    if request.method == 'POST':
        for sabor in sabores:
            cantidad_nueva = request.form.get(sabor)
            if cantidad_nueva is not None:
                cantidad_nueva = int(cantidad_nueva)
                item = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=sabor).first()

                if item:
                    diferencia = cantidad_nueva - item.cantidad_actual
                    if diferencia != 0:
                        movimiento = MovimientosInventario(
                            vendedora=vendedora,
                            sabor=sabor,
                            tipo='ajuste',
                            cantidad=abs(diferencia),
                            motivo=f"Ajuste manual: de {item.cantidad_actual} a {cantidad_nueva}"
                        )
                        db.session.add(movimiento)
                        item.cantidad_actual = cantidad_nueva
                else:
                    nuevo = InventarioBollos(
                        vendedora=vendedora,
                        sabor=sabor,
                        cantidad_actual=cantidad_nueva,
                        fecha_asignacion=date.today()
                    )
                    db.session.add(nuevo)
                    movimiento = MovimientosInventario(
                        vendedora=vendedora,
                        sabor=sabor,
                        tipo='ajuste',
                        cantidad=cantidad_nueva,
                        motivo="Nuevo sabor agregado al inventario"
                    )
                    db.session.add(movimiento)

        db.session.commit()
        mensaje = "✅ Inventario actualizado correctamente."

    inventario = {
        item.sabor: item.cantidad_actual
        for item in InventarioBollos.query.filter_by(vendedora=vendedora).all()
    }

    # ✅ Formatear historial con hora local de Monterrey
    zona_monterrey = pytz.timezone('America/Monterrey')
    historial_raw = MovimientosInventario.query.filter_by(vendedora=vendedora).order_by(
        MovimientosInventario.fecha_movimiento.desc()
    ).all()

    historial = []
    for mov in historial_raw:
        fecha = mov.fecha_movimiento
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=pytz.utc)
        fecha_local = fecha.astimezone(zona_monterrey)

        historial.append({
            "id": mov.id,
            "fecha": fecha_local.strftime('%d/%m/%Y %H:%M'),
            "sabor": mov.sabor,
            "tipo": mov.tipo,
            "cantidad": mov.cantidad,
            "motivo": mov.motivo
        })

    return render_template(
        'inventario.html',
        sabores=sabores,
        inventario=inventario,
        historial=historial,
        mensaje=mensaje
    )

@app.route('/editar_movimiento/<int:id>', methods=['POST'])
def editar_movimiento(id):
    data = request.get_json()
    movimiento = MovimientosInventario.query.get(id)
    if movimiento:
        movimiento.motivo = data.get('motivo')
        movimiento.cantidad = int(data.get('cantidad'))
        db.session.commit()
        return jsonify({"mensaje": "Movimiento actualizado correctamente"})
    return jsonify({"error": "Movimiento no encontrado"}), 404

@app.route('/eliminar_movimiento/<int:id>', methods=['POST'])
def eliminar_movimiento(id):
    movimiento = MovimientosInventario.query.get(id)
    if movimiento:
        db.session.delete(movimiento)
        db.session.commit()
        return jsonify({"mensaje": "Movimiento eliminado correctamente"})
    return jsonify({"error": "Movimiento no encontrado"}), 404

@app.route('/respaldo_db')
def respaldo_db():
    if os.environ.get('RENDER', '').lower() == 'true':
        # Ruta para PostgreSQL (Render)
        archivo = "/tmp/respaldo_bollos.sql"
        comando = [
            "pg_dump",
            "--dbname=" + app.config['SQLALCHEMY_DATABASE_URI'],
            "--file=" + archivo
        ]
        try:
            subprocess.run(comando, check=True)
            return send_file(archivo, as_attachment=True)
        except Exception as e:
            return f"❌ Error al respaldar la base de datos en Render: {e}", 500
    else:
        # Ruta para SQLite (local)
        return send_file("bollos.db", as_attachment=True)

@app.route('/ganancias', methods=['GET', 'POST'])
def ganancias():
    mensaje = None
    hoy = date.today()
    porcentaje_banco = 10  # valor por defecto inicial

    if request.method == 'POST':
        try:
            # Validación segura del porcentaje ingresado
            porcentaje_banco = int(request.form.get('porcentaje_banco', 10))
            if porcentaje_banco < 0 or porcentaje_banco > 100:
                raise ValueError("El porcentaje debe estar entre 0 y 100.")

            # Evita doble registro en la misma fecha
            distribucion_existente = DistribucionGanancias.query.filter_by(fecha_distribucion=hoy).first()
            if distribucion_existente:
                mensaje = "⚠️ Ya se ha realizado una distribución de ganancias hoy."
            else:
                # Cálculo del total de ventas
                total_ventas = db.session.query(func.sum(
                    case(
                        [(VentasBollos.sabor.in_(['Nuez', 'Pay de Limón', 'Mangonada']), 17)],
                        else_=15
                    )
                )).scalar() or 0

                if total_ventas == 0:
                    mensaje = "⚠️ No hay ventas registradas para distribuir."
                else:
                    monto_banco = round(total_ventas * (porcentaje_banco / 100), 2)
                    monto_disponible = total_ventas - monto_banco
                    monto_carmen = round(monto_disponible / 2, 2)
                    monto_mary = round(monto_disponible / 2, 2)

                    nueva_distribucion = DistribucionGanancias(
                        total_ventas=total_ventas,
                        porcentaje_banco=porcentaje_banco,
                        monto_banco=monto_banco,
                        monto_a_dividir=monto_disponible,
                        monto_carmen=monto_carmen,
                        monto_mary=monto_mary,
                        fecha_distribucion=hoy,
                        observaciones=request.form.get('observaciones', '')
                    )

                    db.session.add(nueva_distribucion)
                    db.session.commit()
                    mensaje = "✅ Ganancias distribuidas correctamente."

        except ValueError as ve:
            mensaje = f"❌ Error en porcentaje: {ve}"
        except Exception as e:
            db.session.rollback()
            mensaje = f"❌ Error inesperado: {str(e)}"

    # Filtros para historial (GET)
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    buscar = request.args.get('buscar')

    filtros = []
    if desde:
        filtros.append(DistribucionGanancias.fecha_distribucion >= desde)
    if hasta:
        filtros.append(DistribucionGanancias.fecha_distribucion <= hasta)
    if buscar:
        filtros.append(DistribucionGanancias.observaciones.ilike(f"%{buscar}%"))

    historial = DistribucionGanancias.query.filter(and_(*filtros)).order_by(
        DistribucionGanancias.fecha_distribucion.desc()
    ).all()

    return render_template(
        'ganancias.html',
        porcentaje_banco=porcentaje_banco,
        mensaje=mensaje,
        historial=historial
    )

@app.route('/exportar_ganancias_pdf')
def exportar_ganancias_pdf():
    distribuciones = DistribucionGanancias.query.order_by(DistribucionGanancias.fecha_distribucion.desc()).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(64, 32, 0)
    pdf.cell(0, 10, "Historial de Distribución de Ganancias", 0, 1, "C")

    pdf.set_font("Arial", size=10)
    pdf.set_text_color(0, 0, 0)

    pdf.ln(4)
    headers = ["Fecha", "Total", "Banco", "Dividir", "Carmen", "Mary", "Obs."]
    col_widths = [23, 25, 20, 22, 25, 25, 40]

    for i, h in enumerate(headers):
        pdf.set_fill_color(255, 204, 153)
        pdf.cell(col_widths[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()

    for d in distribuciones:
        fila = [
            d.fecha_distribucion.strftime('%d/%m/%Y'),
            f"${d.total_ventas:.2f}",
            f"${d.monto_banco:.2f}",
            f"${d.monto_a_dividir:.2f}",
            f"${d.monto_carmen:.2f}",
            f"${d.monto_mary:.2f}",
            d.observaciones[:25] if d.observaciones else ""
        ]
        for i, texto in enumerate(fila):
            pdf.cell(col_widths[i], 7, texto, 1)
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    return send_file(buffer, as_attachment=True, download_name=f"distribucion_ganancias_{fecha_actual}.pdf", mimetype='application/pdf')

@app.route('/exportar_resumen_ventas_pdf')
def exportar_resumen_ventas_pdf():
    vendedora = "Mary"
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    sabores = [
        {"nombre": "Plátano", "precio": 15},
        {"nombre": "Fresa", "precio": 15},
        {"nombre": "Mango", "precio": 15},
        {"nombre": "Coco", "precio": 15},
        {"nombre": "Chocolate", "precio": 15},
        {"nombre": "Nuez", "precio": 17},
        {"nombre": "Pay de Limón", "precio": 17},
        {"nombre": "Mangonada", "precio": 17},
    ]

    resumen = []
    total_vendidos = 0
    total_ingresos = 0
    sabores_no_vendidos = []
    inventario_bajo = []

    for s in sabores:
        nombre = s["nombre"]
        precio = s["precio"]

        vendidos = db.session.query(func.count(VentasBollos.id)).filter(
            VentasBollos.vendedora == vendedora,
            VentasBollos.sabor == nombre,
            func.date(VentasBollos.fecha_venta).between(lunes, domingo)
        ).scalar() or 0

        ingresos = vendidos * precio
        total_vendidos += vendidos
        total_ingresos += ingresos

        resumen.append({
            "sabor": nombre,
            "vendidos": vendidos,
            "precio": precio,
            "ingresos": ingresos
        })

        if vendidos == 0:
            sabores_no_vendidos.append(nombre)

        inventario = InventarioBollos.query.filter_by(vendedora=vendedora, sabor=nombre).first()
        cantidad = inventario.cantidad_actual if inventario else 0
        if cantidad <= 3:
            inventario_bajo.append({"sabor": nombre, "restantes": cantidad})

    # Historial
    historial_raw = DistribucionGanancias.query.order_by(DistribucionGanancias.fecha_distribucion).all()
    historial_semanal = []
    for h in historial_raw:
        inicio_semana = h.fecha_distribucion - timedelta(days=h.fecha_distribucion.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        historial_semanal.append({
            "rango": f"{inicio_semana.strftime('%d/%m/%Y')} - {fin_semana.strftime('%d/%m/%Y')}",
            "vendidos": h.total_ventas // 15,  # aproximado
            "ingresos": h.total_ventas,
            "carmen": h.monto_carmen,
            "mary": h.monto_mary,
            "banco": h.monto_banco
        })

    html = render_template("resumen_ventas_pdf.html",
                           resumen=resumen,
                           total_vendidos=total_vendidos,
                           total_ingresos=total_ingresos,
                           fecha=f"{lunes.strftime('%d/%m/%Y')} - {domingo.strftime('%d/%m/%Y')}",
                           top_sabores=sorted(resumen, key=lambda x: x['vendidos'], reverse=True)[:5],
                           sabores_no_vendidos=sabores_no_vendidos,
                           inventario_bajo=inventario_bajo,
                           historial_semanal=historial_semanal
    )

    # Convertir HTML a PDF
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result)

    if pisa_status.err:
        return "❌ Error al generar el PDF", 500

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=resumen_ventas.pdf'
    return response

if __name__ == '__main__':
    with app.app_context():
        if os.environ.get('RENDER') == 'true':
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tablas_existentes = inspector.get_table_names()
            if not tablas_existentes:
                db.create_all()
                registrar_inventario_inicial()
                print("✅ Tablas creadas automáticamente en Render.")
    app.run(debug=True)