#!/usr/bin/env python3
"""
Script de prueba para verificar el sistema de parqueos dual
Simula conexiones de Raspberry Pi para probar la funcionalidad del GUI
"""

import socket
import threading
import time
import sys

class MockRaspberryPi:
    """Servidor simulado de Raspberry Pi para pruebas"""
    
    def __init__(self, parqueo_id, puerto):
        self.parqueo_id = parqueo_id
        self.puerto = puerto
        self.running = False
        self.servidor = None
        
    def iniciar_servidor(self):
        """Iniciar el servidor simulado"""
        try:
            self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.servidor.bind(('localhost', self.puerto))
            self.servidor.listen(1)
            self.running = True
            
            print(f"Mock Parqueo {self.parqueo_id} iniciado en puerto {self.puerto}")
            
            while self.running:
                try:
                    cliente, direccion = self.servidor.accept()
                    print(f"Parqueo {self.parqueo_id}: Conexión desde {direccion}")
                    
                    # Leer comando
                    data = cliente.recv(1024).decode('utf-8').strip()
                    print(f"Parqueo {self.parqueo_id}: Comando recibido: {data}")
                    
                    # Responder según el comando
                    if data == "ESTADO":
                        respuesta = f"ESTADO_OK_PARQUEO_{self.parqueo_id}"
                    elif data in ["SUBIR", "BAJAR", "ABRIR_PASO"]:
                        respuesta = f"OK_{data}_PARQUEO_{self.parqueo_id}"
                    else:
                        respuesta = f"ERROR_COMANDO_DESCONOCIDO_{data}"
                    
                    cliente.send(respuesta.encode('utf-8'))
                    print(f"Parqueo {self.parqueo_id}: Respuesta enviada: {respuesta}")
                    cliente.close()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Error en Parqueo {self.parqueo_id}: {e}")
                    break
                    
        except Exception as e:
            print(f"Error iniciando Mock Parqueo {self.parqueo_id}: {e}")
        finally:
            if self.servidor:
                self.servidor.close()
    
    def detener_servidor(self):
        """Detener el servidor simulado"""
        self.running = False
        if self.servidor:
            self.servidor.close()
        print(f"Mock Parqueo {self.parqueo_id} detenido")

def main():
    """Función principal del simulador"""
    print("SIMULADOR DE RASPBERRY PI PARA PARQUEOS")
    print("=" * 50)
    print("Este script simula las dos Raspberry Pi para probar el GUI")
    print("Presiona Ctrl+C para detener")
    print("=" * 50)
    
    # Crear servidores simulados
    parqueo1 = MockRaspberryPi(1, 1718)
    parqueo2 = MockRaspberryPi(2, 1719)
    
    # Iniciar servidores en hilos separados
    try:
        hilo1 = threading.Thread(target=parqueo1.iniciar_servidor, daemon=True)
        hilo2 = threading.Thread(target=parqueo2.iniciar_servidor, daemon=True)
        
        hilo1.start()
        time.sleep(0.5)  # Pequeña pausa entre inicios
        hilo2.start()
        
        print(f"\nAmbos servidores simulados iniciados")
        print(f"Parqueo 1: localhost:1718")
        print(f"Parqueo 2: localhost:1719")
        print(f"\nAhora puedes ejecutar GUI.py y usar localhost como IP para ambos parqueos")
        print(f"Esperando conexiones... (Ctrl+C para salir)\n")
        
        # Mantener el programa corriendo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\nDeteniendo simuladores...")
        parqueo1.detener_servidor()
        parqueo2.detener_servidor()
        print(f"Simuladores detenidos correctamente")
        sys.exit(0)
    except Exception as e:
        print(f"Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()