const int LED_SALA    = 2;
const int LED_CUARTO1 = 3;
const int LED_CUARTO2 = 4;
const int LED_GARAJE  = 5;
const int LED_VENT    = 6;
const int LED_PUERTA  = 7;

const int BUZZER_PIN  = 11;

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;

const int LDR_PIN  = A0;

const int LDR_UMBRAL_NOCHE = 400;
const long DIST_UMBRAL_PUERTA = 30;

bool puertaAbierta = false;

void setup() {
  Serial.begin(9600);

  pinMode(LED_SALA,    OUTPUT);
  pinMode(LED_CUARTO1, OUTPUT);
  pinMode(LED_CUARTO2, OUTPUT);
  pinMode(LED_GARAJE,  OUTPUT);
  pinMode(LED_VENT,    OUTPUT);
  pinMode(LED_PUERTA,  OUTPUT);

  pinMode(BUZZER_PIN, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  apagarTodo();
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    procesarComando(c);
  }

  comportamientoAutomatico();
  delay(50);
}

void apagarTodo() {
  digitalWrite(LED_SALA,    LOW);
  digitalWrite(LED_CUARTO1, LOW);
  digitalWrite(LED_CUARTO2, LOW);
  digitalWrite(LED_GARAJE,  LOW);
  digitalWrite(LED_VENT,    LOW);
  digitalWrite(LED_PUERTA,  LOW);
  noTone(BUZZER_PIN);
}

void procesarComando(char c) {
  switch (c) {
    case 'A': digitalWrite(LED_SALA, HIGH);  beepCorto(); break;
    case 'a': digitalWrite(LED_SALA, LOW);   beepCorto(); break;

    case 'B': digitalWrite(LED_CUARTO1, HIGH); beepCorto(); break;
    case 'b': digitalWrite(LED_CUARTO1, LOW);  beepCorto(); break;

    case 'C': digitalWrite(LED_CUARTO2, HIGH); beepCorto(); break;
    case 'c': digitalWrite(LED_CUARTO2, LOW);  beepCorto(); break;

    case 'D': digitalWrite(LED_GARAJE, HIGH);  beepCorto(); break;
    case 'd': digitalWrite(LED_GARAJE, LOW);   beepCorto(); break;

    case 'V': digitalWrite(LED_VENT, HIGH); beepCorto(); break;
    case 'v': digitalWrite(LED_VENT, LOW);  beepCorto(); break;

    case 'P': abrirPuerta();  break;
    case 'p': cerrarPuerta(); break;

    case 'H': alarmaTemperatura(); break;

    case 'L': {
      int luz = analogRead(LDR_PIN);
      Serial.println(luz);
      break;
    }

    case 'R': {
      long dist = medirDistancia();
      Serial.println(dist);
      break;
    }
  }
}

void beepCorto() {
  tone(BUZZER_PIN, 2000, 100);
  delay(120);
}

void abrirPuerta() {
  digitalWrite(LED_PUERTA, HIGH);
  puertaAbierta = true;
  tone(BUZZER_PIN, 1500, 200);
  delay(220);
}

void cerrarPuerta() {
  digitalWrite(LED_PUERTA, LOW);
  puertaAbierta = false;
  tone(BUZZER_PIN, 800, 200);
  delay(220);
}

void alarmaTemperatura() {
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 2500);
    delay(200);
    noTone(BUZZER_PIN);
    delay(150);
  }
}

long medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);
  long distancia = duracion / 58;

  return distancia;
}

void comportamientoAutomatico() {
  int luz = analogRead(LDR_PIN);
  long dist = medirDistancia();

  bool esNoche = (luz < LDR_UMBRAL_NOCHE);
  bool alguienEnPuerta = (dist > 0 && dist < DIST_UMBRAL_PUERTA);

  if (esNoche && alguienEnPuerta && !puertaAbierta) {
    digitalWrite(LED_SALA, HIGH);

    tone(BUZZER_PIN, 1000);
    delay(150);
    tone(BUZZER_PIN, 1500);
    delay(150);
    noTone(BUZZER_PIN);
  }
}
