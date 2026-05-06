from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import sqlite3
import hashlib
from datetime import datetime
import re
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

# Crear la aplicación Flask
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_12345'

IVA = 0.19  # 19% de IVA

def hash_password(password):
    """Encriptar contraseña de manera simple"""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_email(email):
    """Verificar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email)

def conectar_db():
    """Conectar a la base de datos"""
    return sqlite3.connect('helpTech.db')

def generar_numero_factura():
    """Generar número de factura automático"""
    año = datetime.now().strftime("%Y")
    mes = datetime.now().strftime("%m")
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM facturas")
    count = cursor.fetchone()[0] + 1
    conn.close()
    
    return f"FAC-{año}{mes}-{count:04d}"

# ============ RUTAS PRINCIPALES ============
@app.route('/')
def index():
    return render_template('index.html')

# ============ USUARIOS ============
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    error = None
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if not nombre or not email or not password:
            error = "Todos los campos son obligatorios"
        elif not verificar_email(email):
            error = "El formato del email no es válido"
        elif len(password) < 6:
            error = "La contraseña debe tener al menos 6 caracteres"
        elif password != confirm_password:
            error = "Las contraseñas no coinciden"
        else:
            try:
                conn = conectar_db()
                cursor = conn.cursor()
                
                cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
                if cursor.fetchone():
                    error = "Este email ya está registrado"
                else:
                    password_hash = hash_password(password)
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cursor.execute('''
                        INSERT INTO usuarios (nombre, email, password, fecha_registro)
                        VALUES (?, ?, ?, ?)
                    ''', (nombre, email, password_hash, fecha))
                    
                    conn.commit()
                    conn.close()
                    return redirect(url_for('login', mensaje="Registro exitoso. Ahora inicia sesión."))
                    
            except Exception as e:
                error = f"Error al registrar: {str(e)}"
            finally:
                conn.close()
    
    return render_template('registro.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    mensaje = request.args.get('mensaje')
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email or not password:
            error = "Todos los campos son obligatorios"
        else:
            try:
                conn = conectar_db()
                cursor = conn.cursor()
                
                password_hash = hash_password(password)
                cursor.execute('''
                    SELECT id, nombre, email FROM usuarios 
                    WHERE email = ? AND password = ?
                ''', (email, password_hash))
                
                usuario = cursor.fetchone()
                conn.close()
                
                if usuario:
                    session['usuario_id'] = usuario[0]
                    session['usuario_nombre'] = usuario[1]
                    session['usuario_email'] = usuario[2]
                    return redirect(url_for('dashboard'))
                else:
                    error = "Email o contraseña incorrectos"
                    
            except Exception as e:
                error = f"Error al iniciar sesión: {str(e)}"
    
    return render_template('login.html', error=error, mensaje=mensaje)

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    try:
        # Contar clientes
        cursor.execute("SELECT COUNT(*) FROM clientes WHERE usuario_id = ?", (session['usuario_id'],))
        total_clientes = cursor.fetchone()[0]
        
        # Contar productos
        cursor.execute("SELECT COUNT(*) FROM productos WHERE usuario_id = ?", (session['usuario_id'],))
        total_productos = cursor.fetchone()[0]
        
        # Contar facturas
        cursor.execute("SELECT COUNT(*) FROM facturas WHERE usuario_id = ?", (session['usuario_id'],))
        total_facturas = cursor.fetchone()[0]
        
        # Calcular ingresos totales
        try:
            cursor.execute("SELECT SUM(total) FROM facturas WHERE usuario_id = ?", (session['usuario_id'],))
            resultado = cursor.fetchone()[0]
            total_ingresos = resultado if resultado is not None else 0
        except:
            total_ingresos = 0
            
    except Exception as e:
        print(f"Error en dashboard: {e}")
        total_clientes = 0
        total_productos = 0
        total_facturas = 0
        total_ingresos = 0
    finally:
        conn.close()
    
    usuario = {
        'nombre': session['usuario_nombre'],
        'email': session['usuario_email']
    }
    
    return render_template('dashboard.html', usuario=usuario, 
                         total_clientes=total_clientes,
                         total_productos=total_productos,
                         total_facturas=total_facturas,
                         total_ingresos=total_ingresos)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============ CLIENTES ============
@app.route('/clientes')
def listar_clientes():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nombre, email, telefono, documento, fecha_registro 
        FROM clientes 
        WHERE usuario_id = ? 
        ORDER BY id DESC
    ''', (session['usuario_id'],))
    clientes = cursor.fetchall()
    conn.close()
    
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    error = None
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        documento = request.form['documento']
        
        if not nombre:
            error = "El nombre del cliente es obligatorio"
        else:
            try:
                conn = conectar_db()
                cursor = conn.cursor()
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute('''
                    INSERT INTO clientes (usuario_id, nombre, email, telefono, direccion, documento, fecha_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session['usuario_id'], nombre, email, telefono, direccion, documento, fecha))
                
                conn.commit()
                conn.close()
                return redirect(url_for('listar_clientes'))
                
            except Exception as e:
                error = f"Error al crear cliente: {str(e)}"
    
    return render_template('cliente_form.html', error=error, titulo="Nuevo Cliente")

@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        documento = request.form['documento']
        
        try:
            cursor.execute('''
                UPDATE clientes 
                SET nombre = ?, email = ?, telefono = ?, direccion = ?, documento = ?
                WHERE id = ? AND usuario_id = ?
            ''', (nombre, email, telefono, direccion, documento, id, session['usuario_id']))
            conn.commit()
            conn.close()
            return redirect(url_for('listar_clientes'))
        except Exception as e:
            conn.close()
            return f"Error: {str(e)}"
    
    cursor.execute('SELECT id, nombre, email, telefono, direccion, documento FROM clientes WHERE id = ? AND usuario_id = ?', 
                  (id, session['usuario_id']))
    cliente = cursor.fetchone()
    conn.close()
    
    if not cliente:
        return redirect(url_for('listar_clientes'))
    
    return render_template('cliente_form.html', cliente=cliente, titulo="Editar Cliente")

@app.route('/cliente/eliminar/<int:id>')
def eliminar_cliente(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clientes WHERE id = ? AND usuario_id = ?', (id, session['usuario_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for('listar_clientes'))

# ============ PRODUCTOS ============
@app.route('/productos')
def listar_productos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo, nombre, descripcion, precio, stock, categoria 
        FROM productos 
        WHERE usuario_id = ? 
        ORDER BY id DESC
    ''', (session['usuario_id'],))
    productos = cursor.fetchall()
    conn.close()
    
    return render_template('productos.html', productos=productos)

@app.route('/producto/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    error = None
    
    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        categoria = request.form['categoria']
        
        if not nombre or not precio:
            error = "Nombre y precio son obligatorios"
        else:
            try:
                precio = float(precio)
                stock = int(stock) if stock else 0
                
                conn = conectar_db()
                cursor = conn.cursor()
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute('''
                    INSERT INTO productos (usuario_id, codigo, nombre, descripcion, precio, stock, categoria, fecha_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (session['usuario_id'], codigo, nombre, descripcion, precio, stock, categoria, fecha))
                
                conn.commit()
                conn.close()
                return redirect(url_for('listar_productos'))
                
            except Exception as e:
                error = f"Error al crear producto: {str(e)}"
    
    return render_template('producto_form.html', error=error, titulo="Nuevo Producto")

@app.route('/producto/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        categoria = request.form['categoria']
        
        try:
            precio = float(precio)
            stock = int(stock)
            
            cursor.execute('''
                UPDATE productos 
                SET codigo = ?, nombre = ?, descripcion = ?, precio = ?, stock = ?, categoria = ?
                WHERE id = ? AND usuario_id = ?
            ''', (codigo, nombre, descripcion, precio, stock, categoria, id, session['usuario_id']))
            conn.commit()
            conn.close()
            return redirect(url_for('listar_productos'))
        except Exception as e:
            conn.close()
            return f"Error: {str(e)}"
    
    cursor.execute('SELECT id, codigo, nombre, descripcion, precio, stock, categoria FROM productos WHERE id = ? AND usuario_id = ?', 
                  (id, session['usuario_id']))
    producto = cursor.fetchone()
    conn.close()
    
    if not producto:
        return redirect(url_for('listar_productos'))
    
    return render_template('producto_form.html', producto=producto, titulo="Editar Producto")

@app.route('/producto/eliminar/<int:id>')
def eliminar_producto(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id = ? AND usuario_id = ?', (id, session['usuario_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for('listar_productos'))

# ============ FACTURAS ============
@app.route('/facturas')
def listar_facturas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.id, f.numero_factura, c.nombre, f.fecha, f.subtotal, f.iva, f.total 
        FROM facturas f
        JOIN clientes c ON f.cliente_id = c.id
        WHERE f.usuario_id = ?
        ORDER BY f.id DESC
    ''', (session['usuario_id'],))
    facturas = cursor.fetchall()
    conn.close()
    
    return render_template('facturas.html', facturas=facturas)

@app.route('/factura/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        productos_json = request.form.get('productos', '[]')
        
        productos = json.loads(productos_json)
        
        if not cliente_id:
            return jsonify({'error': 'Seleccione un cliente'}), 400
        
        if not productos:
            return jsonify({'error': 'Agregue al menos un producto'}), 400
        
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            
            # Calcular totales
            subtotal = 0
            for item in productos:
                subtotal += item['precio'] * item['cantidad']
            
            iva_total = subtotal * IVA
            total = subtotal + iva_total
            
            # Generar número de factura
            numero_factura = generar_numero_factura()
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Insertar factura
            cursor.execute('''
                INSERT INTO facturas (usuario_id, numero_factura, cliente_id, fecha, subtotal, iva, total, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pagada')
            ''', (session['usuario_id'], numero_factura, cliente_id, fecha, subtotal, iva_total, total))
            
            factura_id = cursor.lastrowid
            
            # Insertar detalles y actualizar stock
            for item in productos:
                cursor.execute('''
                    INSERT INTO factura_detalles (factura_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                ''', (factura_id, item['id'], item['cantidad'], item['precio'], item['precio'] * item['cantidad']))
                
                # Actualizar stock
                cursor.execute('''
                    UPDATE productos SET stock = stock - ? WHERE id = ? AND usuario_id = ?
                ''', (item['cantidad'], item['id'], session['usuario_id']))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'factura_id': factura_id, 'numero_factura': numero_factura})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET - Mostrar formulario
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, nombre, documento FROM clientes WHERE usuario_id = ? ORDER BY nombre', (session['usuario_id'],))
    clientes = cursor.fetchall()
    
    cursor.execute('SELECT id, nombre, precio, stock FROM productos WHERE usuario_id = ? AND stock > 0 ORDER BY nombre', (session['usuario_id'],))
    productos = cursor.fetchall()
    
    conn.close()
    
    return render_template('factura_nueva.html', clientes=clientes, productos=productos, iva=IVA*100)

@app.route('/factura/ver/<int:id>')
def ver_factura(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Obtener datos de la factura
    cursor.execute('''
        SELECT f.id, f.numero_factura, c.nombre, c.documento, c.telefono, c.direccion, 
               f.fecha, f.subtotal, f.iva, f.total
        FROM facturas f
        JOIN clientes c ON f.cliente_id = c.id
        WHERE f.id = ? AND f.usuario_id = ?
    ''', (id, session['usuario_id']))
    
    factura = cursor.fetchone()
    
    if not factura:
        conn.close()
        return redirect(url_for('listar_facturas'))
    
    # Obtener detalles de la factura
    cursor.execute('''
        SELECT p.nombre, fd.cantidad, fd.precio_unitario, fd.subtotal
        FROM factura_detalles fd
        JOIN productos p ON fd.producto_id = p.id
        WHERE fd.factura_id = ?
    ''', (id,))
    
    detalles = cursor.fetchall()
    conn.close()
    
    return render_template('factura_ver.html', factura=factura, detalles=detalles, iva=IVA*100)

@app.route('/factura/pdf/<int:id>')
def factura_pdf(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Obtener datos de la factura
    cursor.execute('''
        SELECT f.id, f.numero_factura, c.nombre, c.documento, c.telefono, c.direccion, 
               f.fecha, f.subtotal, f.iva, f.total, u.nombre as empresa
        FROM facturas f
        JOIN clientes c ON f.cliente_id = c.id
        JOIN usuarios u ON f.usuario_id = u.id
        WHERE f.id = ? AND f.usuario_id = ?
    ''', (id, session['usuario_id']))
    
    factura = cursor.fetchone()
    
    if not factura:
        conn.close()
        return redirect(url_for('listar_facturas'))
    
    # Obtener detalles
    cursor.execute('''
        SELECT p.nombre, fd.cantidad, fd.precio_unitario, fd.subtotal
        FROM factura_detalles fd
        JOIN productos p ON fd.producto_id = p.id
        WHERE fd.factura_id = ?
    ''', (id,))
    
    detalles = cursor.fetchall()
    conn.close()
    
    # Generar PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#667eea'))
    normal_style = styles['Normal']
    
    elements = []
    
    # Encabezado
    elements.append(Paragraph("HELPTECH-F", title_style))
    elements.append(Paragraph("Sistema de Facturación Electrónica", styles['Heading3']))
    elements.append(Paragraph(f"Usuario: {factura[10]}", normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Información de la factura
    data_info = [
        ["NÚMERO DE FACTURA:", factura[1]],
        ["FECHA:", factura[6][:10]],
        ["HORA:", factura[6][11:16]]
    ]
    
    info_table = Table(data_info, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Información del cliente
    elements.append(Paragraph("<b>INFORMACIÓN DEL CLIENTE</b>", styles['Heading4']))
    data_cliente = [
        ["Nombre:", factura[2]],
        ["Documento:", factura[3] or "No especificado"],
        ["Teléfono:", factura[4] or "No especificado"],
        ["Dirección:", factura[5] or "No especificada"]
    ]
    
    cliente_table = Table(data_cliente, colWidths=[1.5*inch, 3.5*inch])
    cliente_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(cliente_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de productos
    elements.append(Paragraph("<b>DETALLE DE PRODUCTOS</b>", styles['Heading4']))
    
    table_data = [["CANT.", "PRODUCTO", "P. UNITARIO", "SUBTOTAL"]]
    for detalle in detalles:
        table_data.append([
            str(detalle[1]),
            detalle[0],
            f"${detalle[2]:,.2f}",
            f"${detalle[3]:,.2f}"
        ])
    
    product_table = Table(table_data, colWidths=[0.8*inch, 3*inch, 1.2*inch, 1.2*inch])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(product_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Totales
    data_totales = [
        ["SUBTOTAL:", f"${factura[7]:,.2f}"],
        [f"IVA ({IVA*100:.0f}%):", f"${factura[8]:,.2f}"],
        ["TOTAL A PAGAR:", f"${factura[9]:,.2f}"]
    ]
    
    totales_table = Table(data_totales, colWidths=[3*inch, 2*inch])
    totales_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, 2), (1, 2), colors.HexColor('#c33')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(totales_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Pie de página
    elements.append(Paragraph("Gracias por su compra", styles['Italic']))
    elements.append(Paragraph("Este documento es una factura de venta válida", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=factura_{factura[1]}.pdf'
    
    return response

@app.route('/factura/eliminar/<int:id>')
def eliminar_factura(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Restaurar stock de productos
    cursor.execute('''
        SELECT producto_id, cantidad FROM factura_detalles WHERE factura_id = ?
    ''', (id,))
    detalles = cursor.fetchall()
    
    for detalle in detalles:
        cursor.execute('''
            UPDATE productos SET stock = stock + ? WHERE id = ?
        ''', (detalle[1], detalle[0]))
    
    # Eliminar detalles y factura
    cursor.execute('DELETE FROM factura_detalles WHERE factura_id = ?', (id,))
    cursor.execute('DELETE FROM facturas WHERE id = ? AND usuario_id = ?', (id, session['usuario_id']))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('listar_facturas'))

# API para obtener productos
@app.route('/api/productos')
def api_productos():
    if 'usuario_id' not in session:
        return jsonify([])
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, codigo, nombre, precio, stock FROM productos WHERE usuario_id = ? AND stock > 0', 
                  (session['usuario_id'],))
    productos = cursor.fetchall()
    conn.close()
    
    productos_list = []
    for p in productos:
        productos_list.append({
            'id': p[0],
            'codigo': p[1],
            'nombre': p[2],
            'precio': p[3],
            'stock': p[4]
        })
    
    return jsonify(productos_list)

# ============ INICIAR APLICACIÓN ============
if __name__ == '__main__':
    app.run(debug=True, port=5000)