import serial
import json
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class MeshCoreController:
    """
    Contrôleur pour communiquer avec le Heltec V4 via USB (port série)
    Envoie les données de la station solaire sur le réseau mesh MeshCore
    """
    
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        
    def connect(self):
        """Établit la connexion série avec le Heltec V4"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.connected = True
            logger.info(f"✓ Connecté au Heltec V4 sur {self.port} à {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"✗ Erreur de connexion série: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Ferme la connexion série"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.connected = False
            logger.info("Déconnecté du Heltec V4")
    
    def send_data(self, voltage, current, power, soc):
        """
        Envoie les données de la station solaire via le Heltec V4
        Format JSON pour compatibilité avec MeshCore
        """
        if not self.connected:
            logger.warning("Non connecté au Heltec V4, reconnexion...")
            if not self.connect():
                return False
        
        try:
            # Format du payload MeshCore
            payload = {
                "type": "solarstation",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "voltage_v": round(voltage, 2),
                    "current_a": round(current, 3),
                    "power_w": round(power, 2),
                    "soc_percent": round(soc, 1)
                }
            }
            
            # Sérialiser et envoyer
            message = json.dumps(payload) + '\n'
            self.serial.write(message.encode('utf-8'))
            
            logger.debug(f"📤 Envoyé: {payload}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"✗ Erreur lors de l'envoi: {e}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"✗ Erreur inattendue: {e}")
            return False
    
    def receive_data(self):
        """
        Reçoit et parse les données du Heltec V4
        Utile pour les commands du réseau mesh
        """
        if not self.connected:
            return None
        
        try:
            if self.serial.in_waiting > 0:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    data = json.loads(line)
                    logger.debug(f"📥 Reçu: {data}")
                    return data
        except (serial.SerialException, json.JSONDecodeError) as e:
            logger.warning(f"Erreur réception: {e}")
        
        return None
    
    def is_alive(self):
        """Vérifie que la connexion est toujours active"""
        return self.connected and (self.serial and self.serial.is_open)
