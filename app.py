from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import re
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = 'helptech_f_secret_key_2025'

# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect('helptech_f.db')
    conn.row_factory = sqlite3.Row
    return conn

# Función para crear TODAS las tablas
def init_db():
    """Crear todas las tablas necesarias"""
    conn = get_db_connection()
    
    # Tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            company TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    # Tabla de sesiones de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tabla de clientes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            email TEXT,
            client_type TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Tabla de productos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            unit_price REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            tax_rate REAL NOT NULL DEFAULT 0,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Tabla de impuestos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS taxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tax_rate REAL NOT NULL DEFAULT 0,
            description TEXT,
            tax_type TEXT NOT NULL DEFAULT 'IVA',
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Tabla de facturas
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            invoice_date DATE NOT NULL,
            due_date DATE,
            status TEXT NOT NULL DEFAULT 'Pendiente',
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Tabla de items de factura
    conn.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL DEFAULT 0,
            tax_rate REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            tax_amount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Todas las tablas de la base de datos creadas/verificadas correctamente")

# Función para hash de contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Función para verificar contraseña
def check_password(password_hash, password):
    return password_hash == hashlib.sha256(password.encode()).hexdigest()

# Función para formatear fecha
def format_date(date_string):
    """Convierte string de fecha a formato legible"""
    try:
        if isinstance(date_string, datetime):
            return date_string.strftime('%d/%m/%Y')
        
        if isinstance(date_string, str):
            if ' ' in date_string:
                date_part = date_string.split(' ')[0]
                return datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y')
            else:
                return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return date_string

# Validaciones
def validate_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password):
    """Valida fortaleza de la contraseña"""
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    
    if not any(char.isdigit() for char in password):
        return False, "La contraseña debe contener al menos un número"
    
    if not any(char.isalpha() for char in password):
        return False, "La contraseña debe contener al menos una letra"
    
    return True, "Contraseña válida"

def validate_name(name):
    """Valida nombre"""
    if len(name.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    if not all(char.isalpha() or char.isspace() for char in name):
        return False, "El nombre solo puede contener letras y espacios"
    
    return True, "Nombre válido"

# Middleware para verificar autenticación
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función para generar número de factura
def generate_invoice_number():
    year = datetime.now().year
    random_str = ''.join(random.choices(string.digits, k=6))
    return f'FACT-{year}-{random_str}'

# ============================================
# RUTAS PRINCIPALES (mantener igual)
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        errors = []
        
        if not email:
            errors.append('El email es requerido')
        elif not validate_email(email):
            errors.append('El formato del email no es válido')
        
        if not password:
            errors.append('La contraseña es requerida')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('login.html', email=email)
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND is_active = TRUE',
            (email,)
        ).fetchone()
        conn.close()
        
        if user and check_password(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            
            conn = get_db_connection()
            conn.execute(
                'INSERT INTO user_sessions (user_id, ip_address) VALUES (?, ?)',
                (user['id'], request.remote_addr)
            )
            conn.commit()
            conn.close()
            
            flash(f'¡Bienvenido de nuevo, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
            return render_template('login.html', email=email)
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        company = request.form.get('company', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        name_valid, name_error = validate_name(name)
        if not name_valid:
            errors.append(name_error)
        
        if not email:
            errors.append('El email es requerido')
        elif not validate_email(email):
            errors.append('El formato del email no es válido')
        
        if not password:
            errors.append('La contraseña es requerida')
        else:
            password_valid, password_error = validate_password_strength(password)
            if not password_valid:
                errors.append(password_error)
        
        if password != confirm_password:
            errors.append('Las contraseñas no coinciden')
        
        if not errors:
            conn = get_db_connection()
            existing_user = conn.execute(
                'SELECT id FROM users WHERE email = ?', (email,)
            ).fetchone()
            conn.close()
            
            if existing_user:
                errors.append('Este email ya está registrado')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', name=name, email=email, company=company)
        
        try:
            password_hash = hash_password(password)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (name, email, company, password_hash) VALUES (?, ?, ?, ?)',
                (name, email, company, password_hash)
            )
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('Error en el registro. Por favor, inténtalo de nuevo.', 'error')
            return render_template('register.html', name=name, email=email, company=company)
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (session['user_id'],)
    ).fetchone()
    conn.close()
    
    if not user:
        session.clear()
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('login'))
    
    user_dict = dict(user)
    user_dict['created_at_formatted'] = format_date(user['created_at'])
    
    return render_template('dashboard.html', user=user_dict)

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (session['user_id'],)
    ).fetchone()
    conn.close()
    
    user_dict = dict(user)
    user_dict['created_at_formatted'] = format_date(user['created_at'])
    
    return render_template('profile.html', user=user_dict)

