#pragma once
// Prototypes
void serialBegin();
void serialReadCommands();
void serialSendSample(const float accel[3], const float gyro[3]);
void serialSendMsg(const char* message);
void serialSendFeatures(float moyenne, float ecart_type, float variance, float RMS, bool movement);
