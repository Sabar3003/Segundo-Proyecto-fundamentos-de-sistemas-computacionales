"""
PARQUEO INTELIGENTE - RASPBERRY PI 2 (PARQUEO 2)
===============================================
Puerto: 1719
Espacios: 2 (Espacio 1 y 2 del Parqueo 2)
Componentes del sistema:
- Display 7 segmentos: Espacios disponibles y costo de parqueo
- Botones: Ingreso y Pago/Salida
- Fotoresistencias: Detección de ocupación de espacios
- LEDs: Indicadores de disponibilidad de espacios
- Servomotor: Control de barrera de entrada/salida
- Comunicación WiFi: Control remoto desde GUI
"""

from machine import Pin, PWM, ADC
import time
import socket
import network
import json
import _thread

# ========== CONFIGURACIÓN DE RED ==========
SSID = "Admiti q sos pobre"
PASSWORD = "soy pobre"
PUERTO_SERVIDOR = 1719  # Puerto específico para Parqueo 2
PARQUEO_ID = 2

# ========== CONFIGURACIÓN DE PINES ==========
# Servomotor (barrera)
SERVO_PIN = 28

# Display 7 segmentos (ánodo común)
DISPLAY_PINS = {
    'a': 2,   # Segmento A
    'b': 3,   # Segmento B
    'c': 4,   # Segmento C
    'd': 5,   # Segmento D
    'e': 6,   # Segmento E
    'f': 7,   # Segmento F
    'g': 8,   # Segmento G
    'dp': 9   # Punto decimal
}

# Botones
BOTON_INGRESO = 10
BOTON_PAGO = 11

# LEDs indicadores de espacios
LED_ESPACIO_1 = 12
LED_ESPACIO_2 = 13

# Fotoresistencias (ADC)
FOTO_ESPACIO_1 = 26  # ADC0
FOTO_ESPACIO_2 = 27  # ADC1

# ========== CONFIGURACIÓN DE TARIFAS ==========
TARIFA_POR_10_SEGUNDOS = 1000  # Colones
UMBRAL_FOTORESISTENCIA = 30000  # Valor para detectar ocupación

# ========== PATRONES PARA DISPLAY 7 SEGMENTOS ==========
# Patrones para números 0-9 (ánodo común - 0=encendido, 1=apagado)
DIGITOS_7SEG = {
    0: {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 1},  # 0
    1: {'a': 1, 'b': 0, 'c': 0, 'd': 1, 'e': 1, 'f': 1, 'g': 1},  # 1
    2: {'a': 0, 'b': 0, 'c': 1, 'd': 0, 'e': 0, 'f': 1, 'g': 0},  # 2
    3: {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 1, 'g': 0},  # 3
    4: {'a': 1, 'b': 0, 'c': 0, 'd': 1, 'e': 1, 'f': 0, 'g': 0},  # 4
    5: {'a': 0, 'b': 1, 'c': 0, 'd': 0, 'e': 1, 'f': 0, 'g': 0},  # 5
    6: {'a': 0, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0},  # 6
    7: {'a': 0, 'b': 0, 'c': 0, 'd': 1, 'e': 1, 'f': 1, 'g': 1},  # 7
    8: {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0},  # 8
    9: {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 0, 'g': 0}   # 9
}

