#!/usr/bin/env python3

import asyncio
import json
import logging
import os
from datetime import datetime

from sensor import INA219Sensor
from battery import GestionBatterie

from meshcore import MeshCore, EventType


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

logger = logging.getLogger("SolarStation")


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "/home/ludo/solarstation/config.json"

# ------------------------------------------------------------
# MeshCore / Heltec
# ------------------------------------------------------------

MESHCORE_PORT = "/dev/ttyACM0"
MESHCORE_BAUDRATE = 115200

MESHCORE_CHANNEL_NAME = "MeshCoreStation"

# Envoi automatique de la tension
# toutes les 2 heures
MESHCORE_VOLTAGE_INTERVAL = 2 * 60 * 60

# ------------------------------------------------------------
# Variables globales
# ------------------------------------------------------------

meshcore = None
canal_meshcore = None

derniere_tension = None
dernier_etat = None

tache_ping = None


# ============================================================
# CONFIGURATION
# ============================================================

def charger_configuration():

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as fichier:

            return json.load(fichier)

    except Exception as erreur:

        print(
            f"Erreur lecture configuration : {erreur}"
        )

        raise


# ============================================================
# SAUVEGARDE ETAT
# ============================================================

def sauvegarder_etat(
    chemin,
    batterie
):

    donnees = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "tension": batterie.tension,
        "etat": batterie.etat,
        "niveau": batterie.niveau,
        "tendance": batterie.tendance
    }

    dossier = os.path.dirname(chemin)

    if dossier:
        os.makedirs(
            dossier,
            exist_ok=True
        )

    fichier_temporaire = chemin + ".tmp"

    with open(
        fichier_temporaire,
        "w",
        encoding="utf-8"
    ) as fichier:

        json.dump(
            donnees,
            fichier,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        fichier_temporaire,
        chemin
    )


# ============================================================
# AFFICHAGE LOCAL
# ============================================================

def afficher(
    batterie
):

    fleches = {
        "hausse": "↑",
        "baisse": "↓",
        "stable": "→"
    }

    fleche = fleches.get(
        batterie.tendance,
        "→"
    )

    print()
    print("=" * 42)
    print("           SOLARSTATION")
    print("=" * 42)
    print()
    print(
        f"        🔋 {batterie.tension:.2f} V"
    )
    print()
    print(
        f"        {batterie.etat}"
    )
    print()
    print(
        f"        Tendance : "
        f"{fleche} {batterie.tendance}"
    )
    print()
    print("=" * 42)


# ============================================================
# RECHERCHE CANAL MESHCORE
# ============================================================

async def trouver_canal(
    mesh
):

    print()
    print(
        "Recherche du canal MeshCore..."
    )

    for numero in range(8):

        try:

            resultat = await mesh.commands.get_channel(
                numero
            )

            payload = getattr(
                resultat,
                "payload",
                None
            )

            print(
                f"Canal {numero} : {payload}"
            )

            if isinstance(
                payload,
                dict
            ):

                nom = payload.get(
                    "channel_name",
                    ""
                )

                if nom == MESHCORE_CHANNEL_NAME:

                    print()
                    print(
                        f"✓ {MESHCORE_CHANNEL_NAME} "
                        f"trouvé sur le canal "
                        f"{numero}"
                    )

                    return numero

        except Exception as erreur:

            print(
                f"Canal {numero} : "
                f"erreur {erreur}"
            )

    print()
    print(
        f"ERREUR : canal "
        f"{MESHCORE_CHANNEL_NAME} "
        f"introuvable."
    )

    return None


# ============================================================
# ENVOI MESSAGE MESHCORE
# ============================================================

async def envoyer_message(
    texte
):

    global meshcore
    global canal_meshcore

    if meshcore is None:

        print(
            "MeshCore indisponible : "
            "message non envoyé."
        )

        return False

    if canal_meshcore is None:

        print(
            "Canal MeshCore indisponible."
        )

        return False

    texte = str(
        texte
    ).strip()

    if not texte:
        return False

    try:

        resultat = await meshcore.commands.send_chan_msg(
            canal_meshcore,
            texte
        )

        if getattr(
            resultat,
            "type",
            None
        ) == EventType.ERROR:

            print(
                "Erreur envoi MeshCore : "
                f"{getattr(resultat, 'payload', resultat)}"
            )

            return False

        print()
        print(
            f"MeshCore → canal "
            f"{canal_meshcore} :"
        )
        print(
            texte
        )

        return True

    except Exception as erreur:

        print(
            f"Erreur envoi MeshCore : "
            f"{erreur}"
        )

        return False


