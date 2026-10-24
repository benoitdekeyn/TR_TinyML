#include <Arduino.h>
#include <mbed.h>
#include <Arduino_BMI270_BMM150.h>

#define FREQ 50 // Fréquence d'actualisation en Hz

mbed::Ticker ticker;
volatile bool tick = false;

void onTick() {
  tick = true;
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
  if (!tick) return;
  tick = false;

  float x, y, z;
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);

    // Pour aligner le capteur sur la sérigraphie du PCB 
    float temp_x = x;
    x = y;
    y = temp_x;
    z = -z;

    // Transmission au format CSV en un seul envoi
    char buf[48];
    int n = snprintf(buf, sizeof(buf), "%.2f,%.2f,%.2f\n", x, y, z);
    Serial.write((const uint8_t*)buf, n);
  }
}