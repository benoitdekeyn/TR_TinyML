#include <Arduino.h>
#include <time.h>
#include "serial.h"

// Horloge logicielle : date par défaut 2000-01-01 00:00:00, mise à jour par "date:YYYYMMDDHHMMSS"
static time_t baseEpoch = 946684800; // 2000-01-01 00:00:00 UTC
static uint32_t baseMillis = 0; // Temps en millisecondes correspondant à baseEpoch
static char cmdBuf[32]; // Buffer pour stocker la commande reçue via le port série
static uint8_t cmdLen = 0; // Longueur actuelle de la commande dans le buffer

void serialBegin() {
  Serial.begin(115200);
  while (!Serial);
}


// Pour mettre à jour la date et l'heure du système
// depuis un message serial au format "date:YYYYMMDDHHMMSS"
static void setDate(const char* s) {
  int Y, M, D, h, m, sec;
  if (sscanf(s, "%4d%2d%2d%2d%2d%2d", &Y, &M, &D, &h, &m, &sec) != 6) return;
  struct tm t = {};
  t.tm_year = Y - 1900; t.tm_mon = M - 1; t.tm_mday = D;
  t.tm_hour = h; t.tm_min = m; t.tm_sec = sec;
  baseEpoch = mktime(&t);
  baseMillis = millis();
}

// Lecture des commandes reçues via le port série et traitement des commandes reconnues
void serialReadCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      cmdBuf[cmdLen] = 0;
      if (strncmp(cmdBuf, "date:", 5) == 0) setDate(cmdBuf + 5);
      cmdLen = 0;
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = c;
    }
  }
}

// Envoi d'un échantillon IMU via le port série avec timestamp au format
// "IMU      >> YYYY-MM-DD HH:MM:SS.mmm,ax,ay,az,gx,gy,gz"
void serialSendSample(const float accel[3], const float gyro[3]) {
  // Timestamp basé sur baseEpoch et le temps écoulé depuis baseMillis
  uint32_t dt = millis() - baseMillis;
  time_t sec = baseEpoch + dt / 1000;
  struct tm t;
  gmtime_r(&sec, &t);

  char buf[128];
  int n = snprintf(buf, sizeof(buf),
                   "IMU      >> %04d-%02d-%02d %02d:%02d:%02d.%03d,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n",
                   t.tm_year + 1900, t.tm_mon + 1, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                   (int)(dt % 1000), accel[0], accel[1], accel[2], gyro[0], gyro[1], gyro[2]);
  Serial.write((const uint8_t*)buf, n);
}

// Envoi d'un message via le port série
void serialSendMsg(const char* message) {
  Serial.println(message);
}

// Envoi des caractéristiques calculées via le port série avec timestamp au format
// "FEATURES >> YYYY-MM-DD HH:MM:SS.mmm,moyenne,ecart_type,variance,RMS,movement"
void serialSendFeatures(float moyenne, float ecart_type, float variance, float RMS, bool movement) {
  const uint32_t dt = millis() - baseMillis;
  const time_t sec = baseEpoch + dt / 1000;
  struct tm t;
  gmtime_r(&sec, &t);

  char buf[128];
  const int n = snprintf(buf, sizeof(buf),
                         "FEATURES >> %04d-%02d-%02d %02d:%02d:%02d.%03lu,%.3f,%.3f,%.3f,%.3f,%d\n",
                         t.tm_year + 1900, t.tm_mon + 1, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                         static_cast<unsigned long>(dt % 1000),
                         moyenne, ecart_type, variance, RMS, movement ? 1 : 0);
  if (n > 0 && static_cast<size_t>(n) < sizeof(buf)) {
    Serial.write(reinterpret_cast<const uint8_t*>(buf), static_cast<size_t>(n));
  }
}