# ============================================================
# ENVOI TENSION
# ============================================================

async def envoyer_tension():

    global derniere_tension

    if derniere_tension is None:

        print(
            "Tension inconnue : "
            "pas d'envoi MeshCore."
        )

        return

    message = (
        "SolarStation | Batterie : "
        f"{derniere_tension:.2f} V"
    )

    await envoyer_message(
        message
    )


# ============================================================
# EXTRACTION COMMANDE
# ============================================================

def extraire_commande(
    texte
):

    if texte is None:
        return ""

    texte = str(
        texte
    ).strip()

    if not texte:
        return ""

    commandes = (
        "tension",
        "voltage",
        "batt",
        "batterie",
        "etat",
        "status",
        "info",
        "infos",
        "ping",
        "aide",
        "help"
    )

    texte_min = texte.lower()

    if texte_min in commandes:
        return texte_min

    # --------------------------------------------------------
    # Retirer un éventuel expéditeur
    #
    # Exemple :
    #
    # MonTDeck: tension
    #
    # devient :
    #
    # tension
    # --------------------------------------------------------

    if ":" in texte:

        texte = texte.split(
            ":",
            1
        )[1].strip()

    # --------------------------------------------------------
    # Retirer @
    # --------------------------------------------------------

    if texte.startswith("@"):

        texte = texte[1:].strip()

    return texte.lower().strip()


# ============================================================
# EXTRACTION TEXTE EVENEMENT
# ============================================================

def extraire_texte_evenement(
    event
):

    """
    MeshCore peut utiliser plusieurs structures
    selon la version de la bibliothèque.

    On essaie donc plusieurs possibilités.
    """

    payload = getattr(
        event,
        "payload",
        None
    )

    # --------------------------------------------------------
    # Payload texte direct
    # --------------------------------------------------------

    if isinstance(
        payload,
        str
    ):

        return payload

    # --------------------------------------------------------
    # Payload dictionnaire
    # --------------------------------------------------------

    if isinstance(
        payload,
        dict
    ):

        for cle in (
            "text",
            "message",
            "msg",
            "data"
        ):

            valeur = payload.get(
                cle
            )

            if isinstance(
                valeur,
                str
            ):

                return valeur

    # --------------------------------------------------------
    # Attributs éventuels
    # --------------------------------------------------------

    for attribut in (
        "text",
        "message",
        "msg"
    ):

        valeur = getattr(
            event,
            attribut,
            None
        )

        if isinstance(
            valeur,
            str
        ):

            return valeur

    return None


# ============================================================
# MESSAGE RECU
# ============================================================

async def traiter_commande(
    texte
):

    global dernier_etat
    global derniere_tension

    commande = extraire_commande(
        texte
    )

    print()
    print(
        f"Commande interprétée : "
        f"[{commande}]"
    )

    # --------------------------------------------------------
    # TENSION
    # --------------------------------------------------------

    if commande in (
        "tension",
        "voltage",
        "batt",
        "batterie"
    ):

        if derniere_tension is None:

            await envoyer_message(
                "SolarStation | "
                "Tension indisponible"
            )

        else:

            await envoyer_message(
                "SolarStation | Batterie : "
                f"{derniere_tension:.2f} V"
            )

        return

    # --------------------------------------------------------
    # ETAT
    # --------------------------------------------------------

    if commande in (
        "etat",
        "status"
    ):

        if dernier_etat is None:

            await envoyer_message(
                "SolarStation | "
                "Etat indisponible"
            )

        else:

            await envoyer_message(
                "SolarStation | "
                f"{derniere_tension:.2f} V | "
                f"{dernier_etat.etat} | "
                f"Niveau : "
                f"{dernier_etat.niveau} | "
                f"Tendance : "
                f"{dernier_etat.tendance}"
            )

        return

    # --------------------------------------------------------
    # INFO
    # --------------------------------------------------------

    if commande in (
        "info",
        "infos"
    ):

        if dernier_etat is None:

            await envoyer_message(
                "SolarStation | "
                "Informations indisponibles"
            )

        else:

            heure = datetime.now().strftime(
                "%d/%m %H:%M"
            )

            await envoyer_message(
                "SolarStation | "
                f"{derniere_tension:.2f} V | "
                f"{dernier_etat.etat} | "
                f"Niveau : "
                f"{dernier_etat.niveau} | "
                f"Tendance : "
                f"{dernier_etat.tendance} | "
                f"{heure}"
            )

        return

    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    if commande == "ping":

        await envoyer_message(
            "SolarStation OK"
        )

        return

    # --------------------------------------------------------
    # AIDE
    # --------------------------------------------------------

    if commande in (
        "aide",
        "help"
    ):

        await envoyer_message(
            "SolarStation | "
            "Commandes : "
            "tension, etat, info, ping, aide"
        )

        return

    # --------------------------------------------------------
    # INCONNUE
    # --------------------------------------------------------

    print(
        f"Commande inconnue : "
        f"{commande}"
    )


