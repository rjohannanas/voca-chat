import psycopg2
import toml
import os

# --- 1. CARGA SEGURA DE CONFIGURACIÓN ---
try:
    # Localizamos el archivo de secretos subiendo un nivel desde /scripts
    ruta_secrets = os.path.join(os.path.dirname(__file__), '../.streamlit/secrets.toml')
    secrets = toml.load(ruta_secrets)
    
    # Extraemos la configuración de la base de datos
    DB_CONFIG = secrets["connections"]["postgresql"]
except Exception as e:
    print(f"❌ Error al cargar secrets.toml: {e}")
    exit()

# --- 2. LÓGICA DE INICIALIZACIÓN ---
try:
    # Conectamos usando el desempaquetado de diccionario (**) 
    # Esto usa host, database, user y password del archivo TOML
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("¡Conexión exitosa a AWS RDS! 🚀")

    # Activar la extensión pgvector
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Crear la tabla de micro-actividades
    # Usamos 1024 para el modelo Titan v2
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actividades (
            id SERIAL PRIMARY KEY,
            descripcion TEXT NOT NULL,
            dimensiones JSONB,
            embedding VECTOR(1024) 
        );
    """)
    
    # Crear la tabla de historial (importante para que app.py no falle)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_conversaciones (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            mensaje_usuario TEXT NOT NULL,
            respuesta_ia TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    conn.commit()
    print("Tablas 'actividades' e 'historial_conversaciones' listas. ✅")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error de base de datos: {e}")
