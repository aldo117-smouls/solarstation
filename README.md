# SolarStation 🌞🔋

Système de monitoring en temps réel de l'état d'une batterie solaire 12V avec un capteur INA219 sur Raspberry Pi 4.

## Caractéristiques

- ✅ Lecture continue de la tension batterie via I2C (INA219)
- ✅ Classification automatique de l'état (très faible → chargée)
- ✅ Détection des tendances (hausse, baisse, stable)
- ✅ Sauvegarde de l'historique en JSON
- ✅ Affichage formaté avec indicateurs visuels (↑ ↓ →)

## Prérequis

- Raspberry Pi 4 (ou compatible)
- Capteur INA219 sur I2C (0x40 par défaut)
- Python 3.7+
- Librairies :
  ```bash
  pip install adafruit-circuitpython-ina219
  ```

## Installation

1. Cloner le repo :
   ```bash
   git clone https://github.com/aldo117-smouls/solarstation.git
   cd solarstation
   ```

2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurer `config.json` :
   ```json
   {
     "intervalle_lecture": 30,
     "fichier_etat": "/home/ludo/solarstation/data/etat.json",
     "ina219_address": "0x40"
   }
   ```

## Utilisation

### Lancer le monitoring
```bash
python main.py
```

### Tester le capteur
```bash
python sensor.py
```

Cela affichera 6 lectures espacées de 5 secondes.

## Structure

```
solarstation/
├── main.py          # Boucle principale de monitoring
├── sensor.py        # Pilote INA219
├── battery.py       # Analyse de l'état de batterie
├── config.json      # Configuration
├── data/            # Historique des états (JSON)
└── README.md        # Cette doc
```

## États de la batterie

| Tension | État |
|---------|------|
| < 12.60V | Batterie très faible ⚠️ |
| 12.60-13.00V | Batterie faible |
| 13.00-13.60V | Batterie disponible |
| 13.60-14.00V | Batterie en charge ⚡ |
| 14.00-14.50V | Batterie presque chargée |
| > 14.50V | Batterie chargée ✅ |

## Affichage

```
=========================================
           SOLARSTATION
=========================================

        🔋 13.45 V

        Batterie en charge

        Tendance : ↑ hausse

=========================================
```

## Auteur

Ludo - Projet personnel
