import streamlit as st
import os
import sys
import tempfile
import librosa
import yt_dlp

st.set_page_config(page_title="Analizador de Afinación A4", page_icon="🎵", layout="centered")

st.title("🎵 Analizador de Afinación de YouTube")
st.markdown("Ingresa un enlace de YouTube para detectar si la música está en **432 Hz**, **440 Hz (Estándar)** u otra frecuencia.")

# Formulario de entrada
url_input = st.text_input("URL del Video de YouTube:", placeholder="https://www.youtube.com/watch?v=...")
duracion_analisis = st.slider("Segundos de audio a analizar:", min_value=15, max_value=90, value=45, step=5)

def analizar_audio(url, duracion):
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_filepath = os.path.join(tmp_dir, "audio_temp.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_filepath,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
            'extractor_args': {
                'youtube': {'player_client': ['mweb', 'android', 'ios', 'web']}
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
        archivo_wav = None
        for file in os.listdir(tmp_dir):
            if file.endswith('.wav'):
                archivo_wav = os.path.join(tmp_dir, file)
                break
                
        if not archivo_wav:
            raise Exception("No se pudo procesar el archivo WAV.")

        y, sr = librosa.load(archivo_wav, sr=None, mono=True, duration=duracion)
        tuning_offset = librosa.estimate_tuning(y=y, sr=sr)
        a4_hz = 440.0 * (2.0 ** (tuning_offset / 12.0))
        cents = tuning_offset * 100.0
        
        return {
            "titulo": info.get('title', 'Desconocido'),
            "duracion_total": info.get('duration', 0),
            "sample_rate": sr,
            "a4_hz": round(a4_hz, 2),
            "cents": round(cents, 2)
        }

if st.button("🚀 Analizar Afinación", type="primary"):
    if not url_input.strip():
        st.warning("⚠️ Por favor, ingresa una URL válida.")
    else:
        try:
            with st.spinner("⏳ Descargando audio y procesando armónicos... Esto puede tardar 15-30 segundos."):
                res = analizar_audio(url_input, duracion_analisis)
            
            st.success("¡Análisis completado!")
            st.subheader(f"📌 {res['titulo']}")
            
            # Métricas en columnas
            col1, col2, col3 = st.columns(3)
            col1.metric("Frecuencia A4", f"{res['a4_hz']} Hz")
            col2.metric("Desviación Cents", f"{res['cents']} cents")
            col3.metric("Sample Rate", f"{res['sample_rate']} Hz")
            
            # Diagnóstico visual
            if abs(res['a4_hz'] - 432.0) <= 2.5:
                st.info("🌿 **Diagnóstico:** Afinación Verdi / 432 Hz")
            elif abs(res['a4_hz'] - 440.0) <= 2.5:
                st.info("🎵 **Diagnóstico:** Afinación Estándar ISO / 440 Hz")
            else:
                st.warning(f"🎼 **Diagnóstico:** Afinación No Estándar ({res['a4_hz']} Hz)")
                
        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar el video: {e}")
