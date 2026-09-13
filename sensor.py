from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219
import board
import busio
import logging

logger = logging.getLogger(__name__)


class INA219Sensor:
    """
    Gestion du capteur INA219.

    Le capteur est initialisé directement lors de la création
    de l'objet.
    """

    def __init__(self, i2c_address=0x40):
        self.i2c_address = i2c_address

        self.i2c = busio.I2C(
            board.SCL,
            board.SDA
        )

        self.ina219 = INA219(
            self.i2c,
            addr=i2c_address
        )

        # Résolution maximale pour les mesures
        self.ina219.bus_adc_resolution = (
            ADCResolution.ADCRES_12BIT_32S
        )

        self.ina219.shunt_adc_resolution = (
            ADCResolution.ADCRES_12BIT_32S
        )

        # Batterie 12 V : plage 16 V
        self.ina219.bus_voltage_range = (
            BusVoltageRange.RANGE_16V
        )

        logger.info(
            f"INA219 initialisé à l'adresse "
            f"0x{i2c_address:02x}"
        )

    def get_voltage(self):
        """
        Retourne la tension batterie en volts.
        """
        return float(self.ina219.bus_voltage)

    def get_current(self):
        """
        Retourne le courant en mA.
        """
        return float(self.ina219.current)

    def get_power(self):
        """
        Retourne la puissance en mW.
        """
        return float(self.ina219.power)

    def close(self):
        """
        Ferme proprement le bus I2C si possible.
        """
        try:
            if hasattr(self.i2c, "deinit"):
                self.i2c.deinit()
        except Exception:
            pass
