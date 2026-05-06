import sqlite3
from datetime import datetime

def crear_base_datos():
    # Conectar a la base de datos
    conn = sqlite3.connect('helpTech.db')
    cursor = conn.cursor()
    
    # Crear tabla de usuarios
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
    ''')
    
    # Crear tabla para clientes
    cursor.execute('''
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            direccion TEXT,
            documento TEXT,
            fecha_registro TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla para productos
    cursor.execute('''
        CREATE TABLE productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            codigo TEXT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            categoria TEXT,
            fecha_registro TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Crear tabla para facturas (CON TODAS LAS COLUMNAS NECESARIAS)
    cursor.execute('''
        CREATE TABLE facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            numero_factura TEXT UNIQUE,
            cliente_id INTEGER,
            fecha TEXT,
            subtotal REAL DEFAULT 0,
            iva REAL DEFAULT 0,
            total REAL DEFAULT 0,
            estado TEXT DEFAULT 'pagada',
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    # Crear tabla para detalles de factura
    cursor.execute('''
        CREATE TABLE factura_detalles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY (factura_id) REFERENCES facturas (id),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos creada exitosamente con TODAS las columnas necesarias")
    print("📋 Tablas creadas: usuarios, clientes, productos, facturas, factura_detalles")
    print("✅ La columna 'total' ha sido incluida en la tabla facturas")

if __name__ == "__main__":
    crear_base_datos()
    print("\n🎉 ¡Listo! Ahora puedes ejecutar python app.py")