import time
import json
from sensor import INA219Sensor
from battery import Battery
from meshcore import MeshCoreController
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

class SolarStation:
    def __init__(self, enable_meshcore=True):
        self.config = load_config()
        self.sensor = INA219Sensor(
            i2c_address=int(self.config['ina219']['i2c_address'], 0)
        )
        self.battery = Battery(
            capacity_ah=self.config['battery']['capacity_ah'],
            voltage=self.config['battery']['nominal_voltage']
        )
        
        # Initialiser MeshCore si activé
        self.meshcore = None
        self.enable_meshcore = enable_meshcore
        
        if enable_meshcore:
            self.meshcore = MeshCoreController(port='/dev/ttyACM0', baudrate=115200)
            if self.meshcore.connect():
                logger.info("✓ MeshCore initialisé")
            else:
                logger.warning("⚠ MeshCore non disponible, continuant sans réseau mesh")
                self.meshcore = None
    
    def send_to_meshcore(self, voltage, current, power, soc):
        """Envoie les données via MeshCore si disponible"""
        if self.meshcore and self.meshcore.is_alive():
            self.meshcore.send_data(voltage, current, power, soc)
    
    def run(self, interval=5):
        """Boucle principale de lecture et envoi des données"""
        logger.info("🚀 Démarrage de la station solaire")
        logger.info(f"📡 Intervalle de lecture: {interval}s")
        
        try:
            while True:
                try:
                    # Lecture des données du capteur
                    voltage = self.sensor.get_voltage()
                    current = self.sensor.get_current()
                    power = self.sensor.get_power()
                    
                    # Mise à jour de la batterie
                    self.battery.update(current, voltage)
                    soc = self.battery.get_soc()
                    
                    # Affichage local
                    logger.info(
                        f"☀️  V={voltage:.2f}V | I={current:.3f}A | "
                        f"P={power:.2f}W | SOC={soc:.1f}%"
                    )
                    
                    # Envoi via MeshCore
                    self.send_to_meshcore(voltage, current, power, soc)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"✗ Erreur dans la boucle: {e}")
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("⏹ Arrêt de la station solaire")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Ferme proprement les connexions"""
        if self.meshcore:
            self.meshcore.disconnect()
        logger.info("Nettoyage terminé")

if __name__ == "__main__":
    station = SolarStation(enable_meshcore=True)
    station.run(interval=5)
