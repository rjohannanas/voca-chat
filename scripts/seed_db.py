import boto3
import psycopg2
import json
import toml
import os
from pgvector.psycopg2 import register_vector

# --- 1. CARGA SEGURA DE CONFIGURACIÓN ---
try:
    # Localizamos el archivo de secretos subiendo un nivel desde /scripts
    ruta_secrets = os.path.join(os.path.dirname(__file__), '../.streamlit/secrets.toml')
    secrets = toml.load(ruta_secrets)
    
    # Extraemos configuraciones
    DB_CONFIG = secrets["connections"]["postgresql"]
    AWS_KEYS = secrets["aws"]
except Exception as e:
    print(f"❌ Error al cargar secrets.toml: {e}")
    exit()

# --- 2. INICIALIZACIÓN DE CLIENTES ---
bedrock = boto3.client(
    service_name='bedrock-runtime', 
    region_name=AWS_KEYS["region"],
    aws_access_key_id=AWS_KEYS["aws_access_key_id"],
    aws_secret_access_key=AWS_KEYS["aws_secret_access_key"]
)

# Datos de prueba (El corazón de tu idea)
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

# --- 3. LÓGICA DE CARGA ---
try:
    # Conexión usando desempaquetado de diccionario
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    print("🚀 Empezando la carga de actividades...")
    for act in actividades:
        print(f"Generando vector para: {act['txt'][:30]}...")
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
