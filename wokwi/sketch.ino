/*
 * ESP32 alert-node simulation for Wokwi.
 *
 * MQTT/Serial commands: NORMAL, WARNING, DROWSY, TAMPER
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

enum SystemState { NORMAL, WARNING, DROWSY, TAMPER };

const int GREEN_LED = 4;
const int YELLOW_LED = 5;
const int RED_LED = 2;
const int BUZZER = 18;
const int BUZZER_CHANNEL = 0;
const char *FIRMWARE_VERSION = "5-mqtt-ledc-buzzer";
const char *MQTT_HOST = "host.wokwi.internal";
const int MQTT_PORT = 1883;
const char *COMMAND_TOPIC = "driver/LAPTOP-CAM-01/command";
const char *ACK_TOPIC = "driver/LAPTOP-CAM-01/ack";

SystemState currentState = NORMAL;
String serialBuffer;
unsigned long lastBlink = 0;
unsigned long lastStatusLog = 0;
bool blinkPhase = false;
WiFiClient networkClient;
PubSubClient mqttClient(networkClient);
unsigned long lastMqttAttempt = 0;

const char *stateName(SystemState state) {
  switch (state) {
    case NORMAL: return "NORMAL";
    case WARNING: return "WARNING";
    case DROWSY: return "DROWSY";
    case TAMPER: return "TAMPER";
  }
  return "UNKNOWN";
}

void clearOutputs() {
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED, LOW);
  ledcWriteTone(BUZZER_CHANNEL, 0);
}

void setState(SystemState nextState) {
  if (nextState == currentState) return;
  currentState = nextState;
  clearOutputs();
  if (currentState == DROWSY) {
    ledcWriteTone(BUZZER_CHANNEL, 1800);
  } else if (currentState == TAMPER) {
    ledcWriteTone(BUZZER_CHANNEL, 2400);
  }
  Serial.print("STATE=");
  Serial.println(stateName(currentState));
}

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();
  bool accepted = true;
  if (command == "NORMAL") setState(NORMAL);
  else if (command == "WARNING") setState(WARNING);
  else if (command == "DROWSY") setState(DROWSY);
  else if (command == "TAMPER") setState(TAMPER);
  else if (command.length()) {
    accepted = false;
    Serial.print("UNKNOWN_COMMAND=");
    Serial.println(command);
  }
  if (accepted && command.length()) {
    Serial.print("ACK STATE=");
    Serial.println(stateName(currentState));
  }
}

void onMqttMessage(char *topic, byte *payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) message += (char)payload[i];
  int separator = message.indexOf('|');
  if (separator < 1) {
    Serial.println("MQTT invalid command payload");
    return;
  }
  String requestId = message.substring(0, separator);
  String command = message.substring(separator + 1);
  handleCommand(command);
  String ack = requestId + "|ACK STATE=" + stateName(currentState);
  mqttClient.publish(ACK_TOPIC, ack.c_str());
  Serial.print("MQTT ACK -> ");
  Serial.println(ack);
}

void connectMqtt() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) return;
  unsigned long now = millis();
  if (now - lastMqttAttempt < 2000) return;
  lastMqttAttempt = now;
  String clientId = "wokwi-esp32-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.print("Connecting MQTT to ");
  Serial.print(MQTT_HOST);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  if (mqttClient.connect(clientId.c_str())) {
    mqttClient.subscribe(COMMAND_TOPIC, 1);
    Serial.print("MQTT ready; subscribed to ");
    Serial.println(COMMAND_TOPIC);
  } else {
    Serial.print("MQTT connect failed, rc=");
    Serial.println(mqttClient.state());
  }
}

void readSerialCommands() {
  while (Serial.available()) {
    char value = Serial.read();
    if (value == '\n' || value == '\r') {
      if (serialBuffer.length()) {
        handleCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += value;
    }
  }
}

void updateOutputs() {
  unsigned long now = millis();
  bool blinkChanged = false;
  if (now - lastBlink >= 300) {
    lastBlink = now;
    blinkPhase = !blinkPhase;
    blinkChanged = true;
  }

  switch (currentState) {
    case NORMAL:
      digitalWrite(GREEN_LED, HIGH);
      digitalWrite(YELLOW_LED, LOW);
      digitalWrite(RED_LED, LOW);
      break;
    case WARNING:
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, blinkPhase);
      digitalWrite(RED_LED, LOW);
      break;
    case DROWSY:
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, LOW);
      digitalWrite(RED_LED, HIGH);
      break;
    case TAMPER:
      digitalWrite(GREEN_LED, LOW);
      digitalWrite(YELLOW_LED, !blinkPhase);
      digitalWrite(RED_LED, blinkPhase);
      if (blinkChanged) {
        if (blinkPhase) ledcWriteTone(BUZZER_CHANNEL, 2400);
        else ledcWriteTone(BUZZER_CHANNEL, 0);
      }
      break;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  ledcSetup(BUZZER_CHANNEL, 1800, 8);
  ledcAttachPin(BUZZER, BUZZER_CHANNEL);
  clearOutputs();
  // Startup self-test: confirms that Wokwi/VS Code audio is enabled.
  ledcWriteTone(BUZZER_CHANNEL, 1200);
  delay(350);
  ledcWriteTone(BUZZER_CHANNEL, 0);
  Serial.println("ESP32 DRIVER ALERT NODE READY");
  Serial.println("Commands: NORMAL, WARNING, DROWSY, TAMPER");
  WiFi.mode(WIFI_STA);
  WiFi.begin("Wokwi-GUEST", "", 6);
  Serial.print("Connecting to Wokwi-GUEST");
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi ready: ");
  Serial.println(WiFi.localIP());
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  Serial.print("Firmware: ");
  Serial.println(FIRMWARE_VERSION);
  connectMqtt();
}

void loop() {
  readSerialCommands();
  connectMqtt();
  mqttClient.loop();
  updateOutputs();
  unsigned long now = millis();
  if (now - lastStatusLog >= 2000) {
    lastStatusLog = now;
    Serial.print("HEARTBEAT STATE=");
    Serial.println(stateName(currentState));
  }
  delay(10);
}
