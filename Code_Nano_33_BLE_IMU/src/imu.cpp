#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>
#include "imu.h"
#include "calculs.h"

// Offsets du gyroscope (°/s), additionnés aux mesures dans le repère brut du capteur
#define GYRO_OFFSET_X +0.061f
#define GYRO_OFFSET_Y +0.122f
#define GYRO_OFFSET_Z -0.122f

#define GRAVITY_OFFSET_1G 0.010

// Initialise l'IMU et retourne true si le capteur est détecté.
bool imuBegin() {
  return IMU.begin();
}

// Lit une mesure alignée sur la sérigraphie (offsets gyro appliqués) : accel en g, gyro en °/s.
// Retourne false si aucune nouvelle mesure n'est disponible.
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

  // scale chaque accélération pour que leur normme fasse GRAVITY_OFFSET_1G de plus 
  float norme = calc_norme(accel);
  float facteur = (norme + GRAVITY_OFFSET_1G) / norme;
  accel[0] *= facteur;
  accel[1] *= facteur;
  accel[2] *= facteur;

  return true;
}
