#pragma once
#include <stdint.h>

float calc_norme(float* accel);
float calc_moyenne(float somme, int taille);
float calc_variance(float somme, float somme_carres, int taille);
float calc_ecart_type(float variance);
float calc_RMS(float somme_carres, int taille);