async def message_recu(
    event
):

    print()
    print("=" * 50)
    print("MESSAGE MESHCORE RECU")
    print("=" * 50)

    print(
        f"Payload : "
        f"{getattr(event, 'payload', event)}"
    )

    texte = extraire_texte_evenement(
        event
    )

    if texte:

        print(
            f"Texte : {texte}"
        )

        await traiter_commande(
            texte
        )

    else:

        print(
            "Impossible d'extraire le texte."
        )

    print("=" * 50)


# ============================================================
# BOUCLE PING
# ============================================================

async def boucle_ping(
    intervalle
):

    try:

        while True:

            await asyncio.sleep(
                intervalle
            )

            await envoyer_message(
                "SolarStation OK"
            )

    except asyncio.CancelledError:

        raise


# ============================================================
# BOUCLE SOLAIRE
# ============================================================

async def boucle_solaire(
    capteur,
    batterie,
    intervalle,
    fichier_etat
):

    global derniere_tension
    global dernier_etat

    while True:

        try:

            tension = capteur.get_voltage()

            derniere_tension = tension

            etat = batterie.analyser(
                tension
            )

            dernier_etat = etat

            sauvegarder_etat(
                fichier_etat,
                etat
            )

            afficher(
                etat
            )

        except Exception as erreur:

            print()
            print(
                f"Erreur lecture INA219 : "
                f"{erreur}"
            )

        await asyncio.sleep(
            intervalle
        )


# ============================================================
# BOUCLE MESHCORE
# ============================================================

async def boucle_meshcore():

    while True:

        try:

            await asyncio.sleep(
                MESHCORE_VOLTAGE_INTERVAL
            )

            print()
            print(
                "Envoi périodique "
                "de la tension..."
            )

            await envoyer_tension()

        except asyncio.CancelledError:

            raise

        except Exception as erreur:

            print(
                f"Erreur boucle MeshCore : "
                f"{erreur}"
            )

            await asyncio.sleep(
                10
            )


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

