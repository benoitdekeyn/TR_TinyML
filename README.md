# Tremplin Recherche - TinyML

## Contenu du dépôt actuellement

- **`Code_Nano_33_BLE_IMU/`** : projet PlatformIO contenant le code Arduino (`src/main.cpp`). Il lit l'IMU de la Nano 33 BLE et envoie les accélérations (x, y, z) sur le port série à **50 Hz**. Une fenêtre d'une seconde calcule aussi les statistiques de la norme de l'accélération et émet une trame features horodatée.
- **`Python_GUI_-_Serial_Nano/`** : code Python côté PC :
  - `main.py` : point d'entrée de l'application.
  - `core_server.py` : orchestre les threads, la connexion série et la boucle VPython (qui sert la page locale).
  - `core_Serial.py` : classe les lignes `IMU      >> ...` et `FEATURES >> ...` (préfixe retiré avant traitement), mesure la fréquence IMU (moyenne glissante sur 5 s) et la période des messages features en ms (moyenne sur 10 s, actualisée chaque seconde).
  - `core_IMU.py` et `core_Features.py` : traitent les deux formats CSV et enregistrent les mesures.
  - `core_interface.py` : assemble les graphes, les panneaux de mesures et la scène VPython.
  - `interface_web/` : tout le texte et la mise en forme de la page. `top_panel.html` (titre, connexion, features, contrôles des graphes), `feature_panel.html` (valeurs features sur une ligne), `scene_panel.html` (vue 3D) et `styles.css`. Les emplacements `{{nom}}` reçoivent les widgets VPython (boutons, champs, menu) créés par `core_html.py`.
  - Les messages features sont `FEATURES >> timestamp,moyenne,ecart_type,variance,RMS,movement`, où `movement` vaut `1` si le RMS de la norme d'accélération dépasse `1 g`, sinon `0` (les échantillons IMU sont `IMU      >> timestamp,ax,ay,az,gx,gy,gz`). Ils sont enregistrés sous `recordings/features/`. La durée de la fenêtre est configurable dans le firmware (`DUREE_FENETRE` de `Code_Nano_33_BLE_IMU/src/detection.cpp`).
  - `core_3D.py` : gère la scène 3D (carte, axes, vecteur d'accélération).

## Dépendances Python

| Paquet | Rôle |
|---|---|
| `vpython` | Crée la scène 3D interactive affichée dans le navigateur. |
| `pyserial` | Fournit le module `serial`, qui lit les données envoyées par l'Arduino sur le port COM. |
| `threading` | Module de la bibliothèque standard, donc rien à installer. Il lit le port série en arrière-plan sans bloquer l'affichage. |

Commande d'installation :

```bash
pip install vpython pyserial
```


## Utilisation

1. Ouvrir le dossier `Code_Nano_33_BLE_IMU` comme projet **PlatformIO** dans VS Code.
2. Brancher l'Arduino Nano 33 BLE et **uploader** le code (bouton *Upload*).
3. Si besoin, adapter la résolution dans `Python_GUI_-_Serial_Nano/core_3D.py` (`WINDOW_WIDTH`, `WINDOW_HEIGHT`).
4. Fermer le moniteur série de PlatformIO, qui occupe le port, puis lancer :

   ```bash
   python Python_GUI_-_Serial_Nano/main.py
   ```

5. Une fenêtre s'ouvre dans le navigateur avec l'interface 3D.
6. Choisir le port COM correspondant à l'Arduino sur l'interface.