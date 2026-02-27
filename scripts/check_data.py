import psycopg2
import json

# Configuración (la misma que usaste en seed_db.py)
DB_CONFIG = {
    "host": "chatbot-vocacional-instancia.cfk4w0y8ucoe.us-east-2.rds.amazonaws.com",
    "database": "chatbot_db",
    "user": "postgres",
    "password": "crocodilo1" 
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Consultamos la descripción y solo los primeros 5 números del vector para que no se llene la pantalla
    cur.execute("SELECT descripcion, dimensiones, embedding FROM actividades LIMIT 5;")
    rows = cur.fetchall()

    print("\n--- CONTENIDO DE LA BASE DE DATOS EN AWS ---")
    for row in rows:
        desc = row[0]
        dims = row[1]
        # El embedding es una lista enorme, solo mostramos el inicio
        vector_snippet = str(row[2][:5]) + "..." 
        
        print(f"\n📍 Actividad: {desc}")
        print(f"📊 Dimensiones: {dims}")
        print(f"🔢 Vector (fragmento): {vector_snippet}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error al conectar: {e}")
