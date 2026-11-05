#pragma once
// Prototypes
void setup_capture(int freq);
void detection_loop(float* accel);
bool determine_mouvement(float variance, float rms);