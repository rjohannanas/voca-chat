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

bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-2')

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
    Eres un orientador vocacional humano, empático y curioso. 
    El usuario dice que le apasiona: "{interes_usuario}"
    En nuestra base de datos, lo más cercano que tenemos es: "{actividad_encontrada}"
    
    NO des una conclusión profesional todavía. En su lugar:
    1. Valida su interés con calidez.
    2. Haz una conexión muy sutil o metafórica con la actividad encontrada.
    3. Termina con una PREGUNTA abierta para conocer más al usuario.
    
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

# --- FLUJO PRINCIPAL ---
print("✨ ¡Hola! Soy Voca-Chat. Cuéntame sobre tus hobbies o lo que te gusta hacer...")

try:
    # Conectar a la DB una sola vez fuera del bucle para ser más eficientes
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    while True:
        pregunta_usuario = input("\n👤 Tú: ")

        if pregunta_usuario.lower() in ["salir", "exit", "chau"]:
            print("👋 ¡Nos vemos, Johanna! Éxitos en la UNI.")
            break

        try:
            # 1. Convertir entrada a vector
            vector_usuario = obtener_embedding(pregunta_usuario)
            
            # 2. Buscar en PostgreSQL (Búsqueda semántica)
            cur.execute(
                "SELECT descripcion FROM actividades ORDER BY embedding <=> %s::vector LIMIT 1",
                (vector_usuario,)
            )
            resultado_db = cur.fetchone()[0]

            # 3. Generar respuesta con Claude
            print("\n🔍 Analizando tu perfil...")
            respuesta_final = generar_respuesta_ia(pregunta_usuario, resultado_db)
            
            print(f"\n💡 Orientador IA: {respuesta_final}")

        except Exception as e:
            print(f"❌ Error en el proceso: {e}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error de conexión: {e}")
