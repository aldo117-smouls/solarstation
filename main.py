import asyncio
import json
import os
import time
from datetime import datetime

from sensor import CapteurINA219
from battery import GestionBatterie

from meshcore import MeshCore, EventType


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "/home/ludo/solarstation/config.json"

# USB Heltec V4
MESHCORE_PORT = "/dev/ttyACM0"
MESHCORE_BAUDRATE = 115200

# Canal MeshCore utilisé pour SolarStation
MESHCORE_CHANNEL_NAME = "MeshCoreStation"

# Envoi automatique de la tension toutes les 2 heures
MESHCORE_VOLTAGE_INTERVAL = 2 * 60 * 60


# ============================================================
# VARIABLES GLOBALES
# ============================================================

meshcore = None
canal_meshcore = None

derniere_tension = None
dernier_etat = None


# ============================================================
# CONFIGURATION
# ============================================================

def charger_configuration():
    with open(CONFIG_FILE, "r", encoding="utf-8") as fichier:
        return json.load(fichier)


# ============================================================
# SAUVEGARDE DE L'ETAT
# ============================================================

def sauvegarder_etat(chemin, batterie):
    donnees = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tension": batterie.tension,
        "etat": batterie.etat,
        "niveau": batterie.niveau,
        "tendance": batterie.tendance
    }

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

def afficher(batterie):
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
        f"        Tendance : {fleche} "
        f"{batterie.tendance}"
    )

    print()
    print("=" * 42)


# ============================================================
# RECHERCHE DU CANAL MESHCORE
# ============================================================

async def trouver_canal(mesh):
    print()
    print("Recherche du canal MeshCore...")

    for numero in range(8):
        try:
            resultat = await mesh.commands.get_channel(numero)

            payload = getattr(
                resultat,
                "payload",
                None
            )

            print(
                f"Canal {numero} : {payload}"
            )

            if isinstance(payload, dict):

                nom = payload.get(
                    "channel_name",
                    ""
                )

                if nom == MESHCORE_CHANNEL_NAME:

                    print()
                    print(
                        f"✓ {MESHCORE_CHANNEL_NAME} "
                        f"trouvé sur le canal {numero}"
                    )

                    return numero

        except Exception as erreur:
            print(
                f"Canal {numero} : erreur {erreur}"
            )

    print()
    print(
        f"ERREUR : canal "
        f"{MESHCORE_CHANNEL_NAME} introuvable."
    )

    return None


# ============================================================
# ENVOI MESSAGE MESHCORE
# ============================================================

async def envoyer_message(texte):
    global meshcore
    global canal_meshcore

    if meshcore is None:
        print(
            "MeshCore indisponible : "
            "message non envoyé."
        )
        return

    if canal_meshcore is None:
        print(
            "Canal MeshCore indisponible."
        )
        return

    texte = str(texte).strip()

    if not texte:
        return

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
                f"Erreur envoi MeshCore : "
                f"{getattr(resultat, 'payload', resultat)}"
            )

        else:

            print()
            print(
                f"MeshCore → canal {canal_meshcore} :"
            )
            print(texte)

    except Exception as erreur:

        print(
            f"Erreur envoi MeshCore : {erreur}"
        )


# ============================================================
# ENVOI DE LA TENSION
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

    await envoyer_message(message)


# ============================================================
# EXTRACTION DE LA COMMANDE
# ============================================================

def extraire_commande(texte):
    """
    MeshCore peut fournir le nom de l'expéditeur
    devant le texte.

    Exemple :

        MonTDeck: tension

    devient :

        tension
    """

    if texte is None:
        return ""

    texte = str(texte).strip()

    if not texte:
        return ""

    # Si c'est déjà une commande directe
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

    if texte.lower() in commandes:
        return texte.lower()

    # Sinon on retire le préfixe expéditeur
    if ":" in texte:
        texte = texte.split(
            ":",
            1
        )[1].strip()

    # Retire un éventuel @
    if texte.startswith("@"):
        texte = texte[1:].strip()

    return texte.lower().strip()


# ============================================================
# TRAITEMENT DES COMMANDES
# ============================================================

