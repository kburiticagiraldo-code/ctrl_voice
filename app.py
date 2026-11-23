import base64
import json
import os
import unicodedata

import paho.mqtt.client as paho
import streamlit as st
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

# ---------- Configuración ----------
st.set_page_config(page_title="Interfaces Multimodales", page_icon="🎙️", layout="centered")

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "ksbg"
IMAGEN = "voice_ctrl.jpg"

# ---------- Estilos ----------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(160deg, #1E1B5E 0%, #0F1230 35%, #0A0D24 100%);
    }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 760px; padding-top: 3rem; }
    p, span, div, label { color: #E6E8FF; }

    .titulo {
        text-align: center; font-size: 2.3rem; font-weight: 800; margin: 0;
        background: linear-gradient(90deg, #4DA3FF, #B47CFF, #FF7CC8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .subtitulo {
        text-align: center; letter-spacing: .35em; font-size: .85rem;
        color: #9FA6D9 !important; margin: 10px 0 24px 0;
    }
    .avatar {
        width: 190px; height: 190px; border-radius: 50%; margin: 0 auto 36px auto;
        border: 3px solid #7C6CF0; background: #FFFFFF; overflow: hidden;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 40px rgba(124, 108, 240, .35); font-size: 5rem;
    }
    .avatar img { width: 100%; height: 100%; object-fit: cover; }

    .seccion {
        font-size: 1rem; font-weight: 700; letter-spacing: .04em;
        margin: 26px 0 12px 0; color: #FFFFFF !important;
    }

    .estado-grid { display: flex; gap: 16px; }
    .estado {
        flex: 1; text-align: center; padding: 22px 12px; border-radius: 20px;
        background: #141937; border: 1px solid #2A3060;
    }
    .estado .luz {
        width: 38px; height: 38px; border-radius: 50%; margin: 0 auto 12px auto;
        background: radial-gradient(circle at 35% 30%, #F4EEFF, #9C8BD0);
    }
    .estado.on  .luz { background: radial-gradient(circle at 35% 30%, #FFF6C2, #FFB020);
                       box-shadow: 0 0 22px rgba(255, 176, 32, .7); }
    .estado.off .luz { background: radial-gradient(circle at 35% 30%, #5B6190, #2C3160); }
    .estado .nombre { font-size: .8rem; letter-spacing: .2em; color: #9FA6D9 !important; }
    .estado .valor  { font-size: 1.15rem; font-weight: 700; margin-top: 4px; color: #FFFFFF !important; }

    .cmd-grid { display: flex; flex-wrap: wrap; gap: 10px; }
    .cmd {
        padding: 8px 16px; border-radius: 999px; font-size: .9rem;
        background: #1B2150; border: 1px solid #343B7A; color: #DDE0FF !important;
    }
    .ultimo {
        padding: 16px 20px; border-radius: 16px; background: #141937;
        border: 1px solid #2A3060; font-size: 1.1rem;
    }
    .ultimo b { color: #B47CFF !important; }

    iframe { border-radius: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Estado ----------
st.session_state.setdefault("luces", "Sin datos")
st.session_state.setdefault("puerta", "Sin datos")
st.session_state.setdefault("ultimo", None)


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def interpretar(texto: str):
    """Actualiza el estado visual según lo que se dijo."""
    t = normalizar(texto)
    if "luz" in t or "luces" in t:
        if any(p in t for p in ("enciend", "encend", "prend", "activ")):
            st.session_state.luces = "Encendidas"
        elif any(p in t for p in ("apag", "desactiv")):
            st.session_state.luces = "Apagadas"
    if "puerta" in t:
        if "abr" in t:
            st.session_state.puerta = "Abierta"
        elif "cerr" in t:
            st.session_state.puerta = "Cerrada"


def publicar(texto: str):
    client = paho.Client("stiv_ken")
    client.connect(BROKER, PORT)
    client.publish(TOPIC, json.dumps({"Act1": texto}))
    client.disconnect()


def clase(valor: str) -> str:
    if valor in ("Encendidas", "Abierta"):
        return "on"
    if valor in ("Apagadas", "Cerrada"):
        return "off"
    return ""


# ---------- Encabezado ----------
st.markdown('<div class="titulo">🎙️ INTERFACES MULTIMODALES</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">CONTROL POR VOZ</div>', unsafe_allow_html=True)

if os.path.exists(IMAGEN):
    with open(IMAGEN, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    avatar = f'<img src="data:image/jpeg;base64,{b64}">'
else:
    avatar = "💡"
st.markdown(f'<div class="avatar">{avatar}</div>', unsafe_allow_html=True)

# ---------- Botón de voz ----------
st.markdown('<div class="seccion">🎧 TOCA EL BOTÓN Y HABLA</div>', unsafe_allow_html=True)

stt_button = Button(label="🎙️  Iniciar escucha", width=300, height=50, button_type="primary")
stt_button.js_on_event(
    "button_click",
    CustomJS(
        code="""
    var recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "es-CO";

    recognition.onresult = function (e) {
        var value = "";
        for (var i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
                value += e.results[i][0].transcript;
            }
        }
        if (value != "") {
            document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
        }
    }
    recognition.start();
    """
    ),
)

result = streamlit_bokeh_events(
    stt_button,
    events="GET_TEXT",
    key="listen",
    refresh_on_update=False,
    override_height=75,
    debounce_time=0,
)

if result and "GET_TEXT" in result:
    texto = result.get("GET_TEXT").strip()
    if texto and texto != st.session_state.ultimo:
        try:
            publicar(texto)
            st.session_state.ultimo = texto
            interpretar(texto)
        except Exception as e:
            st.error(f"No se pudo enviar por MQTT: {e}")

# ---------- Último comando ----------
if st.session_state.ultimo:
    st.markdown(
        f'<div class="ultimo">Último comando: <b>“{st.session_state.ultimo}”</b></div>',
        unsafe_allow_html=True,
    )

# ---------- Estado del sistema ----------
luces, puerta = st.session_state.luces, st.session_state.puerta
st.markdown('<div class="seccion">📡 ESTADO DEL SISTEMA</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="estado-grid">
        <div class="estado {clase(luces)}">
            <div class="luz"></div>
            <div class="nombre">LUCES</div>
            <div class="valor">{luces}</div>
        </div>
        <div class="estado {clase(puerta)}">
            <div class="luz"></div>
            <div class="nombre">PUERTA</div>
            <div class="valor">{puerta}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Comandos disponibles ----------
st.markdown('<div class="seccion">💬 COMANDOS DISPONIBLES</div>', unsafe_allow_html=True)
comandos = ["Enciende las luces", "Apaga las luces", "Abre la puerta", "Cierra la puerta"]
st.markdown(
    '<div class="cmd-grid">' + "".join(f'<span class="cmd">{c}</span>' for c in comandos) + "</div>",
    unsafe_allow_html=True,
)
