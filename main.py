import json
import os
import time
from datetime import datetime

from sensor import CapteurINA219
from battery import GestionBatterie

CONFIG_FILE = "/home/ludo/solarstation/config.json"

def charger_configuration():
    with open(CONFIG_FILE, "r", encoding="utf-8") as fichier:
        return json.load(fichier)

def sauvegarder_etat(chemin, batterie):
    donnees = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tension": batterie.tension,
        "etat": batterie.etat,
        "niveau": batterie.niveau,
        "tendance": batterie.tendance
    }

    fichier_temporaire = chemin + ".tmp"

    with open(fichier_temporaire, "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)

    os.replace(fichier_temporaire, chemin)

def afficher(batterie):
    fleches = {
        "hausse": "↑",
        "baisse": "↓",
        "stable": "→"
    }

    fleche = fleches.get(batterie.tendance, "→")

    print()
    print("=" * 42)
    print("           SOLARSTATION")
    print("=" * 42)
    print()
    print(f"        🔋 {batterie.tension:.2f} V")
    print()
    print(f"        {batterie.etat}")
    print()
    print(f"        Tendance : {fleche} {batterie.tendance}")
    print()
    print("=" * 42)

def main():
    configuration = charger_configuration()

    intervalle = configuration["intervalle_lecture"]
    fichier_etat = configuration["fichier_etat"]
    adresse = configuration["ina219_address"]

    capteur = CapteurINA219(adresse)
    batterie = GestionBatterie()

    print("Démarrage de SolarStation...")
    print()

    if not capteur.initialiser():
        print()
        print("INA219 indisponible.")
        print("Vérifie le branchement puis relance le programme.")
        return

    while True:
        try:
            tension = capteur.lire_tension()

            etat = batterie.analyser(tension)

            sauvegarder_etat(fichier_etat, etat)
            afficher(etat)

            time.sleep(intervalle)

        except KeyboardInterrupt:
            print()
            print("SolarStation arrêté.")
            break

        except Exception as erreur:
            print()
            print(f"Erreur : {erreur}")
            print("Nouvelle tentative dans 10 secondes...")
            time.sleep(10)

if __name__ == "__main__":
    main()