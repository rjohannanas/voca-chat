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

def obtener_embedding(texto):
    body = json.dumps({"inputText": texto})
    response = bedrock.invoke_model(
        body=body,
        modelId='amazon.titan-embed-text-v2:0',
        accept='application/json',
        contentType='application/json'
    )
    return json.loads(response.get('body').read())['embedding']

def generar_respuesta_ia(interes_usuario, actividad_encontrada):
    prompt = f"""
    Eres un orientador vocacional humano, empático y curioso de la UNI. 
    El usuario dice que le apasiona: "{interes_usuario}"
    En nuestra base de datos, lo más cercano es: "{actividad_encontrada}"
    
    NO des una conclusión profesional todavía. En su lugar:
    1. Valida su interés con calidez.
    2. Haz una conexión muy sutil con la actividad encontrada.
    3. Termina con una PREGUNTA abierta.
    
    Respuesta corta (máximo 3 oraciones).
    """
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    response = bedrock.invoke_model(
        body=body,
        modelId='us.anthropic.claude-3-haiku-20240307-v1:0'
    )
    result = json.loads(response.get('body').read())
    return result['content'][0]['text']

# --- 3. FLUJO PRINCIPAL ---
print("✨ ¡Hola! Soy Voca-Chat. Cuéntame sobre tus hobbies o lo que te gusta hacer...")

try:
    # Conexión usando desempaquetado de diccionario
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    while True:
        pregunta_usuario = input("\n👤 Tú: ")

        if pregunta_usuario.lower() in ["salir", "exit", "chau"]:
            print("👋 ¡Nos vemos, Johanna! Éxitos en la UNI.")
            break

        try:
            vector_usuario = obtener_embedding(pregunta_usuario)
            
            # Búsqueda semántica usando el operador de distancia de pgvector
            cur.execute(
                "SELECT descripcion FROM actividades ORDER BY embedding <=> %s::vector LIMIT 1",
                (vector_usuario,)
            )
            resultado_db = cur.fetchone()[0]

            print("\n🔍 Analizando tu perfil...")
            respuesta_final = generar_respuesta_ia(pregunta_usuario, resultado_db)
            print(f"\n💡 Orientador IA: {respuesta_final}")

        except Exception as e:
            print(f"❌ Error en el proceso: {e}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error de conexión: {e}")
