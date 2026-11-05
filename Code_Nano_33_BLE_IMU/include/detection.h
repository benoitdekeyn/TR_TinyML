#pragma once
// Prototypes
void setup_capture(int freq);
void detection_loop(float* accel);
bool mouvement_detecte(float variance, float rms);