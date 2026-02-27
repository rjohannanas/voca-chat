import psycopg2

# Configuración con tus datos de AWS
DB_HOST = "chatbot-vocacional-instancia.cfk4w0y8ucoe.us-east-2.rds.amazonaws.com"
DB_NAME = "chatbot_db"
DB_USER = "postgres"
DB_PASS = "crocodilo1" # La que escribiste hace un momento

try:
    # 1. Establecer conexión
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port="5432"
    )
    cur = conn.cursor()
    print("¡Conexión exitosa a AWS RDS! 🚀")

    # 2. Activar la extensión pgvector (El superpoder de IA)
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # 3. Crear la tabla de micro-actividades
    # Usamos 1024 porque es la dimensión del modelo Titan v2 de Bedrock
    cur.execute("""
        CREATE TABLE IF NOT EXISTS actividades (
            id SERIAL PRIMARY KEY,
            descripcion TEXT NOT NULL,
            dimensiones JSONB,
            embedding VECTOR(1024) 
        );
    """)
    
    conn.commit()
    print("Extensión pgvector activada y tabla 'actividades' creada correctamente. ✅")

    cur.close()
    conn.close()

except Exception as e:
    print(f"Error de conexión: {e}")
