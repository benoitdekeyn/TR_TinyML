#include <Arduino.h>
#include <mbed.h>
#include <Arduino_BMI270_BMM150.h>

#define FREQ 50 // Fréquence d'actualisation en Hz

mbed::Ticker ticker;
volatile bool tick = false;

void onTick() {
  tick = true;
}

// Horloge logicielle : date par défaut 2000-01-01 00:00:00, mise à jour par "date:YYYYMMDDHHMMSS"
time_t baseEpoch = 946684800; // 2000-01-01 00:00:00 UTC
uint32_t baseMillis = 0;
char cmdBuf[32];
uint8_t cmdLen = 0;

// Pour mettre à jour la date et l'heure du système
// depuis un message serial au format "date:YYYYMMDDHHMMSS"
void setDate(const char* s) {
  int Y, M, D, h, m, sec;
  if (sscanf(s, "%4d%2d%2d%2d%2d%2d", &Y, &M, &D, &h, &m, &sec) != 6) return;
  struct tm t = {};
  t.tm_year = Y - 1900; t.tm_mon = M - 1; t.tm_mday = D;
  t.tm_hour = h; t.tm_min = m; t.tm_sec = sec;
  baseEpoch = mktime(&t);
  baseMillis = millis();
}

// Lecture des commandes depuis le port série 
// Détecte la commande "date:YYYYMMDDHHMMSS"
// Fait la mise à jour via la fonction setDate()
void readCommands() {
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

void setup() {
  Serial.begin(115200);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("Erreur : IMU non detectee !");
    while (1);
  }

  ticker.attach(onTick, std::chrono::microseconds(1000000 / FREQ));
}

void loop() {
  // Lecture des commandes série
  readCommands();

  // Condition de déclenchement basée sur le ticker 
  // Le flag 'tick' est mis à true à la fréquence FREQ
  if (!tick) return;
  tick = false;

  // Lecture des données IMU si disponibles
  float ax, ay, az, gx, gy, gz;
  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(ax, ay, az);
    IMU.readGyroscope(gx, gy, gz);

    // Pour aligner le capteur sur la sérigraphie du PCB 
    float temp_x = ax;
    ax = ay;
    ay = temp_x;
    az = -az;
    // Même correction pour le gyroscope
    float temp_gx = gx;
    gx = gy;
    gy = temp_gx;
    gz = -gz;

    // Calcul du timestamp basé sur la baseEpoch
    // et le temps écoulé depuis baseMillis
    uint32_t dt = millis() - baseMillis;
    time_t sec = baseEpoch + dt / 1000;
    struct tm t;
    gmtime_r(&sec, &t);

    // Serial output des données IMU avec timestamp
    // Format : YYYY-MM-DD HH:MM:SS.mmm,ax,ay,az,gx,gy,gz
    char buf[112];
    int n = snprintf(buf, sizeof(buf),
                     "%04d-%02d-%02d %02d:%02d:%02d.%03d,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f\n",
                     t.tm_year + 1900, t.tm_mon + 1, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec,
                     (int)(dt % 1000), ax, ay, az, gx, gy, gz);
    Serial.write((const uint8_t*)buf, n);
  }
}