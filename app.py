import streamlit as st
import boto3
import psycopg2
import json
from pgvector.psycopg2 import register_vector

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Voca-Chat UNI", page_icon="🎓")
st.title("🎓 Voca-Chat: Tu Orientador IA")
st.markdown("Cuéntame tus hobbies y te ayudaré a encontrar tu camino profesional.")

# Leer de .streamlit/secrets.toml
DB_CONFIG = st.secrets["connections"]["postgresql"]
AWS_KEYS = st.secrets["aws"]

# Inicializar Bedrock de forma segura
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=AWS_KEYS["region"],
    aws_access_key_id=AWS_KEYS["aws_access_key_id"],
    aws_secret_access_key=AWS_KEYS["aws_secret_access_key"]
)

# --- 2. FUNCIONES DE BASE DE DATOS (Backend) ---

def validar_usuario(user, password):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT password FROM usuarios WHERE username = %s", (user,))
        resultado = cur.fetchone()
        cur.close()
        conn.close()
        return resultado and resultado[0] == password
    except Exception as e:
        st.error(f"Error de conexión DB: {e}")
        return False

def cargar_historial_desde_db(username):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT mensaje_usuario, respuesta_ia 
        FROM historial_conversaciones 
        WHERE username = %s 
        ORDER BY fecha ASC LIMIT 10
    """, (username,))
    filas = cur.fetchall()
    cur.close()
    conn.close()
    
    historial = []
    for f in filas:
        historial.append({"role": "user", "content": f[0]})
        historial.append({"role": "assistant", "content": f[1]})
    return historial

def guardar_historial(user, mensaje, respuesta):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO historial_conversaciones (username, mensaje_usuario, respuesta_ia) VALUES (%s, %s, %s)",
        (user, mensaje, respuesta)
    )
    conn.commit()
    cur.close()
    conn.close()

# --- 3. FUNCIONES DE IA (Inteligencia) ---

def obtener_embedding(texto):
    body = json.dumps({"inputText": texto})
    response = bedrock.invoke_model(
        body=body,
        modelId='amazon.titan-embed-text-v2:0',
        accept='application/json',
        contentType='application/json'
    )
    return json.loads(response.get('body').read())['embedding']

def generar_respuesta_ia(interes_usuario, actividad_encontrada, historial_chat):
    system_prompt = f"""
    Eres un orientador vocacional empático de la UNI. 
    Actividad detectada en DB: "{actividad_encontrada}".
    Usa el historial para no repetirte y mantén la charla fluida.
    Responde brevemente (máximo 3 oraciones) y termina con una pregunta.
    """
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "system": system_prompt,
        "messages": historial_chat
    })
    
    response = bedrock.invoke_model(body=body, modelId='us.anthropic.claude-3-haiku-20240307-v1:0')
    result = json.loads(response.get('body').read())
    return result['content'][0]['text']

# --- 4. LÓGICA DE SESIÓN Y LOGIN ---

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("Login"):
        st.subheader("Acceso al Voca-Chat")
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if validar_usuario(u_input, p_input):
                st.session_state.logged_in = True
                st.session_state.username = u_input
                # Cargamos la memoria real de AWS al iniciar
                st.session_state.messages = cargar_historial_desde_db(u_input)
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- 5. INTERFAZ DE CHAT (Si está logueado) ---

st.sidebar.write(f"Conectado como: **{st.session_state.username}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

# Mostrar mensajes (del historial cargado o nuevos)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("¿Qué te apasiona hacer?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.spinner("Consultando con la IA..."):
            # RAG: Búsqueda vectorial
            vector = obtener_embedding(prompt)
            conn = psycopg2.connect(**DB_CONFIG)
            register_vector(conn)
            cur = conn.cursor()
            cur.execute("SELECT descripcion FROM actividades ORDER BY embedding <=> %s::vector LIMIT 1", (vector,))
            actividad_top = cur.fetchone()[0]
            cur.close()
            conn.close()

            # Generar respuesta
            respuesta = generar_respuesta_ia(prompt, actividad_top, st.session_state.messages)
            
        with st.chat_message("assistant"):
            st.markdown(respuesta)
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
        
        # PERSISTENCIA: Guardar en la tabla de RDS
        guardar_historial(st.session_state.username, prompt, respuesta)

    except Exception as e:
        st.error(f"Hubo un error: {e}")
