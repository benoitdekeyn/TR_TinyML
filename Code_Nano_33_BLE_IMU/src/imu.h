#pragma once

// Initialise l'IMU. Retourne false si le capteur n'est pas détecté.
bool imuBegin();

// Lit une mesure alignée sur la sérigraphie (offsets gyro appliqués) : accel en g, gyro en °/s.
// Retourne false si aucune nouvelle mesure n'est disponible.
bool imuRead(float accel[3], float gyro[3]);
