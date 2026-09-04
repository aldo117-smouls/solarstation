import time
import board
from adafruit_ina219 import INA219

class CapteurINA219:
    def __init__(self, adresse=0x40):
        self.adresse = adresse
        self.ina219 = None

    def initialiser(self):
        try:
            i2c = board.I2C()
            self.ina219 = INA219(i2c, addr=self.adresse)

            tension = self.lire_tension()

            print(f"INA219 détecté sur 0x{self.adresse:02X}")
            print(f"Tension batterie : {tension:.2f} V")

            return True

        except Exception as erreur:
            self.ina219 = None
            print(f"Erreur INA219 : {erreur}")
            return False

    def lire_tension(self):
        if self.ina219 is None:
            raise RuntimeError("INA219 non initialisé")

        return self.ina219.bus_voltage

def test():
    capteur = CapteurINA219()

    if not capteur.initialiser():
        return

    print()
    print("Lecture de la tension pendant 30 secondes...")
    print()

    for _ in range(6):
        try:
            tension = capteur.lire_tension()
            print(f"{time.strftime('%H:%M:%S')}  |  {tension:.2f} V")
        except Exception as erreur:
            print(f"Erreur de lecture : {erreur}")

        time.sleep(5)

if __name__ == "__main__":
    test()