import serial
import time
import requests
import speech_recognition as sr
import sounddevice as sd
import numpy as np
from dotenv import load_dotenv
import os

# ============================
# CARGAR VARIABLES DEL .env
# ============================

load_dotenv()  # Carga automáticamente el archivo .env

PUERTO = os.getenv("PUERTO", "COM9")          # Si no existe, usa COM9
BAUDIOS = int(os.getenv("BAUDIOS", "9600"))   # Si no existe, usa 9600
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    print("ERROR: No se encontró OPENWEATHER_API_KEY en el archivo .env")
    exit(1)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

DURACION_GRABACION = 3     # segundos de grabación para un comando
FRECUENCIA_MUESTREO = 16000 # Hz

# Umbral de temperatura para encender/apagar ventilador
UMBRAL_TEMPERATURA = 25.0

# ============================
# INICIALIZAR SERIAL
# ============================

ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)
time.sleep(2)  # Espera a que Arduino reinicie

# Comandos base que entiende Arduino (1 letra = 1 acción)
comandos = {
    "encender sala": b'A',
    "apagar sala":   b'a',

    "encender cuarto1": b'B',
    "apagar cuarto1":   b'b',

    "encender cuarto2": b'C',
    "apagar cuarto2":   b'c',

    "encender garaje":  b'D',
    "apagar garaje":    b'd',

    "encender ventilador": b'V',
    "apagar ventilador":   b'v',

    "abrir puerta":  b'P',
    "cerrar puerta": b'p',
}

# Frases alternativas que mapeamos a esos comandos
sinonimos = {
    "enciende sala": "encender sala",
    "prende sala": "encender sala",
    "apaga sala": "apagar sala",

    "encender cuarto uno": "encender cuarto1",
    "enciende cuarto uno": "encender cuarto1",
    "prende cuarto uno": "encender cuarto1",
    "apaga cuarto uno": "apagar cuarto1",
    "encender cuarto 1": "encender cuarto1",
    "enciende cuarto 1": "encender cuarto1",
    "prende cuarto 1": "encender cuarto1",
    "apaga cuarto 1": "apagar cuarto1",

    "encender cuarto dos": "encender cuarto2",
    "enciende cuarto dos": "encender cuarto2",
    "prende cuarto dos": "encender cuarto2",
    "apaga cuarto dos": "apagar cuarto2",
    "encender cuarto 2": "encender cuarto2",
    "enciende cuarto 2": "encender cuarto2",
    "prende cuarto 2": "encender cuarto2",
    "apaga cuarto 2": "apagar cuarto2",

    "enciende cochera": "encender garaje",
    "prende cochera": "encender garaje",
    "apaga cochera": "apagar garaje",
    "enciende garaje": "encender garaje",
    "prende garaje": "encender garaje",
    "apaga garaje": "apagar garaje",

    "enciende ventilador": "encender ventilador",
    "prende ventilador": "encender ventilador",
    "apaga ventilador": "apagar ventilador",

    "abre puerta": "abrir puerta",
    "abre la puerta": "abrir puerta",
    "cierra puerta": "cerrar puerta",
    "cierra la puerta": "cerrar puerta",

    "prende todo": "encender todo",
    "enciende todo": "encender todo",
    "apaga todo": "apagar todo",
}

print("====================================")
print("  CASA DOMÓTICA CONTROL (Python)    ")
print("====================================")
print("Comandos por VOZ o TEXTO:")
print(" - encender sala / apagar sala")
print(" - encender cuarto1 / apagar cuarto1")
print(" - encender cuarto2 / apagar cuarto2")
print(" - encender garaje / apagar garaje")
print(" - encender ventilador / apagar ventilador")
print(" - abrir puerta / cerrar puerta")
print(" - encender todo / apagar todo")
print(" - clima  (pregunta ciudad)")
print(" - leer luz")
print(" - leer distancia")
print(" - salir")
print("------------------------------------")

recognizer = sr.Recognizer()

# ============================
# RECONOCIMIENTO DE VOZ (sin PyAudio)
# ============================

def escuchar_comando():
    """Graba unos segundos desde el micrófono con sounddevice y devuelve texto."""
    print(f"\nHabla en cuanto veas este mensaje (tienes {DURACION_GRABACION} s)...")
    try:
        audio = sd.rec(
            int(DURACION_GRABACION * FRECUENCIA_MUESTREO),
            samplerate=FRECUENCIA_MUESTREO,
            channels=1,
            dtype='int16'
        )
        sd.wait()  # Espera a que termine la grabación
    except Exception as e:
        print("Error al acceder al micrófono:", e)
        return ""

    raw_data = audio.tobytes()
    audio_data = sr.AudioData(raw_data, FRECUENCIA_MUESTREO, 2)  # 2 bytes por muestra (int16)

    try:
        texto = recognizer.recognize_google(audio_data, language="es-MX")
        print("Has dicho:", texto)
        return texto.lower()
    except sr.UnknownValueError:
        print("No entendí lo que dijiste")
        return ""
    except sr.RequestError as e:
        print("Error con el servicio de reconocimiento de voz:", e)
        return ""

