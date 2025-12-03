# Casa Domótica (Arduino + Python)

Controla luces, ventilador y puerta con Arduino, y un cliente Python que acepta comandos por voz o texto. Además, integra clima con OpenWeather para activar el ventilador y alarma si hace calor.

## Componentes
- Arduino UNO/Nano (u otro compatible)
- LEDs para: sala (D2), cuarto1 (D3), cuarto2 (D4), garaje (D5), ventilador (D6), puerta (D7)
- Buzzer piezo: `D11`
- Sensor ultrasónico HC-SR04: `TRIG D9`, `ECHO D10`
- LDR + divisor resistivo: `A0`

## Cableado rápido
- LEDs: cada LED con resistencia serie (220–330 Ω) en pines `2,3,4,5,6,7` → GND
- Buzzer: pin `11` → buzzer (+), buzzer (−) → GND
- HC-SR04: `Vcc 5V`, `GND`, `TRIG D9`, `ECHO D10`
- LDR: formar divisor a `A0` (ej. LDR a 5V y resistencia a GND, unión a `A0`)

Los pines están definidos en `casa/casa.ino`:
```
LED_SALA    = 2
LED_CUARTO1 = 3
LED_CUARTO2 = 4
LED_GARAJE  = 5
LED_VENT    = 6
LED_PUERTA  = 7
BUZZER_PIN  = 11
TRIG_PIN    = 9
ECHO_PIN    = 10
LDR_PIN     = A0
```

## Software
- Arduino sketch: `casa/casa.ino`
- Python cliente: `casa_domotica.py`

### 1) Subir el sketch a Arduino
1. Abre `casa/casa.ino` en Arduino IDE.
2. Selecciona tu placa y puerto.
3. Compila y sube.

El sketch expone comandos por Serial (9600 baudios) y lógica automática:
- Comandos serial: `A/a` sala, `B/b` cuarto1, `C/c` cuarto2, `D/d` garaje, `V/v` ventilador, `P/p` puerta, `H` alarma, `L` leer LDR, `R` leer distancia.
- Automático: si es de noche (LDR bajo) y alguien está cerca (<30 cm) y la puerta está cerrada, enciende sala y suena un aviso.

### 2) Configurar Python en Windows
Requisitos:
- Python 3.9+ instalado
- Drivers del puerto serial (Arduino)

Desde PowerShell en la carpeta `Memo`:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pyserial requests SpeechRecognition sounddevice numpy python-dotenv
```

### 3) Archivo .env
Crea `Memo/.env` con:
```
PUERTO=COM9
BAUDIOS=9600
OPENWEATHER_API_KEY=tu_api_key_aqui
```
- `PUERTO`: cambia a tu puerto (ver en Arduino IDE o Administrador de dispositivos).
- Obtén la API key en https://openweathermap.org/api

## Uso del cliente
Ejecuta:
```powershell
.\.venv\Scripts\Activate.ps1
python casa_domotica.py
```
Verás el menú de comandos por voz o texto.

### Comandos disponibles
- Luces: `encender sala`, `apagar sala`, `encender cuarto1`, `apagar cuarto1`, `encender cuarto2`, `apagar cuarto2`, `encender garaje`, `apagar garaje`
- Ventilador: `encender ventilador`, `apagar ventilador`
- Puerta: `abrir puerta`, `cerrar puerta`
- Grupo: `encender todo`, `apagar todo`
- Sensores: `leer luz`, `leer distancia`
- Clima: `clima` (pide ciudad); si `temp >= 25°C` enciende ventilador y manda alarma `H`
- Salir: `salir`

También entiende varios sinónimos ("prende sala", "apaga cochera", etc.). El modo "voz" usa `sounddevice` + `SpeechRecognition` (servicio de Google) y el modo "texto" evita el micrófono.

## Solución de problemas
- No conecta por serial: verifica `PUERTO` en `.env` y que Arduino esté a 9600.
- Voz no funciona: prueba modo texto (`t`), revisa permisos de micrófono y que el dispositivo de entrada esté activo.
- Error de OpenWeather 401: confirma tu API key en `.env`.
- Lecturas extrañas del LDR/ultrasonido: revisa cableado, resistencias y alimentación.

## Licencia
Uso educativo/demostrativo.