class ParqueoInteligente2:
    """Clase principal para manejar el Parqueo 2"""
    
    def __init__(self):
        self.inicializar_hardware()
        self.espacios_disponibles = 2
        self.vehiculos_activos = {}  # ID_temp -> tiempo_entrada
        self.id_vehiculo_actual = 1
        self.modo_pago = False
        self.vehiculo_pagando = None
        self.barrera_abierta = False
        
    def inicializar_hardware(self):
        """Inicializar todos los componentes de hardware"""
        print(f"Inicializando hardware del Parqueo {PARQUEO_ID}...")
        
        # Servomotor
        self.servo = PWM(Pin(SERVO_PIN))
        self.servo.freq(50)
        self.servo.duty_ns(1700000)  # Posición cerrada inicial
        
        # Display 7 segmentos
        self.display_pins = {}
        for segmento, pin_num in DISPLAY_PINS.items():
            self.display_pins[segmento] = Pin(pin_num, Pin.OUT)
            self.display_pins[segmento].value(1)  # Apagar todos los segmentos
        
        # Botones (con pull-up interno)
        self.boton_ingreso = Pin(BOTON_INGRESO, Pin.IN, Pin.PULL_UP)
        self.boton_pago = Pin(BOTON_PAGO, Pin.IN, Pin.PULL_UP)
        
        # LEDs
        self.led_espacio1 = Pin(LED_ESPACIO_1, Pin.OUT)
        self.led_espacio2 = Pin(LED_ESPACIO_2, Pin.OUT)
        
        # Fotoresistencias (ADC)
        self.foto_espacio1 = ADC(Pin(FOTO_ESPACIO_1))
        self.foto_espacio2 = ADC(Pin(FOTO_ESPACIO_2))
        
        # Estado inicial
        self.actualizar_leds()
        self.mostrar_espacios_disponibles()
        
        print(f"Hardware del Parqueo {PARQUEO_ID} inicializado correctamente")
    
    def mostrar_en_display(self, numero):
        """Mostrar número en display 7 segmentos (0-9)"""
        if numero < 0 or numero > 9:
            numero = 0
            
        patron = DIGITOS_7SEG[numero]
        
        for segmento in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
            self.display_pins[segmento].value(patron[segmento])
    
    def mostrar_espacios_disponibles(self):
        """Mostrar espacios disponibles en el display"""
        self.mostrar_en_display(self.espacios_disponibles)
        print(f"Parqueo {PARQUEO_ID} - Display: {self.espacios_disponibles} espacios disponibles")
    
    def leer_fotoresistencias(self):
        """Leer estado de las fotoresistencias"""
        valor1 = self.foto_espacio1.read_u16()
        valor2 = self.foto_espacio2.read_u16()
        
        # True = ocupado, False = libre
        ocupado1 = valor1 < UMBRAL_FOTORESISTENCIA
        ocupado2 = valor2 < UMBRAL_FOTORESISTENCIA
        
        return ocupado1, ocupado2
    
    def actualizar_leds(self):
        """Actualizar LEDs según disponibilidad de espacios"""
        ocupado1, ocupado2 = self.leer_fotoresistencias()
        
        # LED encendido = espacio libre, LED apagado = espacio ocupado
        self.led_espacio1.value(0 if ocupado1 else 1)
        self.led_espacio2.value(0 if ocupado2 else 1)
        
        # Actualizar contador de espacios
        espacios_ocupados = sum([ocupado1, ocupado2])
        self.espacios_disponibles = 2 - espacios_ocupados
    
    def abrir_barrera(self):
        """Abrir barrera del parqueo"""
        print(f"Parqueo {PARQUEO_ID} - Abriendo barrera...")
        self.servo.duty_ns(800000)  # Posición abierta
        self.barrera_abierta = True
    
    def cerrar_barrera(self):
        """Cerrar barrera del parqueo"""
        print(f"Parqueo {PARQUEO_ID} - Cerrando barrera...")
        self.servo.duty_ns(1700000)  # Posición cerrada
        self.barrera_abierta = False
    
    def procesar_ingreso(self):
        """Procesar solicitud de ingreso"""
        if self.espacios_disponibles > 0:
            print(f"Parqueo {PARQUEO_ID} - Vehículo {self.id_vehiculo_actual} solicitando ingreso...")
            
            # Registrar vehículo
            self.vehiculos_activos[self.id_vehiculo_actual] = time.time()
            
            # Abrir barrera
            self.abrir_barrera()
            print(f"Parqueo {PARQUEO_ID} - Ingreso autorizado para vehículo {self.id_vehiculo_actual}")
            
            # Esperar que el vehículo pase
            time.sleep(5)
            
            # Cerrar barrera
            self.cerrar_barrera()
            
            # Actualizar display
            self.actualizar_leds()
            self.mostrar_espacios_disponibles()
            
            self.id_vehiculo_actual += 1
            return True
        else:
            print(f"Parqueo {PARQUEO_ID} - Ingreso denegado: No hay espacios disponibles")
            # Parpadear display para indicar que está lleno
            for _ in range(3):
                self.mostrar_en_display(0)
                time.sleep(0.3)
                # Apagar display
                for segmento in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
                    self.display_pins[segmento].value(1)
                time.sleep(0.3)
            self.mostrar_espacios_disponibles()
            return False
    
    def calcular_costo(self, tiempo_entrada):
        """Calcular costo de parqueo"""
        tiempo_estancia = time.time() - tiempo_entrada
        bloques_10_segundos = max(1, int(tiempo_estancia // 10) + (1 if tiempo_estancia % 10 > 0 else 0))
        costo = bloques_10_segundos * TARIFA_POR_10_SEGUNDOS
        return costo, tiempo_estancia
    
    def procesar_pago(self):
        """Procesar solicitud de pago/salida"""
        if not self.vehiculos_activos:
            print(f"Parqueo {PARQUEO_ID} - No hay vehículos para procesar pago")
            return False
        
        if not self.modo_pago:
            # Primera presión: mostrar costo
            self.modo_pago = True
            
            # Tomar el primer vehículo (FIFO)
            vehiculo_id = min(self.vehiculos_activos.keys())
            self.vehiculo_pagando = vehiculo_id
            tiempo_entrada = self.vehiculos_activos[vehiculo_id]
            
            costo, tiempo_estancia = self.calcular_costo(tiempo_entrada)
            print(f"Parqueo {PARQUEO_ID} - Vehículo {vehiculo_id} - Tiempo: {tiempo_estancia:.0f}s - Costo: ₡{costo}")
            
            # Mostrar costo en display (solo último dígito por simplicidad)
            costo_display = int(str(int(costo/1000))[-1])  # Último dígito de miles
            self.mostrar_en_display(costo_display)
            
            print(f"Parqueo {PARQUEO_ID} - Presione nuevamente el botón de pago para completar la salida")
            return True
            
        else:
            # Segunda presión: permitir salida
            print(f"Parqueo {PARQUEO_ID} - Procesando salida del vehículo {self.vehiculo_pagando}")
            
            # Abrir barrera
            self.abrir_barrera()
            
            # Remover vehículo del registro
            del self.vehiculos_activos[self.vehiculo_pagando]
            
            print(f"Parqueo {PARQUEO_ID} - Salida autorizada para vehículo {self.vehiculo_pagando}")
            
            # Esperar que el vehículo salga
            time.sleep(5)
            
            # Cerrar barrera
            self.cerrar_barrera()
            
            # Resetear modo pago
            self.modo_pago = False
            self.vehiculo_pagando = None
            
            # Actualizar display
            self.actualizar_leds()
            self.mostrar_espacios_disponibles()
            
            return True
    
    def monitorear_botones(self):
        """Monitorear presión de botones"""
        estado_anterior_ingreso = 1
        estado_anterior_pago = 1
        
        while True:
            # Leer estado actual de botones
            estado_ingreso = self.boton_ingreso.value()
            estado_pago = self.boton_pago.value()
            
            # Detectar presión del botón de ingreso (flanco descendente)
            if estado_anterior_ingreso == 1 and estado_ingreso == 0:
                print(f"Parqueo {PARQUEO_ID} - Botón de INGRESO presionado")
                self.procesar_ingreso()
                time.sleep(0.5)  # Debounce
            
            # Detectar presión del botón de pago (flanco descendente)
            if estado_anterior_pago == 1 and estado_pago == 0:
                print(f"Parqueo {PARQUEO_ID} - Botón de PAGO presionado")
                self.procesar_pago()
                time.sleep(0.5)  # Debounce
            
            estado_anterior_ingreso = estado_ingreso
            estado_anterior_pago = estado_pago
            
            # Actualizar LEDs periódicamente
            self.actualizar_leds()
            
            time.sleep(0.1)
    
    def conectar_wifi(self):
        """Conectar a WiFi"""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        if not wlan.isconnected():
            print("Conectando a WiFi...")
            wlan.connect(SSID, PASSWORD)
            
            for i in range(20):
                if wlan.isconnected():
                    break
                print(".", end="")
                time.sleep(0.5)
            
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                print(f"\nParqueo {PARQUEO_ID} conectado a WiFi. IP: {ip}")
                return ip
            else:
                print("\nNo se pudo conectar a la red WiFi.")
                return None
        else:
            ip = wlan.ifconfig()[0]
            print(f"Parqueo {PARQUEO_ID} ya conectado a WiFi. IP: {ip}")
            return ip
    
    def procesar_comando_remoto(self, comando):
        """Procesar comandos desde la aplicación GUI remota"""
        comando = comando.strip().upper()
        print(f"Parqueo {PARQUEO_ID} - Comando remoto recibido: {comando}")
        
        if comando == "SUBIR":
            self.abrir_barrera()
            return f"Parqueo {PARQUEO_ID} - Barrera abierta remotamente"
            
        elif comando == "BAJAR":
            self.cerrar_barrera()
            return f"Parqueo {PARQUEO_ID} - Barrera cerrada remotamente"
            
        elif comando == "ABRIR_PASO":
            self.abrir_barrera()
            time.sleep(3)
            self.cerrar_barrera()
            return f"Parqueo {PARQUEO_ID} - Secuencia de paso completada"
            
        elif comando == "ESTADO":
            ocupado1, ocupado2 = self.leer_fotoresistencias()
            estado = {
                "parqueo_id": PARQUEO_ID,
                "espacios_disponibles": self.espacios_disponibles,
                "vehiculos_activos": len(self.vehiculos_activos),
                "espacio1_ocupado": ocupado1,
                "espacio2_ocupado": ocupado2,
                "barrera_abierta": self.barrera_abierta,
                "modo_pago": self.modo_pago
            }
            return json.dumps(estado)
            
        elif comando == "INGRESO_REMOTO":
            if self.procesar_ingreso():
                return f"Parqueo {PARQUEO_ID} - Ingreso remoto procesado exitosamente"
            else:
                return f"Parqueo {PARQUEO_ID} - Ingreso remoto denegado - Sin espacios disponibles"
                
        elif comando == "PAGO_REMOTO":
            if self.procesar_pago():
                return f"Parqueo {PARQUEO_ID} - Pago remoto procesado exitosamente"
            else:
                return f"Parqueo {PARQUEO_ID} - No hay vehículos para procesar pago"
                
        else:
            return f"Parqueo {PARQUEO_ID} - Comando no reconocido: {comando}"
    
    def servidor_remoto(self):
        """Servidor para comunicación remota con GUI"""
        ip = self.conectar_wifi()
        if not ip:
            print(f"Parqueo {PARQUEO_ID} - No se pudo establecer conexión WiFi para servidor remoto")
            return
        
        s = socket.socket()
        s.bind(('', PUERTO_SERVIDOR))
        s.listen(1)
        print(f"Parqueo {PARQUEO_ID} - Servidor remoto iniciado en {ip}:{PUERTO_SERVIDOR}")
        
        while True:
            try:
                conn, addr = s.accept()
                print(f"Parqueo {PARQUEO_ID} - Cliente remoto conectado desde: {addr}")
                
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    
                    comando = data.decode('utf-8').strip()
                    respuesta = self.procesar_comando_remoto(comando)
                    conn.send(respuesta.encode('utf-8'))
                
                conn.close()
                print(f"Parqueo {PARQUEO_ID} - Cliente remoto desconectado")
                
            except Exception as e:
                print(f"Parqueo {PARQUEO_ID} - Error en servidor remoto: {e}")
                time.sleep(1)
    
    def ejecutar(self):
        """Ejecutar el sistema completo"""
        print("INICIANDO PARQUEO INTELIGENTE 2")
        print("=" * 40)
        print("Componentes:")
        print("Display 7 segmentos - Espacios disponibles")
        print("Botón INGRESO - Solicitar entrada")  
        print("Botón PAGO - Mostrar costo y salir")
        print("LEDs - Indicadores de espacios")
        print("Fotoresistencias - Detección de ocupación")
        print("Servomotor - Control de barrera")
        print("WiFi - Control remoto")
        print(f"Puerto: {PUERTO_SERVIDOR}")
        print("=" * 40)
        
        # Iniciar servidor remoto en hilo separado
        try:
            _thread.start_new_thread(self.servidor_remoto, ())
            print(f"Parqueo {PARQUEO_ID} - Servidor remoto iniciado en hilo separado")
        except Exception as e:
            print(f"Parqueo {PARQUEO_ID} - Error iniciando servidor remoto: {e}")
        
        # Bucle principal - monitoreo de botones
        print(f"Parqueo {PARQUEO_ID} - Sistema listo. Monitoreando botones...")
        self.monitorear_botones()

# ========== FUNCIÓN PRINCIPAL ==========
def main():
    """Función principal"""
    try:
        parqueo = ParqueoInteligente2()
        parqueo.ejecutar()
    except KeyboardInterrupt:
        print(f"\nParqueo {PARQUEO_ID} - Sistema detenido por el usuario")
    except Exception as e:
        print(f"Parqueo {PARQUEO_ID} - Error crítico: {e}")
    finally:
        print(f"Parqueo {PARQUEO_ID} - Limpiando recursos...")

if __name__ == "__main__":
    main()