from machine import Pin, PWM
import time
import socket
import network

SSDI = "Admiti q sos pobre"
PASSWORD = "soy pobre"
 

servoprofe = PWM(Pin(28))
servoprofe.freq(50)
v_grados = 45
v_repetir = 2

# Inicializar servomotor en posición cerrada (barrera abajo)
servoprofe.duty_ns(1700000)  # Posición inicial: barrera cerrada

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Conectando a WiFi...")
        wlan.connect(SSDI, PASSWORD)
        
        for i in range(20):
            if wlan.isconnected():
                break
            print(".", end="")
            time.sleep(0.5)
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("\nConectado a WiFi. IP:", ip)
            return ip
        else:
            print("\nNo se pudo conectar a la red WiFi.")
            return None
def start_server():
    ip = connect_wifi()
    if not ip:
        return
    s = socket.socket()
    s.bind(('', 1718))
    s.listen(1)
    print(f"Servidor iniciado en {ip}:1718")
    print("Esperando cliente...")
    # indicaciones para raspberry sobre subir o bajar el servomotor y permitir la entrada del carro

    while True:
            try:
                conn, addr = s.accept()
                print("Cliente conectado desde:", addr)
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    command = data.decode('utf-8').strip()
                    print("Comando recibido:", command)
                    
                    if command == "SUBIR":
                        servoprofe.duty_ns(800000)  # Posición para subir (barrera abierta)
                        response = "Barrera subiendo - Carro puede pasar."
                        print("Barrera ABIERTA - Permitiendo paso del carro")
                        
                    elif command == "BAJAR":
                        servoprofe.duty_ns(1700000)  # Posición para bajar (barrera cerrada)
                        response = "Barrera bajando - Paso bloqueado."
                        print("Barrera CERRADA - Paso bloqueado")
                        
                    elif command == "ABRIR_PASO":
                        # Comando especial: abrir, esperar, y cerrar automáticamente
                        servoprofe.duty_ns(800000)  # Abrir barrera
                        print("Barrera ABIERTA - Carro pasando...")
                        time.sleep(3)  # Esperar 3 segundos para que pase el carro
                        servoprofe.duty_ns(1700000)  # Cerrar barrera
                        print("Barrera CERRADA - Paso completado")
                        response = "Secuencia de paso completada."
                        
                    else:
                        response = "Comando no reconocido. Usar: SUBIR, BAJAR, o ABRIR_PASO"
                    
                    conn.send(response.encode('utf-8'))
                conn.close()
                print("Cliente desconectado.")
            except Exception as e:
                    print(f"Error en conexión: {e}")
                    time.sleep(1)

try:
    start_server()
except KeyboardInterrupt:
    print("\nServidor detenido")
except Exception as e:
    print("Error crítico:", e)

