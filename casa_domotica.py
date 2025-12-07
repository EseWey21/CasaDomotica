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

PUERTO = os.getenv("PUERTO", "COM9")
BAUDIOS = int(os.getenv("BAUDIOS", "9600"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    print("ERROR: No se encontró OPENWEATHER_API_KEY en el archivo .env")
    exit(1)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

DURACION_GRABACION = 3      # segundos de grabación para un comando
FRECUENCIA_MUESTREO = 16000 # Hz

# Umbral de temperatura para encender/apagar ventilador (servo)
UMBRAL_TEMPERATURA = 25.0

# ============================
# INICIALIZAR SERIAL
# ============================

ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)
time.sleep(2)  # Espera a que Arduino reinicie

# ============================
# COMANDOS BASE (1 letra = 1 acción)
# ============================

comandos = {
    "encender sala": b'A',
    "apagar sala":   b'a',

    "encender cuarto1": b'B',
    "apagar cuarto1":   b'b',

    "encender cuarto2": b'C',
    "apagar cuarto2":   b'c',

    # En modo MANUAL, estos controlan el garaje
    "encender garaje":  b'D',
    "apagar garaje":    b'd',

    # Servo (ventilador)
    "encender ventilador": b'V',
    "apagar ventilador":   b'v',

    "abrir puerta":  b'P',
    "cerrar puerta": b'p',

    # Modo automático / manual de luz del garaje (LDR en Arduino)
    "activar modo automatico luz": b'M',
    "modo automatico luz":        b'M',
    "modo automatico":            b'M',

    "desactivar modo automatico luz": b'm',
    "modo manual luz":               b'm',
    "modo manual":                   b'm',
}

# Frases alternativas que mapeamos a esos comandos
sinonimos = {
    # Sala
    "enciende sala": "encender sala",
    "prende sala":   "encender sala",
    "apaga sala":    "apagar sala",

    # Cuarto 1
    "encender cuarto uno": "encender cuarto1",
    "enciende cuarto uno": "encender cuarto1",
    "prende cuarto uno":   "encender cuarto1",
    "apaga cuarto uno":    "apagar cuarto1",
    "encender cuarto 1":   "encender cuarto1",
    "enciende cuarto 1":   "encender cuarto1",
    "prende cuarto 1":     "encender cuarto1",
    "apaga cuarto 1":      "apagar cuarto1",

    # Cuarto 2
    "encender cuarto dos": "encender cuarto2",
    "enciende cuarto dos": "encender cuarto2",
    "prende cuarto dos":   "encender cuarto2",
    "apaga cuarto dos":    "apagar cuarto2",
    "encender cuarto 2":   "encender cuarto2",
    "enciende cuarto 2":   "encender cuarto2",
    "prende cuarto 2":     "encender cuarto2",
    "apaga cuarto 2":      "apagar cuarto2",

    # Garaje / cochera (modo manual)
    "enciende cochera": "encender garaje",
    "prende cochera":   "encender garaje",
    "apaga cochera":    "apagar garaje",
    "enciende garaje":  "encender garaje",
    "prende garaje":    "encender garaje",
    "apaga garaje":     "apagar garaje",

    # Ventilador
    "enciende ventilador": "encender ventilador",
    "prende ventilador":   "encender ventilador",
    "apaga ventilador":    "apagar ventilador",

    # Puerta
    "abre puerta":       "abrir puerta",
    "abre la puerta":    "abrir puerta",
    "cierra puerta":     "cerrar puerta",
    "cierra la puerta":  "cerrar puerta",

    # Todo
    "prende todo":   "encender todo",
    "enciende todo": "encender todo",
    "apaga todo":    "apagar todo",

    # Modo automático / manual luz garaje
    "activa modo automatico luz":      "activar modo automatico luz",
    "activar modo automatico de luz":  "activar modo automatico luz",
    "activa modo automatico de luz":   "activar modo automatico luz",
    "activar modo luz automatico":     "activar modo automatico luz",

    "desactiva modo automatico luz":   "desactivar modo automatico luz",
    "desactivar modo automatico de luz": "desactivar modo automatico luz",
    "modo luz manual":                 "modo manual luz",
}

# ============================
# INTERFAZ / MENÚ
# ============================

def imprimir_banner():
    print("====================================")
    print("       CASA DOMÓTICA (Python)       ")
    print("====================================")

def imprimir_menu():
    print("\nCOMANDOS DISPONIBLES (texto o voz):")
    print(" Luces:")
    print("   - encender sala / apagar sala")
    print("   - encender cuarto1 / apagar cuarto1")
    print("   - encender cuarto2 / apagar cuarto2")
    print("   - encender garaje / apagar garaje  (solo en modo MANUAL)")
    print("")
    print(" Ventilador (servo):")
    print("   - encender ventilador / apagar ventilador")
    print("")
    print(" Puerta:")
    print("   - abrir puerta / cerrar puerta")
    print("")
    print(" Modo de luz del garaje (LDR en Arduino):")
    print("   - activar modo automatico luz")
    print("   - desactivar modo automatico luz")
    print("   - modo automatico luz / modo manual luz")
    print("")
    print(" Acciones globales:")
    print("   - encender todo / apagar todo")
    print("   - clima   (pregunta ciudad y controla ventilador)")
    print("   - leer luz (muestra valor del LDR)")
    print("")
    print(" Comandos del programa:")
    print("   - ayuda / menu  (ver esta lista)")
    print("   - modo voz / modo texto  (cambiar forma de entrada)")
    print("   - salir")
    print("------------------------------------")

imprimir_banner()
imprimir_menu()

recognizer = sr.Recognizer()

# ============================
# RECONOCIMIENTO DE VOZ
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
        sd.wait()
    except Exception as e:
        print("Error al acceder al micrófono:", e)
        return ""

    raw_data = audio.tobytes()
    audio_data = sr.AudioData(raw_data, FRECUENCIA_MUESTREO, 2)

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

# ============================
# INTERACCIÓN CON EL USUARIO
# ============================

def elegir_modo_entrada_inicial():
    while True:
        modo = input("\nElige modo de entrada [t]exto / [v]oz: ").strip().lower()
        if modo in ("t", "texto"):
            return "texto"
        if modo in ("v", "voz"):
            return "voz"
        print("Opción no válida. Escribe 't' o 'v'.")

def pedir_entrada_cruda(modo_entrada: str) -> str:
    print("\n------------------------------------")
    print(f"Modo actual de entrada: {'VOZ' if modo_entrada == 'voz' else 'TEXTO'}")
    print("Escribe un comando o 'ayuda', 'modo voz', 'modo texto', 'salir'.")
    if modo_entrada == "voz":
        return escuchar_comando()
    else:
        return input(">> ").strip().lower()

# ============================
# FUNCIONES PARA TODO ON/OFF
# ============================

def encender_todo():
    # sala, cuarto1, cuarto2, garaje, ventilador (servo), puerta
    for cmd in [b'A', b'B', b'C', b'D', b'V', b'P']:
        ser.write(cmd)
        time.sleep(0.05)
    print("Todo encendido.")

def apagar_todo():
    for cmd in [b'a', b'b', b'c', b'd', b'v', b'p']:
        ser.write(cmd)
        time.sleep(0.05)
    print("Todo apagado.")

# ============================
# LOOP PRINCIPAL
# ============================

def main():
    modo_entrada = elegir_modo_entrada_inicial()

    while True:
        texto_crudo = pedir_entrada_cruda(modo_entrada)

        if not texto_crudo:
            continue

        texto = texto_crudo.strip().lower()

        # --- Comandos de control del programa (no se mandan a Arduino) ---
        if texto in ("salir", "exit", "quit"):
            print("Cerrando programa…")
            break

        if texto in ("ayuda", "menu", "help"):
            imprimir_menu()
            continue

        if texto in ("modo voz", "cambiar a voz"):
            modo_entrada = "voz"
            print("Modo de entrada cambiado a VOZ.")
            continue

        if texto in ("modo texto", "cambiar a texto"):
            modo_entrada = "texto"
            print("Modo de entrada cambiado a TEXTO.")
            continue

        # --- Normalizar comando domótico ---
        comando = normalizar_comando(texto)

        # --- Comandos especiales de lógica propia ---
        if comando == "clima":
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

            # LÓGICA DE TEMPERATURA + SERVO (VENTILADOR)
            if temp is not None:
                if temp >= UMBRAL_TEMPERATURA:
                    print(f"\nHace calor (≥ {UMBRAL_TEMPERATURA} °C), activando ventilador (servo) y alarma...")
                    ser.write(b'V')  # Encender ventilador
                    time.sleep(0.1)
                    ser.write(b'H')  # Alarma de temperatura (buzzer)
                else:
                    print(f"\nHace fresco (< {UMBRAL_TEMPERATURA} °C), apagando ventilador (servo)...")
                    ser.write(b'v')  # Apagar ventilador

            continue

        if comando == "leer luz":
            ser.write(b'L')
            time.sleep(0.1)
            respuesta = ser.readline().decode().strip()
            print("Valor LDR:", respuesta)
            continue

        if comando == "encender todo":
            encender_todo()
            continue

        if comando == "apagar todo":
            apagar_todo()
            continue

        # --- Comando domótico simple que mapea a una letra ---
        if comando in comandos:
            ser.write(comandos[comando])
        else:
            print("Comando no reconocido:", texto_crudo)

if __name__ == "__main__":
    main()
