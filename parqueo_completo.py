"""
PARQUEO INTELIGENTE - CÓDIGO COMPLETO PARA RASPBERRY PI
======================================================
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
PUERTO_SERVIDOR = 1718

# ========== CONFIGURACIÓN DE PINES ==========
# Servomotor (barrera)
SERVO_PIN = 26 #adc0

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
BOTON_INGRESO = 17
BOTON_PAGO = 14

# LEDs indicadores de espacios
LED_ESPACIO_1 = 15
LED_ESPACIO_2 = 16

# Fotoresistencias (ADC)
FOTO_ESPACIO_1 = 28  # ADC0
FOTO_ESPACIO_2 = 27 # ADC1

# ========== CONFIGURACIÓN DE TARIFAS ==========
TARIFA_POR_10_SEGUNDOS = 1000  # Colones
UMBRAL_FOTORESISTENCIA = 40000  # Valor para detectar ocupación (valores MAYORES = libre con luz)

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

class ParqueoInteligente:
    """Clase principal para manejar el parqueo inteligente"""
    
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
        print("Inicializando hardware del parqueo inteligente...")
        
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
        
        print("Hardware inicializado correctamente")
    
    def mostrar_en_display(self, numero):
        """Mostrar número en display 7 segmentos (0-9)"""
        if numero < 0 or numero > 9:
            numero = 0
            
        patron = DIGITOS_7SEG[numero]
        
        for segmento in ['a', 'b', 'c', 'd', 'e', 'f', 'g']:
            self.display_pins[segmento].value(patron[segmento])
    
    def mostrar_espacios_disponibles(self):
        """Mostrar espacios disponibles (solo en consola, display no disponible)"""
        # self.mostrar_en_display(self.espacios_disponibles)  # Display deshabilitado
        print(f"Espacios disponibles: {self.espacios_disponibles}/2 (Display 7-seg no disponible)")
    
    def probar_display_7_segmentos(self):
        """Probar el display 7 segmentos mostrando números del 0 al 9"""
        print("\n=== PRUEBA DISPLAY 7 SEGMENTOS ===")
        print("Mostrando números del 0 al 9...")
        
        for numero in range(10):
            print(f"Mostrando número: {numero}")
            self.mostrar_en_display(numero)
            time.sleep(1)
        
        # Volver al estado normal
        self.mostrar_espacios_disponibles()
        print("Prueba de display completada\n")
    
    def leer_fotoresistencias(self):
        """Leer estado de las fotoresistencias"""
        valor1 = self.foto_espacio1.read_u16()
        valor2 = self.foto_espacio2.read_u16()
        
        # True = ocupado, False = libre
        # Más luz (valores altos) = LIBRE, menos luz (valores bajos) = OCUPADO
        ocupado1 = valor1 < UMBRAL_FOTORESISTENCIA  # Si hay poca luz = ocupado
        ocupado2 = valor2 < UMBRAL_FOTORESISTENCIA  # Si hay mucha luz = libre
        
        return ocupado1, ocupado2
    
    def probar_fotoresistencias(self):
        """Probar las fotoresistencias y mostrar valores"""
        print("\n=== PRUEBA FOTORESISTENCIAS ===")
        print("Leyendo valores de fotoresistencias por 10 segundos...")
        print(f"Umbral de detección: {UMBRAL_FOTORESISTENCIA}")
        print("Valores menores al umbral = OCUPADO (poca luz)")
        print("Valores mayores al umbral = LIBRE (mucha luz)")
        print("Apunta la linterna a las fotoceldas para simular espacios libres\n")
        
        for i in range(10):
            valor1 = self.foto_espacio1.read_u16()
            valor2 = self.foto_espacio2.read_u16()
            
            estado1 = "OCUPADO" if valor1 < UMBRAL_FOTORESISTENCIA else "LIBRE"
            estado2 = "OCUPADO" if valor2 < UMBRAL_FOTORESISTENCIA else "LIBRE"
            
            print(f"Lectura {i+1}: Espacio1={valor1} ({estado1}) | Espacio2={valor2} ({estado2})")
            time.sleep(1)
        
        print("Prueba de fotoresistencias completada\n")
    
    def actualizar_leds(self):
        """Actualizar LEDs según disponibilidad de espacios"""
        ocupado1, ocupado2 = self.leer_fotoresistencias()
        
        # LED encendido = espacio libre, LED apagado = espacio ocupado
        self.led_espacio1.value(0 if ocupado1 else 1)
        self.led_espacio2.value(0 if ocupado2 else 1)
        
        # Actualizar contador de espacios
        espacios_ocupados = sum([ocupado1, ocupado2])
        self.espacios_disponibles = 2 - espacios_ocupados
    
    def probar_leds(self):
        """Probar los LEDs de los espacios"""
        print("\n=== PRUEBA LEDS DE ESPACIOS ===")
        
        # Encender LED 1
        print("Encendiendo LED Espacio 1...")
        self.led_espacio1.value(1)
        self.led_espacio2.value(0)
        time.sleep(2)
        
        # Encender LED 2
        print("Encendiendo LED Espacio 2...")
        self.led_espacio1.value(0)
        self.led_espacio2.value(1)
        time.sleep(2)
        
        # Encender ambos
        print("Encendiendo ambos LEDs...")
        self.led_espacio1.value(1)
        self.led_espacio2.value(1)
        time.sleep(2)
        
        # Apagar ambos
        print("Apagando ambos LEDs...")
        self.led_espacio1.value(0)
        self.led_espacio2.value(0)
        time.sleep(1)
        
        # Volver al estado normal
        self.actualizar_leds()
        print("Prueba de LEDs completada\n")
    
    def abrir_barrera(self):
        """Abrir barrera del parqueo"""
        print("Abriendo barrera...")
        self.servo.duty_ns(800000)  # Posición abierta
        self.barrera_abierta = True
    
    def cerrar_barrera(self):
        """Cerrar barrera del parqueo"""
        print("Cerrando barrera...")
        self.servo.duty_ns(1700000)  # Posición cerrada
        self.barrera_abierta = False
    
    def probar_servomotor(self):
        """Probar el movimiento del servomotor (barrera)"""
        print("\n=== PRUEBA SERVOMOTOR (BARRERA) ===")
        
        # Estado inicial (cerrada)
        print("Posición inicial: CERRADA")
        self.servo.duty_ns(1700000)
        time.sleep(2)
        
        # Abrir barrera
        print("Abriendo barrera...")
        self.servo.duty_ns(800000)
        time.sleep(2)
        
        # Posiciones intermedias
        print("Posición intermedia 1...")
        self.servo.duty_ns(1250000)
        time.sleep(2)
        
        print("Posición intermedia 2...")
        self.servo.duty_ns(1000000)
        time.sleep(2)
        
        # Volver a cerrar
        print("Cerrando barrera...")
        self.servo.duty_ns(1700000)
        time.sleep(2)
        
        self.barrera_abierta = False
        print("Prueba de servomotor completada\n")
    
    def procesar_ingreso(self):
        """Procesar solicitud de ingreso"""
        if self.espacios_disponibles > 0:
            print(f"Vehículo {self.id_vehiculo_actual} solicitando ingreso...")
            
            # Registrar vehículo
            self.vehiculos_activos[self.id_vehiculo_actual] = time.time()
            
            # Abrir barrera
            self.abrir_barrera()
            print(f"Ingreso autorizado para vehículo {self.id_vehiculo_actual}")
            
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
            print("Ingreso denegado: No hay espacios disponibles")
            # Indicación visual deshabilitada (display no disponible)
            print("PARQUEO LLENO - PARQUEO LLENO - PARQUEO LLENO")
            for _ in range(3):
                print("*** ESPACIO NO DISPONIBLE ***")
                time.sleep(0.5)
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
            print("No hay vehículos para procesar pago")
            return False
        
        if not self.modo_pago:
            # Primera presión: mostrar costo
            self.modo_pago = True
            
            # Tomar el primer vehículo (FIFO)
            vehiculo_id = min(self.vehiculos_activos.keys())
            self.vehiculo_pagando = vehiculo_id
            tiempo_entrada = self.vehiculos_activos[vehiculo_id]
            
            costo, tiempo_estancia = self.calcular_costo(tiempo_entrada)
            print(f"Vehículo {vehiculo_id} - Tiempo: {tiempo_estancia:.0f}s - Costo: ₡{costo}")
            
            # Mostrar costo (display no disponible - solo consola)
            print(f"*** COSTO A PAGAR: ₡{costo} ***")
            print(f"*** TIEMPO: {tiempo_estancia:.0f} segundos ***")
            
            print(f"Presione nuevamente el botón de pago para completar la salida")
            return True
            
        else:
            # Segunda presión: permitir salida
            print(f"Procesando salida del vehículo {self.vehiculo_pagando}")
            
            # Abrir barrera
            self.abrir_barrera()
            
            # Remover vehículo del registro
            del self.vehiculos_activos[self.vehiculo_pagando]
            
            print(f"Salida autorizada para vehículo {self.vehiculo_pagando}")
            
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
                print("Botón de INGRESO presionado")
                self.procesar_ingreso()
                time.sleep(0.5)  # Debounce
            
            # Detectar presión del botón de pago (flanco descendente)
            if estado_anterior_pago == 1 and estado_pago == 0:
                print("Botón de PAGO presionado")
                self.procesar_pago()
                time.sleep(0.5)  # Debounce
            
            estado_anterior_ingreso = estado_ingreso
            estado_anterior_pago = estado_pago
            
            # Actualizar LEDs periódicamente
            self.actualizar_leds()
            
            time.sleep(0.1)
    
    def probar_botones(self):
        """Probar los botones de ingreso y pago"""
        print("\n=== PRUEBA BOTONES ===")
        print("Presiona los botones para probarlos (10 segundos)...")
        print("Botón INGRESO: Pin 10")
        print("Botón PAGO: Pin 11")
        print("(Los botones usan pull-up, presionar = 0, suelto = 1)\n")
        
        tiempo_inicial = time.time()
        estado_anterior_ingreso = 1
        estado_anterior_pago = 1
        
        while time.time() - tiempo_inicial < 10:
            estado_ingreso = self.boton_ingreso.value()
            estado_pago = self.boton_pago.value()
            
            # Detectar presión del botón de ingreso
            if estado_anterior_ingreso == 1 and estado_ingreso == 0:
                print("¡BOTÓN INGRESO PRESIONADO!")
            elif estado_anterior_ingreso == 0 and estado_ingreso == 1:
                print("Botón ingreso liberado")
            
            # Detectar presión del botón de pago
            if estado_anterior_pago == 1 and estado_pago == 0:
                print("¡BOTÓN PAGO PRESIONADO!")
            elif estado_anterior_pago == 0 and estado_pago == 1:
                print("Botón pago liberado")
            
            estado_anterior_ingreso = estado_ingreso
            estado_anterior_pago = estado_pago
            time.sleep(0.1)
        
        print("Prueba de botones completada\n")
    
    def mostrar_estado_componentes(self):
        """Mostrar estado actual de todos los componentes"""
        print("\n=== ESTADO ACTUAL DE COMPONENTES ===")
        
        # Display 7 segmentos
        print("Display 7 Segmentos: NO DISPONIBLE (Hardware no conectado)")
        
        # Estado de fotoresistencias
        valor1 = self.foto_espacio1.read_u16()
        valor2 = self.foto_espacio2.read_u16()
        estado1 = "OCUPADO" if valor1 < UMBRAL_FOTORESISTENCIA else "LIBRE"
        estado2 = "OCUPADO" if valor2 < UMBRAL_FOTORESISTENCIA else "LIBRE"
        
        print(f"Fotoresistencias:")
        print(f"  Espacio 1: {valor1} ({estado1})")
        print(f"  Espacio 2: {valor2} ({estado2})")
        
        # Estado de LEDs
        led1_estado = "ENCENDIDO" if self.led_espacio1.value() else "APAGADO"
        led2_estado = "ENCENDIDO" if self.led_espacio2.value() else "APAGADO"
        print(f"LEDs:")
        print(f"  LED Espacio 1: {led1_estado}")
        print(f"  LED Espacio 2: {led2_estado}")
        
        # Estado de botones
        boton_ing = "PRESIONADO" if not self.boton_ingreso.value() else "LIBRE"
        boton_pago = "PRESIONADO" if not self.boton_pago.value() else "LIBRE"
        print(f"Botones:")
        print(f"  Botón Ingreso: {boton_ing}")
        print(f"  Botón Pago: {boton_pago}")
        
        # Estado general
        print(f"Sistema:")
        print(f"  Espacios disponibles: {self.espacios_disponibles}/2")
        print(f"  Barrera: {'ABIERTA' if self.barrera_abierta else 'CERRADA'}")
        print(f"  Vehículos activos: {len(self.vehiculos_activos)}")
        print(f"  Próximo ID vehículo: {self.id_vehiculo_actual}")
        
        print("================================\n")
    
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
                print(f"\nConectado a WiFi. IP: {ip}")
                return ip
            else:
                print("\nNo se pudo conectar a la red WiFi.")
                return None
        else:
            ip = wlan.ifconfig()[0]
            print(f"Ya conectado a WiFi. IP: {ip}")
            return ip
    
    def procesar_comando_remoto(self, comando):
        """Procesar comandos desde la aplicación GUI remota"""
        comando = comando.strip().upper()
        print(f"Comando remoto recibido: {comando}")
        
        if comando == "SUBIR":
            self.abrir_barrera()
            return "Barrera abierta remotamente"
            
        elif comando == "BAJAR":
            self.cerrar_barrera()
            return "Barrera cerrada remotamente"
            
        elif comando == "ABRIR_PASO":
            self.abrir_barrera()
            time.sleep(3)
            self.cerrar_barrera()
            return "Secuencia de paso completada"
            
        elif comando == "ESTADO":
            ocupado1, ocupado2 = self.leer_fotoresistencias()
            estado = {
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
                return "Ingreso remoto procesado exitosamente"
            else:
                return "Ingreso remoto denegado - Sin espacios disponibles"
                
        elif comando == "PAGO_REMOTO":
            if self.procesar_pago():
                return "Pago remoto procesado exitosamente"
            else:
                return "No hay vehículos para procesar pago"
                
        else:
            return f"Comando no reconocido: {comando}"
    
    def servidor_remoto(self):
        """Servidor para comunicación remota con GUI"""
        ip = self.conectar_wifi()
        if not ip:
            print("No se pudo establecer conexión WiFi para servidor remoto")
            return
        
        s = socket.socket()
        s.bind(('', PUERTO_SERVIDOR))
        s.listen(1)
        print(f"Servidor remoto iniciado en {ip}:{PUERTO_SERVIDOR}")
        
        while True:
            try:
                conn, addr = s.accept()
                print(f"Cliente remoto conectado desde: {addr}")
                
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    
                    comando = data.decode('utf-8').strip()
                    respuesta = self.procesar_comando_remoto(comando)
                    conn.send(respuesta.encode('utf-8'))
                
                conn.close()
                print("Cliente remoto desconectado")
                
            except Exception as e:
                print(f"Error en servidor remoto: {e}")
                time.sleep(1)
    
    def ejecutar_pruebas_componentes(self):
        """Ejecutar todas las pruebas de componentes"""
        print("\n" + "=" * 50)
        print("    SISTEMA DE PRUEBAS - PARQUEO INTELIGENTE")
        print("=" * 50)
        print("Iniciando pruebas de todos los componentes...\n")
        
        try:
            # Prueba 1: Display 7 segmentos (DESHABILITADO - Hardware no disponible)
            print("Saltando prueba de Display 7 segmentos - Hardware no disponible\n")
            # self.probar_display_7_segmentos()
            
            # Prueba 2: LEDs
            self.probar_leds()
            
            # Prueba 3: Servomotor
            self.probar_servomotor()
            
            # Prueba 4: Fotoresistencias
            self.probar_fotoresistencias()
            
            # Prueba 5: Botones
            self.probar_botones()
            
            print("=" * 50)
            print("    TODAS LAS PRUEBAS COMPLETADAS")
            print("=" * 50)
            
        except Exception as e:
            print(f"Error durante las pruebas: {e}")
    
    def mostrar_menu_pruebas(self):
        """Mostrar menú de opciones de prueba"""
        while True:
            print("\n" + "=" * 40)
            print("    MENÚ DE PRUEBAS - PARQUEO INTELIGENTE")
            print("=" * 40)
            print("1. Probar Display 7 Segmentos (NO DISPONIBLE)")
            print("2. Probar LEDs")
            print("3. Probar Servomotor (Barrera)")
            print("4. Probar Fotoresistencias")
            print("5. Probar Botones")
            print("6. Mostrar Estado de Componentes")
            print("7. Ejecutar TODAS las pruebas disponibles")
            print("8. Iniciar sistema normal")
            print("9. Salir")
            print("=" * 40)
            
            try:
                # En MicroPython, adaptar según tu método de entrada preferido
                print("MÉTODO DE SELECCIÓN EN MICROPYTHON:")
                print("- Modifica el código para usar botones físicos")
                print("- O usa conexión serial/WiFi para comandos")
                print("- O cambia la variable de selección directamente")
                print()
                
                # Variable para seleccionar función (modificar según necesites)
                SELECCION = 4  # Cambiar este valor para probar diferentes funciones
                               # 1=Display(NO DISP), 2=LEDs, 3=Servo, 4=Fotores, 5=Botones, 
                               # 6=Estado, 7=Todas disponibles, 8=Normal, 9=Salir
                
                print(f"Ejecutando opción {SELECCION}...")
                
                if SELECCION == 1:
                    print("Display 7 segmentos no disponible - Hardware no conectado")
                    print("Saltando a prueba de LEDs...\n")
                    self.probar_leds()
                elif SELECCION == 2:
                    self.probar_leds()
                elif SELECCION == 3:
                    self.probar_servomotor()
                elif SELECCION == 4:
                    self.probar_fotoresistencias()
                elif SELECCION == 5:
                    self.probar_botones()
                elif SELECCION == 6:
                    self.mostrar_estado_componentes()
                elif SELECCION == 7:
                    self.ejecutar_pruebas_componentes()
                elif SELECCION == 8:
                    self.ejecutar_sistema_normal()
                    break
                elif SELECCION == 9:
                    print("Saliendo del sistema de pruebas...")
                    break
                else:
                    print("Opción no válida. Ejecutando todas las pruebas por defecto...")
                    self.ejecutar_pruebas_componentes()
                
                # Para continuar con más pruebas, cambiar esta línea:
                break  # Cambiar por 'continue' si quieres repetir el menú
                    
            except KeyboardInterrupt:
                print("\nSaliendo del sistema...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def ejecutar_sistema_normal(self):
        """Ejecutar el sistema completo en modo normal"""
        print("\nINICIANDO PARQUEO INTELIGENTE - MODO NORMAL")
        print("=" * 50)
        print("Componentes activos:")
        print("- Display 7 segmentos")
        print("- 2 LEDs indicadores") 
        print("- 2 Fotoresistencias")
        print("- 2 Botones (Ingreso/Pago)")
        print("- 1 Servomotor (Barrera)")
        print("- Servidor WiFi remoto")
        print("=" * 50)
        
        # Iniciar servidor remoto en hilo separado
        try:
            _thread.start_new_thread(self.servidor_remoto, ())
            print("Servidor remoto iniciado en hilo separado")
        except Exception as e:
            print(f"Error iniciando servidor remoto: {e}")
        
        # Bucle principal - monitoreo de botones
        print("Sistema listo. Monitoreando botones...")
        self.monitorear_botones()
    
    def ejecutar(self):
        """Punto de entrada principal del sistema"""
        print("\nSISTEMA DE PARQUEO INTELIGENTE INICIADO")
        print("Opciones disponibles:")
        print("1. Ejecutar pruebas de componentes")
        print("2. Iniciar sistema normal")
        
        # En MicroPython es difícil hacer input interactivo
        # Por defecto iniciamos con el menú de pruebas
        print("\nIniciando con menú de pruebas...")
        self.mostrar_menu_pruebas()
    
    def ejecutar_solo_normal(self):
        """Ejecutar solo el sistema normal (sin menú)"""
        print("INICIANDO PARQUEO INTELIGENTE")
        print("=" * 40)
        print("Componentes:")
        print(" Display 7 segmentos - Espacios disponibles")
        print(" Botón INGRESO - Solicitar entrada")  
        print(" Botón PAGO - Mostrar costo y salir")
        print(" LEDs - Indicadores de espacios")
        print(" Fotoresistencias - Detección de ocupación")
        print(" Servomotor - Control de barrera")
        print(" WiFi - Control remoto")
        print("=" * 40)
        
        # Iniciar servidor remoto en hilo separado
        try:
            _thread.start_new_thread(self.servidor_remoto, ())
            print("Servidor remoto iniciado en hilo separado")
        except Exception as e:
            print(f"Error iniciando servidor remoto: {e}")
        
        # Bucle principal - monitoreo de botones
        print("Sistema listo. Monitoreando botones...")
        self.monitorear_botones()

# ========== FUNCIÓN PRINCIPAL ==========
def main():
    """Función principal"""
    try:
        parqueo = ParqueoInteligente()
        
        print("\n" + "=" * 50)
        print("    PARQUEO INTELIGENTE - SISTEMA DE CONTROL")
        print("=" * 50)
        print("Modos de operación disponibles:")
        print("1. MODO PRUEBAS - Verificar todos los componentes")
        print("2. MODO NORMAL - Sistema operativo completo")
        print("=" * 50)
        
        # Para MicroPython, modificar esta sección según necesites:
        # Opción A: Usar un botón físico para elegir modo
        # Opción B: Configurar por defecto uno u otro
        # Opción C: Usar pin específico como selector
        
        # Por defecto, iniciar con pruebas (cambiar si necesitas)
        MODO_PRUEBAS = True  # Cambiar a False para modo normal directo
        
        if MODO_PRUEBAS:
            print("\nIniciando en MODO PRUEBAS...")
            print("(Para cambiar a modo normal, modifica MODO_PRUEBAS = False)")
            parqueo.ejecutar()  # Incluye menú de pruebas
        else:
            print("\nIniciando en MODO NORMAL...")
            parqueo.ejecutar_solo_normal()  # Solo sistema operativo
            
    except KeyboardInterrupt:
        print("\nSistema detenido por el usuario")
    except Exception as e:
        print(f"Error crítico: {e}")
    finally:
        print("Limpiando recursos...")

if __name__ == "__main__":
    main()