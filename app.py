import os
import tempfile
import requests
import librosa
import streamlit as st
import yt_dlp

# Configuración de la página en Streamlit
st.set_page_config(
    page_title="Analizador de Afinación A4", 
    page_icon="🎵", 
    layout="centered"
)

st.title("🎵 Analizador de Afinación de YouTube")
st.markdown(
    "Ingresa un enlace de YouTube para detectar si la música está en "
    "**432 Hz**, **440 Hz (Estándar)** u otra frecuencia."
)

# Componentes de la interfaz
url_input = st.text_input(
    "URL del Video de YouTube:", 
    placeholder="https://www.youtube.com/watch?v=..."
)

duracion_analisis = st.slider(
    "Segundos de audio a analizar:", 
    min_value=15, 
    max_value=90, 
    value=45, 
    step=5
)

def obtener_audio_bytes(url, temp_dir):
    """
    Descarga el audio evitando el bloqueo 403 de IP en Streamlit Cloud.
    Usa la API pública de Cobalt como canal primario y yt-dlp como respaldo.
    """
    target_wav = os.path.join(temp_dir, "audio_temp.wav")
    
    # --- Intento 1: API de Cobalt (Bypass de IP de Datacenter/AWS) ---
    try:
        cobalt_endpoint = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "downloadMode": "audio",
            "audioFormat": "wav"
        }
        
        response = requests.post(cobalt_endpoint, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            download_url = data.get("url")
            if download_url:
                audio_res = requests.get(download_url, stream=True, timeout=30)
                if audio_res.status_code == 200:
                    with open(target_wav, "wb") as f:
                        for chunk in audio_res.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return target_wav, "Audio obtenido con éxito"
    except Exception:
        pass  # Si la API no responde, continúa al intento con yt-dlp

    # --- Intento 2: yt-dlp con fallback ---
    temp_template = os.path.join(temp_dir, "audio_temp.%(ext)s")
    ydl_opts = {
        'format': 'bestaudio/b/best',
        'outtmpl': temp_template,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
    for file in os.listdir(temp_dir):
        if file.endswith('.wav'):
            return os.path.join(temp_dir, file), info.get('title', 'Desconocido')
            
    raise Exception("No se pudo obtener el archivo de audio procesado.")

def analizar_audio(url, duracion):
    with tempfile.TemporaryDirectory() as tmp_dir:
        archivo_wav, titulo = obtener_audio_bytes(url, tmp_dir)

        # Cargar el audio con Librosa para el análisis armónico
        y, sr = librosa.load(archivo_wav, sr=None, mono=True, duration=duracion)
        
        # Estimación del desplazamiento respecto a A4 = 440Hz
        tuning_offset = librosa.estimate_tuning(y=y, sr=sr)
        a4_hz = 440.0 * (2.0 ** (tuning_offset / 12.0))
        cents = tuning_offset * 100.0
        
        return {
            "titulo": titulo,
            "sample_rate": sr,
            "a4_hz": round(a4_hz, 2),
            "cents": round(cents, 2)
        }

# Lógica del botón de ejecución
if st.button("🚀 Analizar Afinación", type="primary"):
    if not url_input.strip():
        st.warning("⚠️ Por favor, ingresa una URL válida de YouTube.")
    else:
        try:
            with st.spinner("⏳ Procesando audio y analizando espectro armónico... Esto puede tomar unos segundos."):
                res = analizar_audio(url_input, duracion_analisis)
            
            st.success("¡Análisis completado con éxito!")
            if res['titulo'] != "Audio obtenido con éxito":
                st.subheader(f"📌 {res['titulo']}")
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Frecuencia A4", f"{res['a4_hz']} Hz")
            col2.metric("Desviación Cents", f"{res['cents']} cents")
            col3.metric("Sample Rate", f"{res['sample_rate']} Hz")
            
            # Evaluación del diagnóstico
            if abs(res['a4_hz'] - 432.0) <= 2.5:
                st.info("🌿 **Diagnóstico:** Afinación Verdi / 432 Hz")
            elif abs(res['a4_hz'] - 440.0) <= 2.5:
                st.info("🎵 **Diagnóstico:** Afinación Estándar ISO / 440 Hz")
            else:
                st.warning(f"🎼 **Diagnóstico:** Afinación No Estándar / Alternativa ({res['a4_hz']} Hz)")
                
        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar el video: {e}")
