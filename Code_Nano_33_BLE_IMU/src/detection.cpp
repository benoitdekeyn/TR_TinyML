#include <Arduino.h>
#include "detection.h"
#include "calculs.h"
#include "serial.h"

#define SEUIL_RMS 1.1
#define DUREE_FENETRE 1000 // Durée de la fenêtre en millisecondes

float somme = 0.0;
float somme_carres = 0.0;
int mesures_comptees = 0;
int duree_fenetre = 0;
int frequence = 0;

void setup_capture(int freq) {
  somme = 0.0;
  somme_carres = 0.0;
  mesures_comptees = 0;
  duree_fenetre = DUREE_FENETRE;
  frequence = freq;
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
}

void detection_loop(float* accel) {
  
  float norme = calc_norme(accel);
  somme += norme;
  somme_carres += norme * norme;
  ++mesures_comptees;

  if (mesures_comptees < duree_fenetre * frequence / 1000) return;

  float moyenne = calc_moyenne(somme, mesures_comptees);
  float variance = calc_variance(somme, somme_carres, mesures_comptees);
  float ecart_type = calc_ecart_type(variance);
  float rms = calc_RMS(somme_carres, mesures_comptees);
  bool mouvement = mouvement_detecte(variance, rms);

  serialSendFeatures(moyenne, ecart_type, variance, rms, mouvement);

  somme = 0.0;
  somme_carres = 0.0;
  mesures_comptees = 0;
}

bool mouvement_detecte(float variance, float rms) {
  bool mouvement_detecte = rms > SEUIL_RMS;
  digitalWrite(LED_BUILTIN, mouvement_detecte ? HIGH : LOW);
  return mouvement_detecte;
}