async def traiter_commande(texte):
    global dernier_etat
    global derniere_tension

    commande = extraire_commande(texte)

    print()
    print(
        f"Commande interprétée : [{commande}]"
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
                f"Niveau : {dernier_etat.niveau} | "
                f"Tendance : {dernier_etat.tendance}"
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
                f"Niveau : {dernier_etat.niveau} | "
                f"Tendance : {dernier_etat.tendance} | "
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
            "Commandes : tension, etat, info, ping, aide"
        )

        return

    # --------------------------------------------------------
    # COMMANDE INCONNUE
    # --------------------------------------------------------

    print(
        f"Commande inconnue : {commande}"
    )

    await envoyer_message(
        "SolarStation | "
        "Commande inconnue. "
        "Envoie aide"
    )


# ============================================================
# RECEPTION DES MESSAGES MESHCORE
# ============================================================

async def message_recu(event):

    try:

        payload = event.payload or {}

        print()
        print("=" * 50)
        print("MESSAGE MESHCORE RECU")
        print(
            f"Payload : {payload}"
        )
        print("=" * 50)

        if not isinstance(
            payload,
            dict
        ):
            return

        canal = payload.get(
            "channel_idx"
        )

        texte = payload.get(
            "text",
            ""
        )

        # On ne traite que notre canal
        if canal != canal_meshcore:

            print(
                f"Message ignoré : canal {canal}"
            )

            return

        if not texte:

            print(
                "Message reçu sans texte."
            )

            return

        print(
            f"Texte reçu : {texte}"
        )

        # Traite la commande
        await traiter_commande(
            texte
        )

    except Exception as erreur:

        print(
            f"Erreur réception MeshCore : "
            f"{erreur}"
        )


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

            tension = capteur.lire_tension()

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
# BOUCLE ENVOI MESHCORE
# ============================================================

async def boucle_meshcore():

    while True:

        try:

            await asyncio.sleep(
                MESHCORE_VOLTAGE_INTERVAL
            )

            print()
            print(
                "Envoi périodique de la tension..."
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

    configuration = charger_configuration()

    intervalle = configuration[
        "intervalle_lecture"
    ]

    fichier_etat = configuration[
        "fichier_etat"
    ]

    adresse = configuration[
        "ina219_address"
    ]

    # --------------------------------------------------------
    # INA219
    # --------------------------------------------------------

    capteur = CapteurINA219(
        adresse
    )

    batterie = GestionBatterie()

    print()
    print("=" * 50)
    print("        DEMARRAGE SOLARSTATION")
    print("=" * 50)

    print()
    print("Initialisation INA219...")

    if not capteur.initialiser():

        print()
        print(
            "INA219 indisponible."
        )

        return

    print(
        "✓ INA219 opérationnel"
    )

    # --------------------------------------------------------
    # PREMIERE MESURE IMMEDIATE
    # --------------------------------------------------------

    try:

        tension = capteur.lire_tension()

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
            f"ERREUR connexion MeshCore : "
            f"{erreur}"
        )

        return

    # --------------------------------------------------------
    # RECHERCHE CANAL
    # --------------------------------------------------------

    canal_meshcore = await trouver_canal(
        meshcore
    )

    if canal_meshcore is None:

        print()
        print(
            "SolarStation continue "
            "sans MeshCore."
        )

        while True:

            await boucle_solaire(
                capteur,
                batterie,
                intervalle,
                fichier_etat
            )

    # --------------------------------------------------------
    # ABONNEMENT RECEPTION
    # --------------------------------------------------------

    print()
    print(
        "Activation de la réception "
        "automatique MeshCore..."
    )

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

    # --------------------------------------------------------
    # MESSAGE DE DEMARRAGE
    # --------------------------------------------------------

    await envoyer_message(
        "SolarStation en ligne | "
        f"Batterie : {derniere_tension:.2f} V"
    )

    # --------------------------------------------------------
    # COMMANDES DISPONIBLES
    # --------------------------------------------------------

    print()
    print("=" * 50)
    print("COMMANDES MESHCORE")
    print("=" * 50)
    print()
    print("tension  → tension batterie")
    print("etat     → état batterie")
    print("info     → informations complètes")
    print("ping     → test SolarStation")
    print("aide     → liste des commandes")
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
    # LANCEMENT DES BOUCLES
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

        try:
            await meshcore.stop_auto_message_fetching()
        except Exception:
            pass

        try:
            await meshcore.disconnect()
        except Exception:
            pass


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