# ============================
# CLIMA (OpenWeather)
# ============================

def obtener_clima(ciudad: str):
    aliases = {
        "cdmx": "Mexico City,MX",
        "ciudad de mexico": "Mexico City,MX",
        "méxico": "Mexico City,MX",
        "mexico": "Mexico City,MX",
        "tokio": "Tokyo,JP",
    }

    ciudad_normalizada = ciudad.strip().lower()
    consulta = aliases.get(ciudad_normalizada, ciudad)

    params = {
        "q": consulta,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "es",
    }

    try:
        resp = requests.get(OPENWEATHER_URL, params=params, timeout=5)
    except requests.RequestException as e:
        print("Error de red al consultar OpenWeather:", e)
        return None

    if resp.status_code == 401:
        print("Error 401: problema con la API key.")
        return None
    if resp.status_code == 404:
        print(f"Ciudad no encontrada para: '{ciudad}' (se envió '{consulta}')")
        return None
    if resp.status_code != 200:
        print(f"Error {resp.status_code} al consultar OpenWeather.")
        print("Respuesta:", resp.text)
        return None

    data = resp.json()

    if "main" not in data or "weather" not in data:
        print("Respuesta inesperada de la API:", data)
        return None

    temp = data["main"].get("temp")
    sens = data["main"].get("feels_like")
    desc_list = data.get("weather", [])
    desc = desc_list[0].get("description") if desc_list else "Sin descripción"

    return {
        "temp": temp,
        "sensacion": sens,
        "descripcion": desc,
        "ciudad": data.get("name", consulta)
    }

# ============================
# NORMALIZAR COMANDO
# ============================

def normalizar_comando(texto: str) -> str:
    texto = texto.strip().lower()
    if texto in comandos:
        return texto
    if texto in sinonimos:
        return sinonimos[texto]
    return texto

def pedir_comando():
    """Pregunta si quieres voz o texto y devuelve el comando normalizado."""
    modo = input("\n¿Usar voz o texto? (v/t): ").strip().lower()
    if modo == "v":
        texto = escuchar_comando()
        return normalizar_comando(texto)
    else:
        texto = input("Escribe un comando: ").strip().lower()
        return normalizar_comando(texto)

# ============================
# FUNCIONES PARA TODO ON/OFF
# ============================

def encender_todo():
    """Enciende todas las luces, ventilador y abre la puerta."""
    # Orden: sala, cuarto1, cuarto2, garaje, ventilador, puerta
    for cmd in [b'A', b'B', b'C', b'D', b'V', b'P']:
        ser.write(cmd)
        time.sleep(0.05)
    print("Todo encendido (luces, ventilador, puerta abierta).")

def apagar_todo():
    """Apaga todas las luces, ventilador y cierra la puerta."""
    for cmd in [b'a', b'b', b'c', b'd', b'v', b'p']:
        ser.write(cmd)
        time.sleep(0.05)
    print("Todo apagado (luces, ventilador, puerta cerrada).")

# ============================
# LOOP PRINCIPAL
# ============================

while True:
    texto = pedir_comando()

    if not texto:
        continue

    if texto == "salir":
        print("Cerrando programa…")
        break

    elif texto == "clima":
        ciudad = input("Ciudad: ").strip()
        if not ciudad:
            print("No escribiste ciudad.")
            continue

        info = obtener_clima(ciudad)
        if info is None:
            continue

        temp = info["temp"]
        sens = info["sensacion"]
        desc = info["descripcion"]
        nombre_ciudad = info["ciudad"]

        print(f"\nClima en {nombre_ciudad}:")
        print(f" - Temperatura: {temp:.1f} °C")
        print(f" - Sensación térmica: {sens:.1f} °C")
        print(f" - Descripción: {desc}")

        # Lógica domótica con umbral 25 °C:
        if temp is not None:
            if temp >= UMBRAL_TEMPERATURA:
                print(f"\nHace calor (≥ {UMBRAL_TEMPERATURA} °C), activando ventilador y alarma en la casa...")
                ser.write(b'V')  # Encender ventilador
                time.sleep(0.1)
                ser.write(b'H')  # Alarma de temperatura
            else:
                print(f"\nHace fresco (< {UMBRAL_TEMPERATURA} °C), apagando ventilador si estaba encendido...")
                ser.write(b'v')  # Apagar ventilador

    elif texto == "leer luz":
        ser.write(b'L')
        time.sleep(0.1)
        respuesta = ser.readline().decode().strip()
        print("Valor LDR:", respuesta)

    elif texto == "leer distancia":
        ser.write(b'R')
        time.sleep(0.1)
        respuesta = ser.readline().decode().strip()
        print("Distancia:", respuesta, "cm")

    elif texto == "encender todo":
        encender_todo()

    elif texto == "apagar todo":
        apagar_todo()

    elif texto in comandos:
        ser.write(comandos[texto])

    else:
        print("Comando no reconocido:", texto)
