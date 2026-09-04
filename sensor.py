from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219
import board
import busio
import logging

logger = logging.getLogger(__name__)

class INA219Sensor:
    def __init__(self, i2c_address=0x40):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ina219 = INA219(self.i2c, addr=i2c_address)
        
        # Configuration pour meilleure précision
        self.ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self.ina219.bus_voltage_range = BusVoltageRange.RANGE_16V
        
        logger.info(f"INA219 initialisé à l'adresse 0x{i2c_address:02x}")
    
    def get_voltage(self):
        """Retourne la tension en volts"""
        return self.ina219.bus_voltage
    
    def get_current(self):
        """Retourne le courant en ampères"""
        return self.ina219.current
    
    def get_power(self):
        """Retourne la puissance en watts"""
        return self.ina219.power