# ============================================
# RUTAS DE GESTIÓN DE CLIENTES (mantener igual)
# ============================================

@app.route('/client-management')
@login_required
def client_management():
    conn = get_db_connection()
    clients = conn.execute(
        'SELECT * FROM clients WHERE created_by = ? AND is_active = TRUE ORDER BY name',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('client_management.html', clients=clients)

@app.route('/add-client', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        client_type = request.form.get('client_type', '').strip()
        
        errors = []
        
        if not name:
            errors.append('El nombre del cliente es requerido')
        
        if not client_type:
            errors.append('El tipo de cliente es requerido')
        
        if email and not validate_email(email):
            errors.append('El formato del email no es válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_client.html', 
                                 name=name, address=address, phone=phone, 
                                 email=email, client_type=client_type)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''INSERT INTO clients 
                (name, address, phone, email, client_type, created_by) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (name, address, phone, email, client_type, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Cliente agregado exitosamente', 'success')
            return redirect(url_for('client_management'))
            
        except Exception as e:
            flash('Error al agregar el cliente', 'error')
            return render_template('add_client.html', 
                                 name=name, address=address, phone=phone, 
                                 email=email, client_type=client_type)
    
    return render_template('add_client.html')

@app.route('/edit-client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    conn = get_db_connection()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ? AND created_by = ?',
        (client_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not client:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('client_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        client_type = request.form.get('client_type', '').strip()
        
        errors = []
        
        if not name:
            errors.append('El nombre del cliente es requerido')
        
        if not client_type:
            errors.append('El tipo de cliente es requerido')
        
        if email and not validate_email(email):
            errors.append('El formato del email no es válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_client.html', client=client)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''UPDATE clients 
                SET name = ?, address = ?, phone = ?, email = ?, client_type = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ? AND created_by = ?''',
                (name, address, phone, email, client_type, client_id, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('client_management'))
            
        except Exception as e:
            flash('Error al actualizar el cliente', 'error')
            return render_template('edit_client.html', client=client)
    
    return render_template('edit_client.html', client=client)

@app.route('/delete-client/<int:client_id>')
@login_required
def delete_client(client_id):
    conn = get_db_connection()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ? AND created_by = ?',
        (client_id, session['user_id'])
    ).fetchone()
    
    if not client:
        conn.close()
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('client_management'))
    
    conn.execute(
        'UPDATE clients SET is_active = FALSE WHERE id = ?',
        (client_id,)
    )
    conn.commit()
    conn.close()
    
    flash('Cliente eliminado exitosamente', 'success')
    return redirect(url_for('client_management'))

@app.route('/view-client/<int:client_id>')
@login_required
def view_client(client_id):
    conn = get_db_connection()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ? AND created_by = ? AND is_active = TRUE',
        (client_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not client:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('client_management'))
    
    return render_template('view_client.html', client=client)

# ============================================
# RUTAS DE GESTIÓN DE PRODUCTOS (NUEVAS)
# ============================================

@app.route('/product-management')
@login_required
def product_management():
    """Vista principal de gestión de productos"""
    conn = get_db_connection()
    products = conn.execute(
        '''SELECT * FROM products 
           WHERE created_by = ? AND is_active = TRUE 
           ORDER BY name''',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('product_management.html', products=products)

@app.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Agregar nuevo producto"""
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        unit_price = request.form.get('unit_price', '0').strip()
        stock = request.form.get('stock', '0').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        
        # Validaciones
        errors = []
        
        if not code:
            errors.append('El código del producto es requerido')
        
        if not name:
            errors.append('El nombre del producto es requerido')
        
        # Validar números
        try:
            unit_price = float(unit_price)
            if unit_price < 0:
                errors.append('El precio unitario no puede ser negativo')
        except:
            errors.append('El precio unitario debe ser un número válido')
        
        try:
            stock = int(stock)
            if stock < 0:
                errors.append('El stock no puede ser negativo')
        except:
            errors.append('El stock debe ser un número entero válido')
        
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                errors.append('La tasa de impuesto debe estar entre 0 y 100')
        except:
            errors.append('La tasa de impuesto debe ser un número válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_product.html', 
                                 code=code, name=name, description=description,
                                 category=category, unit_price=unit_price,
                                 stock=stock, tax_rate=tax_rate)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''INSERT INTO products 
                (code, name, description, category, unit_price, stock, tax_rate, created_by) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (code, name, description, category, unit_price, stock, tax_rate, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Producto agregado exitosamente', 'success')
            return redirect(url_for('product_management'))
            
        except Exception as e:
            flash('Error al agregar el producto', 'error')
            return render_template('add_product.html', 
                                 code=code, name=name, description=description,
                                 category=category, unit_price=unit_price,
                                 stock=stock, tax_rate=tax_rate)
    
    return render_template('add_product.html')

@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Editar producto existente"""
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ? AND created_by = ?',
        (product_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not product:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('product_management'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        unit_price = request.form.get('unit_price', '0').strip()
        stock = request.form.get('stock', '0').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        
        # Validaciones
        errors = []
        
        if not code:
            errors.append('El código del producto es requerido')
        
        if not name:
            errors.append('El nombre del producto es requerido')
        
        # Validar números
        try:
            unit_price = float(unit_price)
            if unit_price < 0:
                errors.append('El precio unitario no puede ser negativo')
        except:
            errors.append('El precio unitario debe ser un número válido')
        
        try:
            stock = int(stock)
            if stock < 0:
                errors.append('El stock no puede ser negativo')
        except:
            errors.append('El stock debe ser un número entero válido')
        
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                errors.append('La tasa de impuesto debe estar entre 0 y 100')
        except:
            errors.append('La tasa de impuesto debe ser un número válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_product.html', product=product)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''UPDATE products 
                SET code = ?, name = ?, description = ?, category = ?, 
                    unit_price = ?, stock = ?, tax_rate = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ? AND created_by = ?''',
                (code, name, description, category, unit_price, stock, tax_rate, 
                 product_id, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Producto actualizado exitosamente', 'success')
            return redirect(url_for('product_management'))
            
        except Exception as e:
            flash('Error al actualizar el producto', 'error')
            return render_template('edit_product.html', product=product)
    
    return render_template('edit_product.html', product=product)

@app.route('/delete-product/<int:product_id>')
@login_required
def delete_product(product_id):
    """Eliminar producto (soft delete)"""
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ? AND created_by = ?',
        (product_id, session['user_id'])
    ).fetchone()
    
    if not product:
        conn.close()
        flash('Producto no encontrado', 'error')
        return redirect(url_for('product_management'))
    
    conn.execute(
        'UPDATE products SET is_active = FALSE WHERE id = ?',
        (product_id,)
    )
    conn.commit()
    conn.close()
    
    flash('Producto eliminado exitosamente', 'success')
    return redirect(url_for('product_management'))

@app.route('/view-product/<int:product_id>')
@login_required
def view_product(product_id):
    """Ver detalles del producto"""
    conn = get_db_connection()
    product = conn.execute(
        '''SELECT * FROM products 
           WHERE id = ? AND created_by = ? AND is_active = TRUE''',
        (product_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not product:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('product_management'))
    
    return render_template('view_product.html', product=product)

# ============================================
# RUTAS DE GESTIÓN DE FACTURAS (NUEVAS)
# ============================================

@app.route('/invoice-management')
@login_required
def invoice_management():
    """Vista principal de gestión de facturas"""
    conn = get_db_connection()
    invoices = conn.execute(
        '''SELECT i.*, c.name as client_name 
           FROM invoices i
           LEFT JOIN clients c ON i.client_id = c.id
           WHERE i.created_by = ? AND i.is_active = TRUE 
           ORDER BY i.invoice_date DESC''',
        (session['user_id'],)
    ).fetchall()
    
    clients = conn.execute(
        'SELECT id, name FROM clients WHERE created_by = ? AND is_active = TRUE',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    return render_template('invoice_management.html', invoices=invoices, clients=clients)

@app.route('/add-invoice', methods=['GET', 'POST'])
@login_required
def add_invoice():
    """Agregar nueva factura"""
    conn = get_db_connection()
    clients = conn.execute(
        'SELECT id, name FROM clients WHERE created_by = ? AND is_active = TRUE',
        (session['user_id'],)
    ).fetchall()
    
    products = conn.execute(
        'SELECT id, name, unit_price, tax_rate FROM products WHERE created_by = ? AND is_active = TRUE',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        invoice_date = request.form.get('invoice_date')
        due_date = request.form.get('due_date')
        status = request.form.get('status', 'Pendiente')
        
        # Validaciones básicas
        if not client_id:
            flash('Debe seleccionar un cliente', 'error')
            return render_template('add_invoice.html', clients=clients, products=products)
        
        try:
            conn = get_db_connection()
            # Insertar factura
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO invoices 
                (client_id, invoice_number, invoice_date, due_date, status, created_by) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (client_id, generate_invoice_number(), invoice_date, due_date, status, session['user_id'])
            )
            
            invoice_id = cursor.lastrowid
            
            # Insertar items de la factura
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            
            for product_id, quantity in zip(product_ids, quantities):
                if product_id and quantity:
                    # Obtener información del producto
                    product = conn.execute(
                        'SELECT unit_price, tax_rate FROM products WHERE id = ?',
                        (product_id,)
                    ).fetchone()
                    
                    if product:
                        unit_price = product['unit_price']
                        tax_rate = product['tax_rate']
                        subtotal = float(unit_price) * float(quantity)
                        tax_amount = subtotal * (float(tax_rate) / 100)
                        total = subtotal + tax_amount
                        
                        conn.execute(
                            '''INSERT INTO invoice_items 
                            (invoice_id, product_id, quantity, unit_price, tax_rate, subtotal, tax_amount, total) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (invoice_id, product_id, quantity, unit_price, tax_rate, subtotal, tax_amount, total)
                        )
            
            conn.commit()
            conn.close()
            
            flash('Factura creada exitosamente', 'success')
            return redirect(url_for('invoice_management'))
            
        except Exception as e:
            flash('Error al crear la factura', 'error')
            return render_template('add_invoice.html', clients=clients, products=products)
    
    return render_template('add_invoice.html', clients=clients, products=products)

@app.route('/view-invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """Ver detalles de la factura"""
    conn = get_db_connection()
    
    invoice = conn.execute(
        '''SELECT i.*, c.name as client_name, c.address, c.phone, c.email
           FROM invoices i
           LEFT JOIN clients c ON i.client_id = c.id
           WHERE i.id = ? AND i.created_by = ?''',
        (invoice_id, session['user_id'])
    ).fetchone()
    
    if not invoice:
        conn.close()
        flash('Factura no encontrada', 'error')
        return redirect(url_for('invoice_management'))
    
    items = conn.execute(
        '''SELECT ii.*, p.name as product_name, p.code as product_code
           FROM invoice_items ii
           LEFT JOIN products p ON ii.product_id = p.id
           WHERE ii.invoice_id = ?''',
        (invoice_id,)
    ).fetchall()
    
    # Calcular totales
    totals = conn.execute(
        '''SELECT SUM(subtotal) as subtotal, SUM(tax_amount) as tax, SUM(total) as total
           FROM invoice_items WHERE invoice_id = ?''',
        (invoice_id,)
    ).fetchone()
    
    conn.close()
    
    return render_template('view_invoice.html', invoice=invoice, items=items, totals=totals)

@app.route('/delete-invoice/<int:invoice_id>')
@login_required
def delete_invoice(invoice_id):
    """Eliminar factura (soft delete)"""
    conn = get_db_connection()
    invoice = conn.execute(
        'SELECT * FROM invoices WHERE id = ? AND created_by = ?',
        (invoice_id, session['user_id'])
    ).fetchone()
    
    if not invoice:
        conn.close()
        flash('Factura no encontrada', 'error')
        return redirect(url_for('invoice_management'))
    
    # Primero eliminar los items de la factura
    conn.execute('DELETE FROM invoice_items WHERE invoice_id = ?', (invoice_id,))
    
    # Luego eliminar la factura
    conn.execute('UPDATE invoices SET is_active = FALSE WHERE id = ?', (invoice_id,))
    
    conn.commit()
    conn.close()
    
    flash('Factura eliminada exitosamente', 'success')
    return redirect(url_for('invoice_management'))

# ============================================
# RUTAS DE GESTIÓN DE IMPUESTOS (NUEVAS)
# ============================================

@app.route('/tax-management')
@login_required
def tax_management():
    """Vista principal de gestión de impuestos"""
    conn = get_db_connection()
    taxes = conn.execute(
        '''SELECT * FROM taxes 
           WHERE created_by = ? AND is_active = TRUE 
           ORDER BY name''',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('tax_management.html', taxes=taxes)

@app.route('/add-tax', methods=['GET', 'POST'])
@login_required
def add_tax():
    """Agregar nuevo impuesto"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        description = request.form.get('description', '').strip()
        tax_type = request.form.get('tax_type', 'IVA')
        
        # Validaciones
        errors = []
        
        if not name:
            errors.append('El nombre del impuesto es requerido')
        
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                errors.append('La tasa de impuesto debe estar entre 0 y 100')
        except:
            errors.append('La tasa de impuesto debe ser un número válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_tax.html', 
                                 name=name, tax_rate=tax_rate, 
                                 description=description, tax_type=tax_type)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''INSERT INTO taxes 
                (name, tax_rate, description, tax_type, created_by) 
                VALUES (?, ?, ?, ?, ?)''',
                (name, tax_rate, description, tax_type, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Impuesto agregado exitosamente', 'success')
            return redirect(url_for('tax_management'))
            
        except Exception as e:
            flash('Error al agregar el impuesto', 'error')
            return render_template('add_tax.html', 
                                 name=name, tax_rate=tax_rate, 
                                 description=description, tax_type=tax_type)
    
    return render_template('add_tax.html')

@app.route('/edit-tax/<int:tax_id>', methods=['GET', 'POST'])
@login_required
def edit_tax(tax_id):
    """Editar impuesto existente"""
    conn = get_db_connection()
    tax = conn.execute(
        'SELECT * FROM taxes WHERE id = ? AND created_by = ?',
        (tax_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not tax:
        flash('Impuesto no encontrado', 'error')
        return redirect(url_for('tax_management'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        tax_rate = request.form.get('tax_rate', '0').strip()
        description = request.form.get('description', '').strip()
        tax_type = request.form.get('tax_type', 'IVA')
        
        # Validaciones
        errors = []
        
        if not name:
            errors.append('El nombre del impuesto es requerido')
        
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                errors.append('La tasa de impuesto debe estar entre 0 y 100')
        except:
            errors.append('La tasa de impuesto debe ser un número válido')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_tax.html', tax=tax)
        
        try:
            conn = get_db_connection()
            conn.execute(
                '''UPDATE taxes 
                SET name = ?, tax_rate = ?, description = ?, tax_type = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ? AND created_by = ?''',
                (name, tax_rate, description, tax_type, tax_id, session['user_id'])
            )
            conn.commit()
            conn.close()
            
            flash('Impuesto actualizado exitosamente', 'success')
            return redirect(url_for('tax_management'))
            
        except Exception as e:
            flash('Error al actualizar el impuesto', 'error')
            return render_template('edit_tax.html', tax=tax)
    
    return render_template('edit_tax.html', tax=tax)

@app.route('/delete-tax/<int:tax_id>')
@login_required
def delete_tax(tax_id):
    """Eliminar impuesto (soft delete)"""
    conn = get_db_connection()
    tax = conn.execute(
        'SELECT * FROM taxes WHERE id = ? AND created_by = ?',
        (tax_id, session['user_id'])
    ).fetchone()
    
    if not tax:
        conn.close()
        flash('Impuesto no encontrado', 'error')
        return redirect(url_for('tax_management'))
    
    conn.execute(
        'UPDATE taxes SET is_active = FALSE WHERE id = ?',
        (tax_id,)
    )
    conn.commit()
    conn.close()
    
    flash('Impuesto eliminado exitosamente', 'success')
    return redirect(url_for('tax_management'))

@app.route('/view-tax/<int:tax_id>')
@login_required
def view_tax(tax_id):
    """Ver detalles del impuesto"""
    conn = get_db_connection()
    tax = conn.execute(
        '''SELECT * FROM taxes 
           WHERE id = ? AND created_by = ? AND is_active = TRUE''',
        (tax_id, session['user_id'])
    ).fetchone()
    conn.close()
    
    if not tax:
        flash('Impuesto no encontrado', 'error')
        return redirect(url_for('tax_management'))
    
    return render_template('view_tax.html', tax=tax)

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('index'))

# Inicializar la base de datos al iniciar la aplicación
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)