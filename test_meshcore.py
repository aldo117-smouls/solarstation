#!/usr/bin/env python3

import asyncio
import sys
from meshcore import MeshCore, EventType

# ==========================
# CONFIGURATION
# ==========================

PORT = "/dev/ttyACM0"
BAUDRATE = 115200

# Mets ici le numéro du canal MeshCoreStation
CHANNEL = 0

MESSAGE = "TEST DEPUIS LE RPI"


async def main():

    print("Connexion au Heltec...")

    try:
        meshcore = await MeshCore.create_serial(
            PORT,
            BAUDRATE,
            debug=False
        )
    except Exception as e:
        print(f"ERREUR connexion USB : {e}")
        return

    print("Heltec connecté !")

    # Envoi du message
    print(f"Envoi sur le canal {CHANNEL} : {MESSAGE}")

    result = await meshcore.commands.send_chan_msg(
        CHANNEL,
        MESSAGE
    )

    if result.type == EventType.ERROR:
        print("ERREUR lors de l'envoi :")
        print(result.payload)
    else:
        print("MESSAGE ENVOYÉ !")

    await meshcore.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
