#pragma once

// Ouvre le port série et attend la connexion du PC.
void serialBegin();

// Lit les commandes reçues ("date:YYYYMMDDHHMMSS" : mise à jour de l'horloge logicielle).
void serialReadCommands();

// Envoie une mesure : YYYY-MM-DD HH:MM:SS.mmm,ax,ay,az,gx,gy,gz
void serialSendSample(const float accel[3], const float gyro[3]);

void serialSendError(const char* message);
