#include <Arduino.h>
#include <mbed.h>
#include "imu.h"
#include "serial.h"
#include "detection.h"

#define FREQ 50 // Fréquence d'actualisation en Hz

// Ticker pour la fréquence d'échantillonnage de l'IMU
mbed::Ticker ticker;
volatile bool tick = false;

void onTick() {
  tick = true;
}

void setup() {
  // Initialise la communication série
  serialBegin();

  // Initialise l'IMU et vérifie sa disponibilité
  if (!imuBegin()) {
    serialSendMsg("Erreur : IMU non detectee !");
    while (1);
  }

  // Initialise la capture avec la fréquence d'échantillonnage FREQ
  setup_capture(FREQ);

  // Initialise le ticker pour appeler onTick() à la fréquence FREQ
  ticker.attach(onTick, std::chrono::microseconds(1000000 / FREQ));
}

void loop() {
  // Lecture des commandes série
  serialReadCommands();

  // Attente de la prochaine itération selon la fréquence FREQ
  if (!tick) return;
  tick = false;

  // Lecture des mesures de l'IMU
  float accel[3], gyro[3];
  if (!imuRead(accel, gyro)) return;

  // Envoi des mesures via la communication série
  serialSendSample(accel, gyro);

  // Analyse des mesures pour détecter le mouvement
  detection_loop(accel);
}
