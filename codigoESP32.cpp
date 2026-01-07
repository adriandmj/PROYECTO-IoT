#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"

// --- CONFIGURACIÓN WIFI Y MQTT ---
const char* ssid = "IZZI-7661";
const char* password = "My.Net2xx2";
const char* mqtt_broker = "broker.emqx.io"; // Servidor público
const char* topic_publish = "proyecto/salud/equipo_adri/datos/oxigeno"; // Tópico único
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);
MAX30105 particleSensor;

// --- VARIABLES SENSOR ---
uint32_t irBuffer[100]; 
uint32_t redBuffer[100];
int32_t bufferLength, spo2, heartRate;
int8_t validSPO2, validHeartRate;

void setup_wifi() {
  delay(10);
  Serial.print("\nConectando a "); Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi conectado. IP: "); Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    // Creamos un ID de cliente único para el broker público
    String clientId = "ESP32Client-Salud-" + String(random(0, 999));
    if (client.connect(clientId.c_str())) {
      Serial.println("conectado");
    } else {
      Serial.print("falló, rc="); Serial.print(client.state());
      Serial.println(" reintentando en 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_broker, mqtt_port);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 no encontrado.");
    while (1);
  }

  // Configuración sensor
  particleSensor.setup(60, 4, 2, 100, 411, 4096);
  Serial.println("Sensor listo. Coloca tu dedo.");
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  bufferLength = 100;
  for (byte i = 0 ; i < bufferLength ; i++) {
    while (particleSensor.available() == false) particleSensor.check();
    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();
  }

  maxim_heart_rate_and_oxygen_saturation(irBuffer, bufferLength, redBuffer, &spo2, &validSPO2, &heartRate, &validHeartRate);

  if (validHeartRate == 1 && validSPO2 == 1 && heartRate > 40 && heartRate < 130) {
    // Calculamos el promedio (usando tu lógica de suavizado)
    int finalBPM = heartRate; 
    int finalSPO2 = spo2;

    Serial.printf("Enviando -> BPM: %d, SpO2: %d%%\n", finalBPM, finalSPO2);

    // Creamos el mensaje en formato JSON para que sea fácil de leer después
    String payload = "{\"bpm\":";
    payload += finalBPM;
    payload += ", \"spo2\":";
    payload += finalSPO2;
    payload += "}";

    // Publicamos en el broker
    client.publish(topic_publish, payload.c_str());
  } else {
    Serial.println("Obteniendo señal estable...");
  }
}