import sqlite3

conn = sqlite3.connect('helpTech.db')
cursor = conn.cursor()

# Verificar columnas de la tabla facturas
cursor.execute("PRAGMA table_info(facturas)")
columnas = cursor.fetchall()

print("📋 Columnas en la tabla facturas:")
for columna in columnas:
    print(f"  ✓ {columna[1]} ({columna[2]})")

# Verificar si existe la columna total
existe_total = any(columna[1] == 'total' for columna in columnas)

if existe_total:
    print("\n✅ ¡La columna 'total' existe correctamente!")
else:
    print("\n❌ ERROR: La columna 'total' no existe")

conn.close()