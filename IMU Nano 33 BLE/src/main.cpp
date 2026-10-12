#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>

#define FREQ 10 // Fréquence d'échantillonnage en Hz

void setup() {
  Serial.begin(115200);
  while (!Serial);
  IMU.begin();
}

void loop() {
  float x, y, z;

  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(x, y, z);

    // Format propre : "X,Y,Z"
    Serial.print(x, 2); 
    Serial.print(",");
    Serial.print(y, 2);
    Serial.print(",");
    Serial.println(z, 2);
  }
  
  delay(1000/FREQ); 
}