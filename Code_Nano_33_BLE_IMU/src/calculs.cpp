#include <Arduino.h>
#include <math.h>
#include "calculs.h"

float calc_norme(float* accel) {
  return sqrt(accel[0] * accel[0] +
              accel[1] * accel[1] +
              accel[2] * accel[2]);
}

float calc_moyenne(float somme, int taille) {
  return taille == 0 ? 0.0 : (somme / taille);
}

float calc_variance(float somme, float somme_carres, int taille) {
  if (taille == 0) return 0.0;
  float moyenne = somme / taille;
  float variance = somme_carres / taille - moyenne * moyenne;
  return variance > 0.0 ? variance : 0.0;
}

float calc_ecart_type(float variance) {
  return sqrt(variance > 0.0 ? variance : 0.0);
}

float calc_RMS(float somme_carres, int taille) {
  return taille == 0 ? 0.0 : sqrt(somme_carres / taille);
}