async def main():

    global meshcore
    global canal_meshcore
    global derniere_tension
    global dernier_etat
    global tache_ping

    # --------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------

    configuration = charger_configuration()

    intervalle = configuration.get(
        "intervalle_lecture",
        10
    )

    fichier_etat = configuration.get(
        "fichier_etat",
        "/home/ludo/solarstation/data/status.json"
    )

    adresse = configuration.get(
        "ina219_address",
        0x40
    )

    print()
    print("=" * 50)
    print("        DEMARRAGE SOLARSTATION")
    print("=" * 50)
    print()

    # --------------------------------------------------------
    # INA219
    # --------------------------------------------------------

    print(
        "Initialisation INA219..."
    )

    try:

        capteur = INA219Sensor(
            adresse
        )

        batterie = GestionBatterie()

        print(
            "✓ INA219 opérationnel"
        )

    except Exception as erreur:

        print()
        print(
            "❌ INA219 indisponible."
        )

        print(
            f"Erreur : {erreur}"
        )

        return

    # --------------------------------------------------------
    # PREMIERE MESURE
    # --------------------------------------------------------

    try:

        tension = capteur.get_voltage()

        derniere_tension = tension

        etat = batterie.analyser(
            tension
        )

        dernier_etat = etat

        sauvegarder_etat(
            fichier_etat,
            etat
        )

        afficher(
            etat
        )

    except Exception as erreur:

        print(
            f"Erreur première mesure : "
            f"{erreur}"
        )

    # --------------------------------------------------------
    # CONNEXION MESHCORE
    # --------------------------------------------------------

    print()
    print(
        f"Connexion Heltec sur "
        f"{MESHCORE_PORT}..."
    )

    try:

        meshcore = await MeshCore.create_serial(
            MESHCORE_PORT,
            MESHCORE_BAUDRATE,
            debug=True
        )

        print(
            "✓ Liaison USB MeshCore établie"
        )

    except Exception as erreur:

        print()
        print(
            "ERREUR connexion MeshCore : "
            f"{erreur}"
        )

        print()
        print(
            "SolarStation continue "
            "sans MeshCore."
        )

        tache_solaire = asyncio.create_task(
            boucle_solaire(
                capteur,
                batterie,
                intervalle,
                fichier_etat
            )
        )

        try:

            await tache_solaire

        finally:

            tache_solaire.cancel()

            try:
                await tache_solaire
            except asyncio.CancelledError:
                pass

            capteur.close()

        return

    # --------------------------------------------------------
    # RECHERCHE DU CANAL
    # --------------------------------------------------------

    canal_meshcore = await trouver_canal(
        meshcore
    )

    if canal_meshcore is None:

        print()
        print(
            "Canal MeshCoreStation "
            "introuvable."
        )

        print(
            "SolarStation continue "
            "sans MeshCore."
        )

        try:

            await meshcore.disconnect()

        except Exception:

            pass

        tache_solaire = asyncio.create_task(
            boucle_solaire(
                capteur,
                batterie,
                intervalle,
                fichier_etat
            )
        )

        try:

            await tache_solaire

        finally:

            tache_solaire.cancel()

            try:
                await tache_solaire
            except asyncio.CancelledError:
                pass

            capteur.close()

        return

    # --------------------------------------------------------
    # ABONNEMENT RECEPTION
    # --------------------------------------------------------

    print()
    print(
        "Activation de la réception "
        "automatique MeshCore..."
    )

    try:

        meshcore.subscribe(
            EventType.CHANNEL_MSG_RECV,
            message_recu,
            attribute_filters={
                "channel_idx": canal_meshcore
            }
        )

        await meshcore.start_auto_message_fetching()

        print(
            "✓ Réception MeshCore activée"
        )

    except Exception as erreur:

        print(
            "Erreur activation réception "
            f"MeshCore : {erreur}"
        )

    # --------------------------------------------------------
    # MESSAGE DE DEMARRAGE
    # --------------------------------------------------------

    if derniere_tension is not None:

        await envoyer_message(
            "SolarStation en ligne | "
            f"Batterie : "
            f"{derniere_tension:.2f} V"
        )

    else:

        await envoyer_message(
            "SolarStation en ligne"
        )

    # --------------------------------------------------------
    # INFORMATIONS
    # --------------------------------------------------------

    print()
    print("=" * 50)
    print("COMMANDES MESHCORE")
    print("=" * 50)
    print()
    print(
        "tension  → tension batterie"
    )
    print(
        "etat     → état batterie"
    )
    print(
        "info     → informations complètes"
    )
    print(
        "ping     → test SolarStation"
    )
    print(
        "aide     → liste des commandes"
    )
    print()
    print(
        f"Canal : {MESHCORE_CHANNEL_NAME}"
    )
    print(
        f"Index : {canal_meshcore}"
    )
    print()
    print(
        "SolarStation prêt."
    )
    print("=" * 50)

    # --------------------------------------------------------
    # BOUCLES
    # --------------------------------------------------------

    tache_solaire = asyncio.create_task(
        boucle_solaire(
            capteur,
            batterie,
            intervalle,
            fichier_etat
        )
    )

    tache_meshcore = asyncio.create_task(
        boucle_meshcore()
    )

    try:

        await asyncio.gather(
            tache_solaire,
            tache_meshcore
        )

    except asyncio.CancelledError:

        pass

    finally:

        tache_solaire.cancel()
        tache_meshcore.cancel()

        try:
            await tache_solaire
        except asyncio.CancelledError:
            pass

        try:
            await tache_meshcore
        except asyncio.CancelledError:
            pass

        # ----------------------------------------------------
        # Arrêt MeshCore
        # ----------------------------------------------------

        try:

            await meshcore.stop_auto_message_fetching()

        except Exception:

            pass

        try:

            await meshcore.disconnect()

        except Exception:

            pass

        # ----------------------------------------------------
        # Arrêt INA219
        # ----------------------------------------------------

        capteur.close()

        print()
        print(
            "✓ SolarStation arrêtée"
        )


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "SolarStation arrêté."
        )
