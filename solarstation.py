#!/usr/bin/env python3

import asyncio
import time
import smbus2

from meshcore import MeshCore, EventType


# ============================================================
# CONFIGURATION
# ============================================================

PORT = "/dev/ttyACM0"
BAUDRATE = 115200

CHANNEL_NAME = "MeshCoreStation"

# Adresse I2C de l'INA219
INA219_ADDRESS = 0x40

# Bus I2C du Raspberry Pi
I2C_BUS = 1

# Envoi automatique de la tension toutes les 4 heures
VOLTAGE_INTERVAL = 4 * 60 * 60


# ============================================================
# INA219
# ============================================================

def read_voltage():

    try:
        bus = smbus2.SMBus(I2C_BUS)

        # Registre BUS VOLTAGE de l'INA219
        raw = bus.read_word_data(INA219_ADDRESS, 0x02)

        bus.close()

        # inversion des octets
        raw = ((raw & 0xFF) << 8) | ((raw >> 8) & 0xFF)

        # bits 15-3 = tension
        voltage = ((raw >> 3) * 0.004)

        return voltage

    except Exception as e:

        print(f"[INA219] Erreur : {e}")

        return None


# ============================================================
# RECHERCHE DU CANAL
# ============================================================

async def find_channel(meshcore):

    print()
    print("Recherche du canal MeshCoreStation...")

    for channel in range(8):

        try:

            result = await meshcore.commands.get_channel(channel)

            if result.type == EventType.CHANNEL_INFO:

                data = result.payload

                print(f"Canal {channel} : {data}")

                # Recherche du nom dans les données retournées
                text = str(data)

                if CHANNEL_NAME.lower() in text.lower():

                    print()
                    print(f"✓ {CHANNEL_NAME} trouvé sur le canal {channel}")

                    return channel

        except Exception as e:

            print(f"Erreur canal {channel}: {e}")

    print()
    print("Canal MeshCoreStation introuvable.")

    return None


# ============================================================
# RECEPTION DES MESSAGES
# ============================================================

def message_received(event):

    print()
    print("========================================")

    print("📥 MESSAGE REÇU")

    print(event.payload)

    print("========================================")
    print()


# ============================================================
# ENVOI MESSAGE
# ============================================================

async def send_message(meshcore, channel, message):

    result = await meshcore.commands.send_chan_msg(
        channel,
        message
    )

    if result.type == EventType.ERROR:

        print()
        print("❌ Erreur d'envoi :")
        print(result.payload)

    else:

        print()
        print("✓ Message envoyé")


# ============================================================
# ENVOI TENSION
# ============================================================

async def send_voltage(meshcore, channel):

    voltage = read_voltage()

    if voltage is None:

        print("Impossible de lire la tension.")

        return

    message = f"SolarStation | Batterie : {voltage:.2f} V"

    print()
    print(f"🔋 {message}")

    await send_message(
        meshcore,
        channel,
        message
    )


# ============================================================
# BOUCLE AUTOMATIQUE TENSION
# ============================================================

async def voltage_loop(meshcore, channel):

    while True:

        await asyncio.sleep(VOLTAGE_INTERVAL)

        await send_voltage(
            meshcore,
            channel
        )


# ============================================================
# MENU
# ============================================================

async def menu(meshcore, channel):

    print()
    print("========================================")
    print("       SOLARSTATION - MESHCORE")
    print("========================================")
    print(f"USB       : {PORT}")
    print(f"Canal     : {CHANNEL_NAME}")
    print(f"Canal n°  : {channel}")
    print("========================================")
    print()
    print("Commandes :")
    print()
    print("  m  = envoyer un message")
    print("  v  = envoyer la tension maintenant")
    print("  q  = quitter")
    print()

    while True:

        try:

            commande = await asyncio.to_thread(
                input,
                "SolarStation > "
            )

            commande = commande.strip().lower()

            if commande == "m":

                message = await asyncio.to_thread(
                    input,
                    "Message > "
                )

                if message:

                    await send_message(
                        meshcore,
                        channel,
                        message
                    )

            elif commande == "v":

                await send_voltage(
                    meshcore,
                    channel
                )

            elif commande == "q":

                print("Arrêt...")

                break

            else:

                print("Commande inconnue.")

        except (KeyboardInterrupt, EOFError):

            break


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

async def main():

    print()
    print("========================================")
    print("       DÉMARRAGE SOLARSTATION")
    print("========================================")
    print()

    # --------------------------------------------------------
    # Connexion USB
    # --------------------------------------------------------

    print("Connexion au Heltec...")

    try:

        meshcore = await MeshCore.create_serial(
            PORT,
            BAUDRATE,
            debug=False
        )

    except Exception as e:

        print()
        print("❌ Impossible de connecter le Heltec.")
        print(e)

        return

    print("✓ Heltec connecté")

    # --------------------------------------------------------
    # Réception des messages
    # --------------------------------------------------------

    meshcore.subscribe(
        EventType.CHANNEL_MSG_RECV,
        message_received
    )

    # --------------------------------------------------------
    # Recherche du canal
    # --------------------------------------------------------

    channel = await find_channel(
        meshcore
    )

    if channel is None:

        print()
        print("Je laisse le programme arrêté.")
        print("Vérifie que MeshCoreStation existe bien sur le Heltec.")

        await meshcore.disconnect()

        return

    # --------------------------------------------------------
    # Lancement surveillance tension
    # --------------------------------------------------------

    voltage_task = asyncio.create_task(
        voltage_loop(
            meshcore,
            channel
        )
    )

    # --------------------------------------------------------
    # Menu utilisateur
    # --------------------------------------------------------

    try:

        await menu(
            meshcore,
            channel
        )

    finally:

        voltage_task.cancel()

        try:

            await voltage_task

        except asyncio.CancelledError:

            pass

        await meshcore.disconnect()

        print()
        print("✓ SolarStation arrêtée")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Arrêt.")
