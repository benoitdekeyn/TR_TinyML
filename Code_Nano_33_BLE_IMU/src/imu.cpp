#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>
#include "imu.h"

// Offsets du gyroscope (°/s), additionnés aux mesures dans le repère brut du capteur
#define GYRO_OFFSET_X +0.061f
#define GYRO_OFFSET_Y +0.122f
#define GYRO_OFFSET_Z -0.122f

bool imuBegin() {
  return IMU.begin();
}

bool imuRead(float accel[3], float gyro[3]) {
  if (!(IMU.accelerationAvailable() && IMU.gyroscopeAvailable())) return false;

  float ax, ay, az, gx, gy, gz;
  IMU.readAcceleration(ax, ay, az);
  IMU.readGyroscope(gx, gy, gz);

  // Pour aligner le capteur sur la sérigraphie du PCB
  accel[0] = ay;
  accel[1] = ax;
  accel[2] = -az;
  // Même correction pour le gyroscope
  gyro[0] = -gy;
  gyro[1] = -gx;
  gyro[2] = +gz;
  
  // Ajoute les offsets du gyroscope aux mesures alignées sur la sérigraphie
  gyro[0] += (GYRO_OFFSET_X);
  gyro[1] += (GYRO_OFFSET_Y);
  gyro[2] += (GYRO_OFFSET_Z);

  return true;
}
