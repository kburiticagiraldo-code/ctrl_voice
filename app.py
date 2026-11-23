import json
import unicodedata

import paho.mqtt.client as paho
import streamlit as st
from bokeh.models import CustomJS
from bokeh.models.widgets import Button
from streamlit_bokeh_events import streamlit_bokeh_events

# ---------- Configuración ----------
st.set_page_config(page_title="Casa por voz", page_icon="🏠", layout="centered")

BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "ksbg"

# ---------- Estilos ----------
# Paleta: azul hielo (fondo), tinta marino (texto), verde agua (acción), ámbar (encendido)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700;800&family=DM+Sans:wght@400;500;700&display=swap');

    .stApp { background: #E9F0F4; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 620px; padding-top: 3.5rem; }
    html, body, p, span, div, label { font-family: 'DM Sans', sans-serif; color: #10263A; }

    .titulo {
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800;
        font-size: 3.2rem; line-height: 1.02; letter-spacing: -0.02em; margin: 0 0 12px 0;
    }
    .intro { font-size: 1.1rem; color: #4A6275 !important; margin: 0 0 30px 0; max-width: 30em; }

    .voz {
        background: #FFFFFF; border-radius: 28px; padding: 24px 26px 8px 26px;
        box-shadow: 0 10px 30px rgba(16, 38, 58, .08);
    }
    .voz .pista { font-size: .95rem; color: #4A6275 !important; margin-bottom: 4px; }
    .escuche {
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
        font-size: 1.9rem; line-height: 1.2; margin: 6px 0 18px 0;
    }
    .escuche.vacio { color: #9DB0BF !important; }

    .titulo-lista {
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
        font-size: 1.3rem; margin: 34px 0 12px 0;
    }
    .fila {
        display: flex; align-items: center; gap: 16px;
        background: #FFFFFF; border-radius: 20px; padding: 16px 20px; margin-bottom: 12px;
    }
    .fila .icono {
        width: 48px; height: 48px; border-radius: 14px; background: #E9F0F4;
        display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
    }
    .fila.on .icono { background: #FFE9B0; }
    .fila .texto { flex: 1; }
    .fila .nombre { font-weight: 700; font-size: 1.05rem; }
    .fila .estado { font-size: .92rem; color: #4A6275 !important; }

    .switch {
        width: 56px; height: 32px; border-radius: 999px; background: #C5D3DD;
        position: relative; transition: background .25s;
    }
    .switch::after {
        content: ""; position: absolute; top: 4px; left: 4px; width: 24px; height: 24px;
        border-radius: 50%; background: #FFFFFF; transition: left .25s;
    }
    .fila.on .switch { background: #0E9F8E; }
    .fila.on .switch::after { left: 28px; }

    .ejemplos { color: #4A6275 !important; font-size: .98rem; line-height: 1.7; }
    .ejemplos b { color: #10263A !important; font-weight: 500;
                  background: #FFFFFF; padding: 2px 10px; border-radius: 8px; }

    iframe { border-radius: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Estado ----------
st.session_state.setdefault("luces", None)    # True / False / None
st.session_state.setdefault("puerta", None)
st.session_state.setdefault("ultimo", None)


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def interpretar(texto: str):
    t = normalizar(texto)
    if "luz" in t or "luces" in t:
        if any(p in t for p in ("enciend", "encend", "prend", "activ")):
            st.session_state.luces = True
        elif any(p in t for p in ("apag", "desactiv")):
            st.session_state.luces = False
    if "puerta" in t:
        if "abr" in t:
            st.session_state.puerta = True
        elif "cerr" in t:
            st.session_state.puerta = False


def publicar(texto: str):
    client = paho.Client("stiv_ken")
    client.connect(BROKER, PORT)
    client.publish(TOPIC, json.dumps({"Act1": texto}))
    client.disconnect()


def fila(icono, nombre, valor, si, no):
    clase = "on" if valor else ""
    estado = si if valor else (no if valor is False else "Sin información todavía")
    return f"""
    <div class="fila {clase}">
        <div class="icono">{icono}</div>
        <div class="texto"><div class="nombre">{nombre}</div><div class="estado">{estado}</div></div>
        <div class="switch"></div>
    </div>
    """


# ---------- Encabezado ----------
st.markdown('<div class="titulo">Dilo y<br>se hace.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="intro">Controla las luces y la puerta con tu voz. '
    "Interfaces multimodales, control por voz.</div>",
    unsafe_allow_html=True,
)

# ---------- Panel de voz ----------
if st.session_state.ultimo:
    escuche = f'<div class="escuche">“{st.session_state.ultimo}”</div>'
else:
    escuche = '<div class="escuche vacio">Aquí verás lo que digas</div>'

st.markdown(
    f"""
    <div class="voz">
        <div class="pista">Pulsa el botón, permite el micrófono y habla</div>
        {escuche}
    </div>
    """,
    unsafe_allow_html=True,
)

stt_button = Button(label="🎙️  Hablar", width=260, height=52, button_type="success")
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
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo enviar por MQTT: {e}")

# ---------- Dispositivos ----------
st.markdown('<div class="titulo-lista">Tu casa ahora</div>', unsafe_allow_html=True)
st.markdown(
    fila("💡", "Luces", st.session_state.luces, "Encendidas", "Apagadas")
    + fila("🚪", "Puerta", st.session_state.puerta, "Abierta", "Cerrada"),
    unsafe_allow_html=True,
)

# ---------- Ejemplos ----------
st.markdown('<div class="titulo-lista">Prueba diciendo</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ejemplos"><b>enciende las luces</b> <b>apaga las luces</b><br>'
    "<b>abre la puerta</b> <b>cierra la puerta</b></div>",
    unsafe_allow_html=True,
)
