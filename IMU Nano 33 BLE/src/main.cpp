#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>

#define FREQ 10 // Fréquence d'échantillonnage en Hz

void setup() {
  Serial.begin(115200);
  while (!Serial);

  if (!IMU.begin()) {
    Serial.println("Erreur : IMU non detectee !");
    while (1);
  }
}

void loop() {
  float x, y, z;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);

    // Permutation pour aligner le capteur Bosch sur la sérigraphie du PCB :
    float temp = x;
    float x = y;
    float y = temp;

    // Transmission propre au format CSV
    Serial.print(x, 2);
    Serial.print(",");
    Serial.print(y, 2);
    Serial.print(",");
    Serial.println(z, 2);
  }
  
  delay(1000/FREQ); 
}