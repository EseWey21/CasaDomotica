#include <Servo.h>

// =====================
// Pines de salida
// =====================
const int LED_SALA       = 2;
const int LED_CUARTO1    = 3;
const int LED_CUARTO2    = 4;
const int LED_GARAJE     = 5;
const int SERVO_VENT_PIN = 6;   // Servo SG90 (ventilador)
const int LED_PUERTA     = 7;

const int BUZZER_PIN     = 11;

// LDR (sensor de luz)
const int LDR_PIN        = A0;

// =====================
// Servo (ventilador)
// =====================
Servo servoVent;
bool ventiladorEncendido = false;   // estado del ventilador

int anguloServo = 0;                // ángulo actual del servo
int pasoServo   = 6;                // cuánto cambia cada actualización (velocidad)
unsigned long ultimoMovimientoServo = 0;
const unsigned long INTERVALO_SERVO = 5; // ms entre movimientos (más chico = más rápido)

// =====================
// LDR → luz automática del garaje + buzzer en cambios
// =====================
int UMBRAL_OBSCURIDAD = 600;          // menos de 600 = consideramos obscuridad
unsigned long ultimoLDR = 0;
const unsigned long INTERVALO_LDR = 200; // ms entre lecturas de luz

bool estadoOscuro = false;           // estado anterior: estaba oscuro o no

// Modo automático / manual del garaje
bool modoAutomaticoGaraje = false;   // false = manual (D/d), true = automático (LDR)

// =====================
// Prototipos
// =====================
void actualizarServoVentilador();
void sonarAlarma();
void controlarLuzPorLDR();

// ======== TONOS PERSONALIZADOS ========

void beepTono(int freq, int dur) {
  tone(BUZZER_PIN, freq, dur);
  delay(dur + 10);
}

void sonidoEncender() {          // 🔔 Encender luz
  beepTono(1200, 80);
}

void sonidoApagar() {            // 🔕 Apagar luz
  beepTono(600, 80);
}

void sonidoAbrirPuerta() {       // 🚪 Abrir puerta
  beepTono(700, 150);
}

void sonidoCerrarPuerta() {      // 🚪 Cerrar puerta
  beepTono(900, 80);
}

void sonidoVentiladorOn() {      // 🌀 Encender ventilador
  beepTono(900, 60);
  beepTono(1200, 60);
}

void sonidoVentiladorOff() {     // 🌀 Apagar ventilador
  beepTono(1200, 60);
  beepTono(900, 60);
}

void sonidoModoAutomatico() {    // 🌗 Activar automático
  beepTono(1100, 60);
  beepTono(1300, 60);
}

void sonidoModoManual() {        // 🌗 Desactivar automático
  beepTono(700, 60);
  beepTono(500, 60);
}

void beepCambioLuz() {           // 🔦 Cambio por LDR
  beepTono(800, 80);
}

// =====================
// Setup
// =====================
void setup() {
  Serial.begin(9600);

  pinMode(LED_SALA,    OUTPUT);
  pinMode(LED_CUARTO1, OUTPUT);
  pinMode(LED_CUARTO2, OUTPUT);
  pinMode(LED_GARAJE,  OUTPUT);
  pinMode(LED_PUERTA,  OUTPUT);
  pinMode(BUZZER_PIN,  OUTPUT);
  // LDR en A0 es entrada analógica por defecto

  // Servo
  servoVent.attach(SERVO_VENT_PIN);
  servoVent.write(0);  // posición inicial (ventilador "apagado")

  // Todo apagado al inicio
  digitalWrite(LED_SALA,    LOW);
  digitalWrite(LED_CUARTO1, LOW);
  digitalWrite(LED_CUARTO2, LOW);
  digitalWrite(LED_GARAJE,  LOW);
  digitalWrite(LED_PUERTA,  LOW);
  digitalWrite(BUZZER_PIN,  LOW);
}

