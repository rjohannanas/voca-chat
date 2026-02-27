import boto3
import psycopg2
import json
from pgvector.psycopg2 import register_vector

# 1. Configuración
DB_CONFIG = {
    "host": "chatbot-vocacional-instancia.cfk4w0y8ucoe.us-east-2.rds.amazonaws.com",
    "database": "chatbot_db",
    "user": "postgres",
    "password": "crocodilo1"
}

# Cliente de Bedrock
bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-2')

# 2. Datos de prueba (El corazón de tu idea)
actividades = [
    {"txt": "Analizar por qué la gente elige un producto sobre otro usando datos", "dim": {"analitico": 0.9}, "env": "Marketing/Data"},
    {"txt": "Coordinar equipos para resolver un problema urgente en una ciudad", "dim": {"liderazgo": 0.8}, "env": "Social/Gov"},
    {"txt": "Diseñar interfaces que sean fáciles de usar para personas mayores", "dim": {"creativo": 0.7}, "env": "Tech/Diseño"},
    {"txt": "Investigar vulnerabilidades en sistemas para proteger información", "dim": {"seguridad": 0.9}, "env": "Ciberseguridad"}
]

def generar_vector(texto):
    body = json.dumps({"inputText": texto})
    response = bedrock.invoke_model(
        body=body,
        modelId='amazon.titan-embed-text-v2:0',
        accept='application/json',
        contentType='application/json'
    )
    return json.loads(response.get('body').read())['embedding']

try:
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    print("🚀 Empezando la carga de actividades...")
    for act in actividades:
        vector = generar_vector(act['txt'])
        cur.execute(
            "INSERT INTO actividades (descripcion, dimensiones, embedding) VALUES (%s, %s, %s)",
            (act['txt'], json.dumps(act['dim']), vector)
        )
    
    conn.commit()
    print(f"✅ ¡Éxito! {len(actividades)} actividades cargadas con sus vectores.")
    
    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
