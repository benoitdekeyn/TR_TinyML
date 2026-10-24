# Tremplin Recherche - TinyML

## Contenu du dépôt actuellement

- **`Code_Nano_33_BLE_IMU/`** : projet PlatformIO contenant le code Arduino (`src/main.cpp`). Il lit l'IMU de la Nano 33 BLE et envoie les accélérations (x, y, z) sur le port série à **50 Hz**.
- **`Python_GUI_-_Serial_Nano/`** : code Python côté PC :
  - `main.py` : point d'entrée, il relie la lecture série et l'affichage.
  - `core_IMU.py` : récupère les données reçues sur le port série de l'Arduino (dans un thread dédié).
  - `core_3D.py` : gère l'affichage 3D (carte, axes, vecteur d'accélération).

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