// =====================
// Loop principal
// =====================
void loop() {
  // 1) Procesar comandos recibidos por Serial desde Python
  if (Serial.available() > 0) {
    char cmd = (char)Serial.read();

    switch (cmd) {
      // ===== Luces habitaciones =====
      case 'A':
        digitalWrite(LED_SALA, HIGH);
        sonidoEncender();
        break;

      case 'a':
        digitalWrite(LED_SALA, LOW);
        sonidoApagar();
        break;

      case 'B':
        digitalWrite(LED_CUARTO1, HIGH);
        sonidoEncender();
        break;

      case 'b':
        digitalWrite(LED_CUARTO1, LOW);
        sonidoApagar();
        break;

      case 'C':
        digitalWrite(LED_CUARTO2, HIGH);
        sonidoEncender();
        break;

      case 'c':
        digitalWrite(LED_CUARTO2, LOW);
        sonidoApagar();
        break;

      // ===== Garaje (solo funciona si estamos en modo MANUAL) =====
      case 'D':
        if (!modoAutomaticoGaraje) {
          digitalWrite(LED_GARAJE, HIGH);
          sonidoEncender();
        }
        break;

      case 'd':
        if (!modoAutomaticoGaraje) {
          digitalWrite(LED_GARAJE, LOW);
          sonidoApagar();
        }
        break;

      // ===== Ventilador (servo) =====
      case 'V':
        // Encender ventilador → empezamos a mover el servo en actualizarServoVentilador()
        ventiladorEncendido = true;
        sonidoVentiladorOn();
        break;

      case 'v':
        // Apagar ventilador → detener servo y llevarlo a 0°
        ventiladorEncendido = false;
        anguloServo = 0;
        pasoServo   = 6;
        servoVent.write(0);
        sonidoVentiladorOff();
        break;

      // ===== Puerta (LED) =====
      case 'P':
        // Abrir puerta
        digitalWrite(LED_PUERTA, HIGH);
        sonidoAbrirPuerta();
        break;

      case 'p':
        // Cerrar puerta
        digitalWrite(LED_PUERTA, LOW);
        sonidoCerrarPuerta();
        break;

      // ===== Alarma (buzzer) – comando 'H' desde Python =====
      case 'H':
        sonarAlarma();
        break;

      // ===== Lectura LDR para Python (comando 'L') =====
      case 'L': {
        int luz = analogRead(LDR_PIN);
        Serial.println(luz);   // Python leerá este valor con readline()
        break;
      }

      // ===== Modo automático ON (M) / OFF (m) para la luz del garaje =====
      case 'M':
        modoAutomaticoGaraje = true;
        // opcional: poner estadoOscuro inicial según lectura actual
        estadoOscuro = (analogRead(LDR_PIN) < UMBRAL_OBSCURIDAD);
        sonidoModoAutomatico();
        break;

      case 'm':
        modoAutomaticoGaraje = false;
        // opcional: apagar garaje al salir de modo automático
        // digitalWrite(LED_GARAJE, LOW);
        sonidoModoManual();
        break;

      default:
        // Comando no reconocido: no hacemos nada
        break;
    }
  }

  // 2) Actualizar movimiento del servo si el ventilador está encendido
  actualizarServoVentilador();

  // 3) Control automático de la luz del garaje con el LDR + buzzer en cambios
  controlarLuzPorLDR();
}

// =====================
// Movimiento continuo del servo (simula ventilador)
// =====================
void actualizarServoVentilador() {
  if (!ventiladorEncendido) {
    return;  // si está apagado, no movemos nada
  }

  unsigned long ahora = millis();
  if (ahora - ultimoMovimientoServo >= INTERVALO_SERVO) {
    ultimoMovimientoServo = ahora;

    // Barrido 0 -> 180 -> 0 -> 180 ...
    anguloServo += pasoServo;

    if (anguloServo >= 180 || anguloServo <= 0) {
      pasoServo = -pasoServo;  // invierte la dirección
    }

    servoVent.write(anguloServo);
  }
}

// =====================
// Alarma con el buzzer (para 'H')
// =====================
void sonarAlarma() {
  // Ejemplo simple: 3 beeps rápidos
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
  }
}

// =====================
// Control automático de luz del garaje con el LDR
// + Buzzer cuando cambie el estado
// Solo actúa si modoAutomaticoGaraje == true
// =====================
void controlarLuzPorLDR() {
  if (!modoAutomaticoGaraje) {
    return;  // En modo manual no hacemos nada con el LDR
  }

  unsigned long ahora = millis();

  if (ahora - ultimoLDR >= INTERVALO_LDR) {
    ultimoLDR = ahora;

    int valor = analogRead(LDR_PIN);

    // Determinar si está oscuro según el umbral
    bool oscuro = (valor < UMBRAL_OBSCURIDAD);

    // Si hubo cambio de estado (luz -> oscuro o oscuro -> luz)
    if (oscuro != estadoOscuro) {
      estadoOscuro = oscuro;

      // Cambia la luz del garaje y hace beep
      if (oscuro) {
        // Ahora está oscuro → encender garaje
        digitalWrite(LED_GARAJE, HIGH);
      } else {
        // Ahora hay luz → apagar garaje
        digitalWrite(LED_GARAJE, LOW);
      }

      // Beep por cambio de estado (tono especial LDR)
      beepCambioLuz();
    } else {
      // Si no hubo cambio, mantenemos el estado acorde al modo automático
      if (oscuro) {
        digitalWrite(LED_GARAJE, HIGH);
      } else {
        digitalWrite(LED_GARAJE, LOW);
      }
    }

    // Debug opcional:
    // Serial.print("LDR: ");
    // Serial.print(valor);
    // Serial.print("  oscuro: ");
    // Serial.println(oscuro ? "SI" : "NO");
  }
}
