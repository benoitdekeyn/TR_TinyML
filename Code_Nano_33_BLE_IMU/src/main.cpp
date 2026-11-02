#include <Arduino.h>
#include <mbed.h>
#include "imu.h"
#include "serial.h"

#define FREQ 50 // Fréquence d'actualisation en Hz

mbed::Ticker ticker;
volatile bool tick = false;

void onTick() {
  tick = true;
}

void setup() {
  serialBegin();

  if (!imuBegin()) {
    serialSendError("Erreur : IMU non detectee !");
    while (1);
  }

  ticker.attach(onTick, std::chrono::microseconds(1000000 / FREQ));
}

void loop() {
  serialReadCommands();

  // Le flag 'tick' est mis à true à la fréquence FREQ
  if (!tick) return;
  tick = false;

  float accel[3], gyro[3];
  if (imuRead(accel, gyro)) serialSendSample(accel, gyro);
}
