"""
GUI para administración de parqueos
Funcionalidades:
1. Calcular costo de parqueo (1000 colones por 10 segundos)
2. Visualizar espacios disponibles en tiempo real
3. Controlar LEDs remotamente
4. Controlar barrera de entrada/salida
5. Estadísticas históricas y ganancias
"""
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import time
import datetime
import json
import requests
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import os

# Configuración
# PARA RASPBERRY PI REALES: Cambiar por las IPs reales de tus Raspberry Pi
RASPBERRY_IP_1 = "10.99.207.214"  # IP real de la Raspberry Pi 1 (Parqueo 1)
RASPBERRY_IP_2 = "10.99.207.111"  # IP real de la Raspberry Pi 2 (Parqueo 2)
# PARA PRUEBAS CON SIMULADOR: Usar "localhost" para ambas

RASPBERRY_PORT_1 = 1718  # Puerto para Parqueo 1
RASPBERRY_PORT_2 = 1719  # Puerto para Parqueo 2
ESPACIOS_TOTALES = 2  # Total de espacios por parqueo 
TARIFA_POR_10_SEGUNDOS = 1000  # Colones

@dataclass
class Vehiculo:
    """Clase para representar un vehículo en el parqueo"""
    id: str
    hora_entrada: datetime.datetime
    hora_salida: Optional[datetime.datetime] = None
    parqueo: int = 1  # 1 o 2
    costo: int = 0
    pagado: bool = False

class ParqueoManager:
    """Manejador principal del sistema de parqueos"""
    
    def __init__(self):
        self.vehiculos_activos = {}  # ID -> Vehiculo
        self.historial_vehiculos = []  # Lista de todos los vehículos
        self.espacios_ocupados = {"parqueo1": 0, "parqueo2": 0}
        self.leds_estado = {"parqueo1": [False] * ESPACIOS_TOTALES, "parqueo2": [False] * ESPACIOS_TOTALES}
        self.tipo_cambio_usd = 500  # Valor por defecto
        self.conexiones_raspberry = {"parqueo1": False, "parqueo2": False}
        self.ips_raspberry = {"parqueo1": RASPBERRY_IP_1, "parqueo2": RASPBERRY_IP_2}
        self.puertos_raspberry = {"parqueo1": RASPBERRY_PORT_1, "parqueo2": RASPBERRY_PORT_2}
        self.cargar_datos()
        self.actualizar_tipo_cambio()
    
    def actualizar_tipo_cambio(self):
        """Obtener tipo de cambio actual del dólar"""
        try:
            # API gratuita para tipo de cambio
            response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
            data = response.json()
            # Aproximación para colones costarricenses (usar valor fijo si no está disponible)
            self.tipo_cambio_usd = 509  # Valor aproximado actual
            print(f"Tipo de cambio actualizado: ₡{self.tipo_cambio_usd} por $1")
        except:
            print("No se pudo actualizar el tipo de cambio, usando valor por defecto")
    
    def registrar_entrada(self, vehiculo_id: str, parqueo: int):
        """Registrar la entrada de un vehículo"""
        if vehiculo_id in self.vehiculos_activos:
            return False, "El vehículo ya está en el parqueo"
        
        vehiculo = Vehiculo(
            id=vehiculo_id,
            hora_entrada=datetime.datetime.now(),
            parqueo=parqueo
        )
        
        self.vehiculos_activos[vehiculo_id] = vehiculo
        self.espacios_ocupados[f"parqueo{parqueo}"] += 1
        self.guardar_datos()
        return True, f"Vehículo {vehiculo_id} registrado en parqueo {parqueo}"
    
    def registrar_salida(self, vehiculo_id: str):
        """Registrar la salida de un vehículo y calcular costo"""
        if vehiculo_id not in self.vehiculos_activos:
            return False, "El vehículo no está registrado en el parqueo", 0
        
        vehiculo = self.vehiculos_activos[vehiculo_id]
        vehiculo.hora_salida = datetime.datetime.now()
        
        # Calcular tiempo de estancia en segundos
        tiempo_estancia = (vehiculo.hora_salida - vehiculo.hora_entrada).total_seconds()
        
        # Calcular costo (1000 colones por cada 10 segundos)
        bloques_10_segundos = max(1, int(tiempo_estancia // 10) + (1 if tiempo_estancia % 10 > 0 else 0))
        vehiculo.costo = bloques_10_segundos * TARIFA_POR_10_SEGUNDOS
        
        # Mover al historial
        self.historial_vehiculos.append(vehiculo)
        del self.vehiculos_activos[vehiculo_id]
        self.espacios_ocupados[f"parqueo{vehiculo.parqueo}"] -= 1
        self.guardar_datos()
        
        return True, f"Vehículo {vehiculo_id} salió. Tiempo: {tiempo_estancia:.0f}s", vehiculo.costo
    
    def toggle_led(self, parqueo: int, espacio: int):
        """Cambiar estado de un LED específico"""
        parqueo_key = f"parqueo{parqueo}"
        if 0 <= espacio < ESPACIOS_TOTALES:
            self.leds_estado[parqueo_key][espacio] = not self.leds_estado[parqueo_key][espacio]
            
            # Actualizar contador de espacios ocupados
            self.espacios_ocupados[parqueo_key] = sum(self.leds_estado[parqueo_key])
            return True
        return False
    
    def obtener_estadisticas(self):
        """Obtener estadísticas históricas"""
        if not self.historial_vehiculos:
            return {
                "total_vehiculos": {"parqueo1": 0, "parqueo2": 0, "total": 0},
                "ganancias_colones": {"parqueo1": 0, "parqueo2": 0, "total": 0},
                "ganancias_dolares": {"parqueo1": 0, "parqueo2": 0, "total": 0}
            }
        
        stats = {
            "total_vehiculos": {"parqueo1": 0, "parqueo2": 0, "total": 0},
            "ganancias_colones": {"parqueo1": 0, "parqueo2": 0, "total": 0},
            "ganancias_dolares": {"parqueo1": 0.0, "parqueo2": 0.0, "total": 0.0}
        }
        
        for vehiculo in self.historial_vehiculos:
            parqueo_key = f"parqueo{vehiculo.parqueo}"
            stats["total_vehiculos"][parqueo_key] += 1
            stats["total_vehiculos"]["total"] += 1
            
            stats["ganancias_colones"][parqueo_key] += vehiculo.costo
            stats["ganancias_colones"]["total"] += vehiculo.costo
        
        # Convertir a dólares
        for key in ["parqueo1", "parqueo2", "total"]:
            stats["ganancias_dolares"][key] = round(stats["ganancias_colones"][key] / self.tipo_cambio_usd, 2)
        
        return stats
    
    def verificar_conexion_raspberry(self, parqueo: int):
        """Verificar conexión con una Raspberry Pi específica"""
        parqueo_key = f"parqueo{parqueo}"
        ip = self.ips_raspberry[parqueo_key]
        puerto = self.puertos_raspberry[parqueo_key]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((ip, puerto))
                s.send("ESTADO".encode('utf-8'))
                response = s.recv(1024).decode('utf-8')
                # Verificar que la respuesta sea válida
                if "ESTADO_OK" in response or "OK" in response:
                    self.conexiones_raspberry[parqueo_key] = True
                    return True, f"Parqueo {parqueo} conectado en {ip}:{puerto} - Respuesta: {response}"
                else:
                    self.conexiones_raspberry[parqueo_key] = False
                    return False, f"Respuesta inválida de Parqueo {parqueo}: {response}"
        except ConnectionRefusedError:
            self.conexiones_raspberry[parqueo_key] = False
            return False, f"Conexión rechazada a Parqueo {parqueo} en {ip}:{puerto} - ¿Servidor iniciado?"
        except socket.timeout:
            self.conexiones_raspberry[parqueo_key] = False
            return False, f"Timeout conectando a Parqueo {parqueo} en {ip}:{puerto}"
        except Exception as e:
            self.conexiones_raspberry[parqueo_key] = False
            return False, f"Error conectando Parqueo {parqueo}: {str(e)}"
    
    def verificar_todas_conexiones(self):
        """Verificar conexión con todas las Raspberry Pi"""
        resultados = {}
        for parqueo in [1, 2]:
            exito, mensaje = self.verificar_conexion_raspberry(parqueo)
            resultados[f"parqueo{parqueo}"] = {"conectado": exito, "mensaje": mensaje}
        return resultados
    
    def todas_raspberry_conectadas(self):
        """Verificar si todas las Raspberry Pi están conectadas"""
        return all(self.conexiones_raspberry.values())
    
    def controlar_barrera(self, accion: str, parqueo: int = 1):
        """Enviar comando a la barrera (Raspberry Pi específica)"""
        parqueo_key = f"parqueo{parqueo}"
        ip = self.ips_raspberry[parqueo_key]
        puerto = self.puertos_raspberry[parqueo_key]
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((ip, puerto))
                s.send(accion.encode('utf-8'))
                response = s.recv(1024).decode('utf-8')
                return True, response
        except Exception as e:
            return False, f"Error de conexión con Parqueo {parqueo}: {str(e)}"
    
    def guardar_datos(self):
        """Guardar datos en archivo JSON"""
        datos = {
            "vehiculos_activos": {k: asdict(v) for k, v in self.vehiculos_activos.items()},
            "historial_vehiculos": [asdict(v) for v in self.historial_vehiculos],
            "espacios_ocupados": self.espacios_ocupados,
            "leds_estado": self.leds_estado
        }
        
        # Convertir datetime a string para JSON
        for vehiculo in datos["vehiculos_activos"].values():
            vehiculo["hora_entrada"] = vehiculo["hora_entrada"].isoformat() if isinstance(vehiculo["hora_entrada"], datetime.datetime) else vehiculo["hora_entrada"]
            if vehiculo["hora_salida"]:
                vehiculo["hora_salida"] = vehiculo["hora_salida"].isoformat()
        
        for vehiculo in datos["historial_vehiculos"]:
            vehiculo["hora_entrada"] = vehiculo["hora_entrada"].isoformat() if isinstance(vehiculo["hora_entrada"], datetime.datetime) else vehiculo["hora_entrada"]
            if vehiculo["hora_salida"]:
                vehiculo["hora_salida"] = vehiculo["hora_salida"].isoformat()
        
        with open("parqueo_datos.json", "w") as f:
            json.dump(datos, f, indent=2)
    
    def cargar_datos(self):
        """Cargar datos desde archivo JSON"""
        try:
            with open("parqueo_datos.json", "r") as f:
                datos = json.load(f)
            
            # Cargar vehículos activos
            for k, v in datos.get("vehiculos_activos", {}).items():
                v["hora_entrada"] = datetime.datetime.fromisoformat(v["hora_entrada"])
                if v["hora_salida"]:
                    v["hora_salida"] = datetime.datetime.fromisoformat(v["hora_salida"])
                self.vehiculos_activos[k] = Vehiculo(**v)
            
            # Cargar historial
            for v in datos.get("historial_vehiculos", []):
                v["hora_entrada"] = datetime.datetime.fromisoformat(v["hora_entrada"])
                if v["hora_salida"]:
                    v["hora_salida"] = datetime.datetime.fromisoformat(v["hora_salida"])
                self.historial_vehiculos.append(Vehiculo(**v))
            
            self.espacios_ocupados = datos.get("espacios_ocupados", {"parqueo1": 0, "parqueo2": 0})
            self.leds_estado = datos.get("leds_estado", {"parqueo1": [False] * ESPACIOS_TOTALES, "parqueo2": [False] * ESPACIOS_TOTALES})
            
        except FileNotFoundError:
            print("No se encontró archivo de datos, iniciando con datos vacíos")
        except Exception as e:
            print(f"Error cargando datos: {e}")

class ParqueoGUI:
    """Interfaz gráfica para el sistema de parqueos"""
    
    def __init__(self):
        self.manager = ParqueoManager()
        self.root = tk.Tk()
        self.root.title("Sistema de Administración de Parqueos")
        self.root.geometry("1200x800")
        
        # Mostrar ventana de conexión primero
        if not self.mostrar_ventana_conexion():
            return  # Si no se conecta, salir
        
        self.crear_interfaz()
        self.actualizar_display()
        
        # Actualizar cada segundo
        self.root.after(1000, self.actualizar_periodico)
    
    def mostrar_ventana_conexion(self):
        """Mostrar ventana de configuración y conexión de Raspberry Pi"""
        ventana_conexion = tk.Toplevel(self.root)
        ventana_conexion.title("Conexión a Raspberry Pi")
        ventana_conexion.geometry("600x500")
        ventana_conexion.transient(self.root)
        ventana_conexion.grab_set()
        
        # Centrar ventana
        ventana_conexion.update_idletasks()
        x = (ventana_conexion.winfo_screenwidth() // 2) - (600 // 2)
        y = (ventana_conexion.winfo_screenheight() // 2) - (500 // 2)
        ventana_conexion.geometry(f"600x500+{x}+{y}")
        
        # Título principal
        tk.Label(ventana_conexion, text="SISTEMA DE PARQUEOS INTELIGENTE", 
                font=("Arial", 16, "bold"), fg="blue").pack(pady=20)
        
        tk.Label(ventana_conexion, text="Configuración de Raspberry Pi", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Frame para configuración
        frame_config = tk.LabelFrame(ventana_conexion, text="Configuración de IPs", font=("Arial", 10, "bold"))
        frame_config.pack(fill=tk.X, padx=20, pady=10)
        
        # Configuración Parqueo 1
        tk.Label(frame_config, text="Parqueo 1 (Puerto 1718):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_ip1 = tk.Entry(frame_config, width=20)
        self.entry_ip1.insert(0, RASPBERRY_IP_1)
        self.entry_ip1.grid(row=0, column=1, padx=10, pady=5)
        
        # Configuración Parqueo 2
        tk.Label(frame_config, text="Parqueo 2 (Puerto 1719):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.entry_ip2 = tk.Entry(frame_config, width=20)
        self.entry_ip2.insert(0, RASPBERRY_IP_2)
        self.entry_ip2.grid(row=1, column=1, padx=10, pady=5)
        
        # Frame para estado de conexión
        frame_estado = tk.LabelFrame(ventana_conexion, text="Estado de Conexión", font=("Arial", 10, "bold"))
        frame_estado.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Labels de estado
        self.label_estado1 = tk.Label(frame_estado, text="Parqueo 1: Desconectado", 
                                     font=("Arial", 10), fg="red")
        self.label_estado1.pack(pady=5)
        
        self.label_estado2 = tk.Label(frame_estado, text="Parqueo 2: Desconectado", 
                                     font=("Arial", 10), fg="red")
        self.label_estado2.pack(pady=5)
        
        # Text widget para logs
        self.text_logs = tk.Text(frame_estado, height=8, width=60)
        self.text_logs.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(self.text_logs)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_logs.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_logs.yview)
        
        # Frame para botones
        frame_botones = tk.Frame(ventana_conexion)
        frame_botones.pack(fill=tk.X, padx=20, pady=10)
        
        # Botones
        tk.Button(frame_botones, text="Probar Conexiones", command=lambda: self.probar_conexiones(ventana_conexion),
                 bg="orange", fg="white", font=("Arial", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        
        self.btn_conectar = tk.Button(frame_botones, text="Iniciar Sistema", command=lambda: self.iniciar_sistema(ventana_conexion),
                                     bg="gray", fg="white", font=("Arial", 10, "bold"), width=15, state="disabled")
        self.btn_conectar.pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_botones, text="Cancelar", command=lambda: self.cancelar_conexion(ventana_conexion),
                 bg="red", fg="white", font=("Arial", 10, "bold"), width=15).pack(side=tk.RIGHT, padx=5)
        
        # Variable para controlar el resultado
        self.conexion_exitosa = False
        
        # Probar conexiones automáticamente al abrir
        ventana_conexion.after(500, lambda: self.probar_conexiones(ventana_conexion))
        # Verificar cada 3 segundos mientras la ventana esté abierta
        def verificacion_periodica():
            if ventana_conexion.winfo_exists():
                self.probar_conexiones(ventana_conexion)
                ventana_conexion.after(3000, verificacion_periodica)
        ventana_conexion.after(3000, verificacion_periodica)
        
        # Esperar hasta que se cierre la ventana
        self.root.wait_window(ventana_conexion)
        
        return self.conexion_exitosa
    
    def log_mensaje(self, mensaje):
        """Agregar mensaje al log de la ventana de conexión"""
        if hasattr(self, 'text_logs'):
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.text_logs.insert(tk.END, f"[{timestamp}] {mensaje}\n")
            self.text_logs.see(tk.END)
    
    def probar_conexiones(self, ventana):
        """Probar conexiones a ambas Raspberry Pi"""
        self.log_mensaje("Iniciando pruebas de conexión...")
        
        # Actualizar IPs desde los campos de entrada
        self.manager.ips_raspberry["parqueo1"] = self.entry_ip1.get().strip()
        self.manager.ips_raspberry["parqueo2"] = self.entry_ip2.get().strip()
        
        # Probar conexión Parqueo 1
        self.log_mensaje(f"Probando conexión con Parqueo 1 ({self.manager.ips_raspberry['parqueo1']}:{RASPBERRY_PORT_1})...")
        exito1, mensaje1 = self.manager.verificar_conexion_raspberry(1)
        
        if exito1:
            self.label_estado1.config(text="Parqueo 1: Conectado", fg="green")
            self.log_mensaje(f"EXITO: {mensaje1}")
        else:
            self.label_estado1.config(text="Parqueo 1: Error", fg="red")
            self.log_mensaje(f"ERROR: {mensaje1}")
        
        # Probar conexión Parqueo 2
        self.log_mensaje(f"Probando conexión con Parqueo 2 ({self.manager.ips_raspberry['parqueo2']}:{RASPBERRY_PORT_2})...")
        exito2, mensaje2 = self.manager.verificar_conexion_raspberry(2)
        
        if exito2:
            self.label_estado2.config(text="Parqueo 2: Conectado", fg="green")
            self.log_mensaje(f"EXITO: {mensaje2}")
        else:
            self.label_estado2.config(text="Parqueo 2: Error", fg="red")
            self.log_mensaje(f"ERROR: {mensaje2}")
        
        # Habilitar botón si al menos una está conectada
        if exito1 or exito2:
            if exito1 and exito2:
                self.btn_conectar.config(state="normal", bg="green")
                self.log_mensaje("Todas las conexiones exitosas. Sistema completo listo para iniciar.")
            else:
                self.btn_conectar.config(state="normal", bg="orange")
                parqueo_conectado = "Parqueo 1" if exito1 else "Parqueo 2"
                self.log_mensaje(f"ADVERTENCIA: Solo {parqueo_conectado} conectado. Sistema iniciará con funcionalidad limitada.")
        else:
            self.btn_conectar.config(state="disabled", bg="gray")
            self.log_mensaje("Error: Se requiere al menos una Raspberry Pi conectada para continuar.")
    
    def iniciar_sistema(self, ventana):
        """Iniciar el sistema principal"""
        if any(self.manager.conexiones_raspberry.values()):
            parqueos_conectados = [k for k, v in self.manager.conexiones_raspberry.items() if v]
            if len(parqueos_conectados) == 2:
                self.log_mensaje("Iniciando sistema completo con ambos parqueos...")
            else:
                parqueo_activo = parqueos_conectados[0]
                self.log_mensaje(f"Iniciando sistema con {parqueo_activo} únicamente...")
                messagebox.showwarning("Sistema Limitado", 
                    f"Solo {parqueo_activo} está conectado.\nAlgunas funciones estarán deshabilitadas.")
            
            self.conexion_exitosa = True
            ventana.destroy()
        else:
            messagebox.showerror("Error", "Se requiere al menos una Raspberry Pi conectada")
    
    def cancelar_conexion(self, ventana):
        """Cancelar y cerrar la aplicación"""
        self.conexion_exitosa = False
        ventana.destroy()
        self.root.quit()
    
    def crear_interfaz(self):
        """Crear la interfaz gráfica"""
        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña 1: Control Principal
        self.frame_principal = ttk.Frame(notebook)
        notebook.add(self.frame_principal, text="Control Principal")
        self.crear_panel_principal()
        
        # Pestaña 2: Control de LEDs
        self.frame_leds = ttk.Frame(notebook)
        notebook.add(self.frame_leds, text="Control de LEDs")
        self.crear_panel_leds()
        
        # Pestaña 3: Estadísticas
        self.frame_stats = ttk.Frame(notebook)
        notebook.add(self.frame_stats, text="Estadísticas")
        self.crear_panel_estadisticas()
        
        # Verificación inicial de conexiones después de crear la interfaz
        self.root.after(1000, self.verificar_conexiones_silencioso)
    
    def crear_panel_principal(self):
        """Crear panel principal de control"""
        # Frame superior - Información en tiempo real
        frame_info = ttk.LabelFrame(self.frame_principal, text="Estado en Tiempo Real")
        frame_info.pack(fill=tk.X, padx=10, pady=5)
        
        # Espacios disponibles
        tk.Label(frame_info, text="ESPACIOS DISPONIBLES", font=("Arial", 14, "bold")).pack(pady=5)
        
        frame_espacios = tk.Frame(frame_info)
        frame_espacios.pack(pady=5)
        
        tk.Label(frame_espacios, text="Parqueo 1:", font=("Arial", 12)).grid(row=0, column=0, padx=10)
        self.label_espacios1 = tk.Label(frame_espacios, text="2/2", font=("Arial", 16, "bold"), fg="green")
        self.label_espacios1.grid(row=0, column=1, padx=10)
        
        # Indicador de conexión P1
        self.label_conexion1 = tk.Label(frame_espacios, text="●", font=("Arial", 20), fg="red")
        self.label_conexion1.grid(row=0, column=1, padx=10, sticky="e")
        
        tk.Label(frame_espacios, text="Parqueo 2:", font=("Arial", 12)).grid(row=0, column=2, padx=10)
        self.label_espacios2 = tk.Label(frame_espacios, text="2/2", font=("Arial", 16, "bold"), fg="green")
        self.label_espacios2.grid(row=0, column=3, padx=10)
        
        # Indicador de conexión P2
        self.label_conexion2 = tk.Label(frame_espacios, text="●", font=("Arial", 20), fg="red")
        self.label_conexion2.grid(row=0, column=3, padx=10, sticky="e")
        
        # Control de barrera
        frame_barrera = ttk.LabelFrame(self.frame_principal, text="Control de Barreras")
        frame_barrera.pack(fill=tk.X, padx=10, pady=5)
        
        # Parqueo 1
        tk.Label(frame_barrera, text="PARQUEO 1", font=("Arial", 11, "bold")).pack(pady=5)
        frame_botones_p1 = tk.Frame(frame_barrera)
        frame_botones_p1.pack(pady=5)
        
        self.btn_abrir_p1 = tk.Button(frame_botones_p1, text="ABRIR PASO P1", command=lambda: self.controlar_barrera("ABRIR_PASO", 1),
                 bg="green", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_abrir_p1.pack(side=tk.LEFT, padx=3)
        
        self.btn_subir_p1 = tk.Button(frame_botones_p1, text="SUBIR P1", command=lambda: self.controlar_barrera("SUBIR", 1),
                 bg="blue", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_subir_p1.pack(side=tk.LEFT, padx=3)
        
        self.btn_bajar_p1 = tk.Button(frame_botones_p1, text="BAJAR P1", command=lambda: self.controlar_barrera("BAJAR", 1),
                 bg="red", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_bajar_p1.pack(side=tk.LEFT, padx=3)
        
        # Parqueo 2
        tk.Label(frame_barrera, text="PARQUEO 2", font=("Arial", 11, "bold")).pack(pady=(15,5))
        frame_botones_p2 = tk.Frame(frame_barrera)
        frame_botones_p2.pack(pady=5)
        
        self.btn_abrir_p2 = tk.Button(frame_botones_p2, text="ABRIR PASO P2", command=lambda: self.controlar_barrera("ABRIR_PASO", 2),
                 bg="green", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_abrir_p2.pack(side=tk.LEFT, padx=3)
        
        self.btn_subir_p2 = tk.Button(frame_botones_p2, text="SUBIR P2", command=lambda: self.controlar_barrera("SUBIR", 2),
                 bg="blue", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_subir_p2.pack(side=tk.LEFT, padx=3)
        
        self.btn_bajar_p2 = tk.Button(frame_botones_p2, text="BAJAR P2", command=lambda: self.controlar_barrera("BAJAR", 2),
                 bg="red", fg="white", font=("Arial", 10, "bold"), width=12)
        self.btn_bajar_p2.pack(side=tk.LEFT, padx=3)
        
        # Control de vehículos
        frame_vehiculos = ttk.LabelFrame(self.frame_principal, text="Registro de Vehículos")
        frame_vehiculos.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Entrada de vehículos
        frame_entrada = tk.Frame(frame_vehiculos)
        frame_entrada.pack(pady=10)
        
        tk.Label(frame_entrada, text="ID Vehículo:").grid(row=0, column=0, padx=5)
        self.entry_vehiculo_id = tk.Entry(frame_entrada, width=15)
        self.entry_vehiculo_id.grid(row=0, column=1, padx=5)
        
        tk.Label(frame_entrada, text="Parqueo:").grid(row=0, column=2, padx=5)
        self.combo_parqueo = ttk.Combobox(frame_entrada, values=["1", "2"], width=10, state="readonly")
        self.combo_parqueo.grid(row=0, column=3, padx=5)
        self.combo_parqueo.set("1")
        
        tk.Button(frame_entrada, text="REGISTRAR ENTRADA", command=self.registrar_entrada,
                 bg="green", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=10)
        tk.Button(frame_entrada, text="REGISTRAR SALIDA", command=self.registrar_salida,
                 bg="orange", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=5, padx=5)
        
        # Lista de vehículos activos
        tk.Label(frame_vehiculos, text="Vehículos Activos:", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=10, pady=(10,0))
        
        self.tree_vehiculos = ttk.Treeview(frame_vehiculos, columns=("ID", "Parqueo", "Entrada", "Tiempo"), show="headings", height=8)
        self.tree_vehiculos.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree_vehiculos.heading("ID", text="ID Vehículo")
        self.tree_vehiculos.heading("Parqueo", text="Parqueo")
        self.tree_vehiculos.heading("Entrada", text="Hora Entrada")
        self.tree_vehiculos.heading("Tiempo", text="Tiempo Transcurrido")
        
        self.tree_vehiculos.column("ID", width=100)
        self.tree_vehiculos.column("Parqueo", width=80)
        self.tree_vehiculos.column("Entrada", width=150)
        self.tree_vehiculos.column("Tiempo", width=150)
    
    def crear_panel_leds(self):
        """Crear panel de control de LEDs"""
        tk.Label(self.frame_leds, text="Control de LEDs por Espacio", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Parqueo 1
        frame_p1 = ttk.LabelFrame(self.frame_leds, text="Parqueo 1")
        frame_p1.pack(fill=tk.X, padx=20, pady=10)
        
        self.botones_leds1 = []
        frame_botones1 = tk.Frame(frame_p1)
        frame_botones1.pack(pady=10)
        
        for i in range(ESPACIOS_TOTALES):
            btn = tk.Button(frame_botones1, text=f"Espacio {i+1}", width=12, height=2,
                           command=lambda x=i: self.toggle_led(1, x))
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)
            self.botones_leds1.append(btn)
        
        # Parqueo 2
        frame_p2 = ttk.LabelFrame(self.frame_leds, text="Parqueo 2")
        frame_p2.pack(fill=tk.X, padx=20, pady=10)
        
        self.botones_leds2 = []
        frame_botones2 = tk.Frame(frame_p2)
        frame_botones2.pack(pady=10)
        
        for i in range(ESPACIOS_TOTALES):
            btn = tk.Button(frame_botones2, text=f"Espacio {i+1}", width=12, height=2,
                           command=lambda x=i: self.toggle_led(2, x))
            btn.grid(row=i//5, column=i%5, padx=5, pady=5)
            self.botones_leds2.append(btn)
    
    def crear_panel_estadisticas(self):
        """Crear panel de estadísticas"""
        tk.Label(self.frame_stats, text="Estadísticas Históricas", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Frame para estadísticas
        self.frame_stats_content = tk.Frame(self.frame_stats)
        self.frame_stats_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Button(self.frame_stats, text="ACTUALIZAR ESTADÍSTICAS", command=self.actualizar_estadisticas,
                 bg="blue", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
    
    def actualizar_display(self):
        """Actualizar información en pantalla"""
        # Actualizar espacios disponibles
        espacios_disp1 = ESPACIOS_TOTALES - self.manager.espacios_ocupados["parqueo1"]
        espacios_disp2 = ESPACIOS_TOTALES - self.manager.espacios_ocupados["parqueo2"]
        
        self.label_espacios1.config(text=f"{espacios_disp1}/{ESPACIOS_TOTALES}")
        self.label_espacios2.config(text=f"{espacios_disp2}/{ESPACIOS_TOTALES}")
        
        # Cambiar color según disponibilidad
        color1 = "green" if espacios_disp1 > 1 else "orange" if espacios_disp1 > 0 else "red"
        color2 = "green" if espacios_disp2 > 1 else "orange" if espacios_disp2 > 0 else "red"
        
        self.label_espacios1.config(fg=color1)
        self.label_espacios2.config(fg=color2)
        
        # Actualizar indicadores de conexión
        conexion1 = self.manager.conexiones_raspberry.get("parqueo1", False)
        conexion2 = self.manager.conexiones_raspberry.get("parqueo2", False)
        
        self.label_conexion1.config(fg="green" if conexion1 else "red")
        self.label_conexion2.config(fg="green" if conexion2 else "red")
        
        # Actualizar tooltips/textos de ayuda
        tooltip1 = "Conectado" if conexion1 else "Desconectado"
        tooltip2 = "Conectado" if conexion2 else "Desconectado"
        
        # Actualizar estado de botones de control según conexión
        if hasattr(self, 'btn_abrir_p1'):
            estado1 = tk.NORMAL if conexion1 else tk.DISABLED
            estado2 = tk.NORMAL if conexion2 else tk.DISABLED
            
            # Botones Parqueo 1
            self.btn_abrir_p1.config(state=estado1)
            self.btn_subir_p1.config(state=estado1)
            self.btn_bajar_p1.config(state=estado1)
            
            # Botones Parqueo 2
            self.btn_abrir_p2.config(state=estado2)
            self.btn_subir_p2.config(state=estado2)
            self.btn_bajar_p2.config(state=estado2)
        
        # Actualizar combo de parqueos para mostrar solo los disponibles
        if hasattr(self, 'combo_parqueo'):
            parqueos_disponibles = []
            if conexion1:
                parqueos_disponibles.append("1")
            if conexion2:
                parqueos_disponibles.append("2")
            
            if parqueos_disponibles:
                self.combo_parqueo.config(values=parqueos_disponibles)
                if self.combo_parqueo.get() not in parqueos_disponibles:
                    self.combo_parqueo.set(parqueos_disponibles[0])
            else:
                self.combo_parqueo.config(values=["Sin conexión"])
        
        # Actualizar lista de vehículos activos
        for item in self.tree_vehiculos.get_children():
            self.tree_vehiculos.delete(item)
        
        for vehiculo_id, vehiculo in self.manager.vehiculos_activos.items():
            tiempo_transcurrido = datetime.datetime.now() - vehiculo.hora_entrada
            self.tree_vehiculos.insert("", "end", values=(
                vehiculo_id,
                vehiculo.parqueo,
                vehiculo.hora_entrada.strftime("%H:%M:%S"),
                str(tiempo_transcurrido).split(".")[0]
            ))
        
        # Actualizar botones de LEDs
        for i, btn in enumerate(self.botones_leds1):
            color = "red" if self.manager.leds_estado["parqueo1"][i] else "lightgray"
            btn.config(bg=color)
        
        for i, btn in enumerate(self.botones_leds2):
            color = "red" if self.manager.leds_estado["parqueo2"][i] else "lightgray"
            btn.config(bg=color)
    
    def actualizar_periodico(self):
        """Actualización periódica de la interfaz"""
        self.actualizar_display()
        
        # Verificar conexiones cada 5 segundos
        if hasattr(self, '_contador_verificacion'):
            self._contador_verificacion += 1
        else:
            self._contador_verificacion = 0
            
        if self._contador_verificacion >= 5:  # 5 segundos
            self._contador_verificacion = 0
            self.verificar_conexiones_silencioso()
        
        self.root.after(1000, self.actualizar_periodico)
    
    def verificar_conexiones_silencioso(self):
        """Verificar conexiones sin mostrar mensajes (para uso periódico)"""
        try:
            conexiones_previas = dict(self.manager.conexiones_raspberry)
            
            # Verificar ambas conexiones de forma rápida
            for parqueo in [1, 2]:
                parqueo_key = f"parqueo{parqueo}"
                ip = self.manager.ips_raspberry[parqueo_key]
                puerto = self.manager.puertos_raspberry[parqueo_key]
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)  # Timeout corto para verificación rápida
                        s.connect((ip, puerto))
                        s.send("ESTADO".encode('utf-8'))
                        response = s.recv(1024).decode('utf-8')
                        if "ESTADO_OK" in response or "OK" in response:
                            self.manager.conexiones_raspberry[parqueo_key] = True
                        else:
                            self.manager.conexiones_raspberry[parqueo_key] = False
                except:
                    self.manager.conexiones_raspberry[parqueo_key] = False
            
            # Actualizar indicadores visuales si hay cambios
            if conexiones_previas != self.manager.conexiones_raspberry:
                self.actualizar_indicadores_conexion()
                
        except Exception as e:
            print(f"Error en verificación periódica: {e}")
    
    def actualizar_indicadores_conexion(self):
        """Actualizar los indicadores visuales de conexión en la interfaz principal"""
        if hasattr(self, 'label_conexion1') and hasattr(self, 'label_conexion2'):
            # Actualizar indicador Parqueo 1
            color1 = "green" if self.manager.conexiones_raspberry.get("parqueo1", False) else "red"
            self.label_conexion1.config(fg=color1)
            
            # Actualizar indicador Parqueo 2  
            color2 = "green" if self.manager.conexiones_raspberry.get("parqueo2", False) else "red"
            self.label_conexion2.config(fg=color2)
            
            # Habilitar/deshabilitar botones según conexión
            estado1 = "normal" if self.manager.conexiones_raspberry.get("parqueo1", False) else "disabled"
            estado2 = "normal" if self.manager.conexiones_raspberry.get("parqueo2", False) else "disabled"
            
            if hasattr(self, 'btn_abrir_p1'):
                self.btn_abrir_p1.config(state=estado1)
                self.btn_subir_p1.config(state=estado1)
                self.btn_bajar_p1.config(state=estado1)
                
            if hasattr(self, 'btn_abrir_p2'):
                self.btn_abrir_p2.config(state=estado2)
                self.btn_subir_p2.config(state=estado2)  
                self.btn_bajar_p2.config(state=estado2)
            
            # Actualizar combo de parqueos disponibles
            parqueos_disponibles = []
            if self.manager.conexiones_raspberry.get("parqueo1", False):
                parqueos_disponibles.append("1")
            if self.manager.conexiones_raspberry.get("parqueo2", False):
                parqueos_disponibles.append("2")
            
            if hasattr(self, 'combo_parqueo') and parqueos_disponibles:
                valor_actual = self.combo_parqueo.get()
                self.combo_parqueo['values'] = parqueos_disponibles
                # Mantener selección si sigue disponible, sino seleccionar el primero disponible
                if valor_actual not in parqueos_disponibles:
                    self.combo_parqueo.set(parqueos_disponibles[0])
                    
            print(f"Indicadores actualizados - P1: {color1}, P2: {color2}")
    
    def registrar_entrada(self):
        """Registrar entrada de vehículo"""
        vehiculo_id = self.entry_vehiculo_id.get().strip()
        if not vehiculo_id:
            messagebox.showerror("Error", "Ingrese un ID de vehículo")
            return
        
        parqueo = int(self.combo_parqueo.get())
        parqueo_key = f"parqueo{parqueo}"
        
        # Verificar si el parqueo seleccionado está conectado
        if not self.manager.conexiones_raspberry.get(parqueo_key, False):
            messagebox.showerror("Error", f"Parqueo {parqueo} no está conectado. Seleccione un parqueo disponible.")
            return
        
        exito, mensaje = self.manager.registrar_entrada(vehiculo_id, parqueo)
        
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self.entry_vehiculo_id.delete(0, tk.END)
        else:
            messagebox.showerror("Error", mensaje)
    
    def registrar_salida(self):
        """Registrar salida de vehículo"""
        vehiculo_id = self.entry_vehiculo_id.get().strip()
        if not vehiculo_id:
            messagebox.showerror("Error", "Ingrese un ID de vehículo")
            return
        
        exito, mensaje, costo = self.manager.registrar_salida(vehiculo_id)
        
        if exito:
            costo_dolares = costo / self.manager.tipo_cambio_usd
            mensaje_completo = f"{mensaje}\n\nCosto a pagar:\n₡{costo:,.0f} colones\n${costo_dolares:.2f} dólares"
            messagebox.showinfo("Facturación", mensaje_completo)
            self.entry_vehiculo_id.delete(0, tk.END)
        else:
            messagebox.showerror("Error", mensaje)
    
    def controlar_barrera(self, accion, parqueo=1):
        """Controlar la barrera remotamente"""
        parqueo_key = f"parqueo{parqueo}"
        
        # Verificar si el parqueo está conectado
        if not self.manager.conexiones_raspberry.get(parqueo_key, False):
            messagebox.showerror("Error", f"Parqueo {parqueo} no está conectado. No se puede ejecutar el comando.")
            return
        
        exito, respuesta = self.manager.controlar_barrera(accion, parqueo)
        
        if exito:
            messagebox.showinfo("Barrera", f"Parqueo {parqueo} - Comando enviado: {accion}\nRespuesta: {respuesta}")
        else:
            messagebox.showerror("Error de Conexión", respuesta)
    
    def toggle_led(self, parqueo, espacio):
        """Cambiar estado de LED"""
        parqueo_key = f"parqueo{parqueo}"
        
        # Verificar si el parqueo está conectado
        if not self.manager.conexiones_raspberry.get(parqueo_key, False):
            messagebox.showerror("Error", f"Parqueo {parqueo} no está conectado. No se puede controlar el LED.")
            return
        
        if self.manager.toggle_led(parqueo, espacio):
            estado = "OCUPADO" if self.manager.leds_estado[f"parqueo{parqueo}"][espacio] else "LIBRE"
            messagebox.showinfo("LED Control", f"Parqueo {parqueo}, Espacio {espacio+1}: {estado}")
    
    def actualizar_estadisticas(self):
        """Actualizar y mostrar estadísticas"""
        stats = self.manager.obtener_estadisticas()
        
        # Limpiar frame anterior
        for widget in self.frame_stats_content.winfo_children():
            widget.destroy()
        
        # Crear tabla de estadísticas
        headers = ["Métrica", "Parqueo 1", "Parqueo 2", "Total"]
        
        # Crear encabezados
        for col, header in enumerate(headers):
            tk.Label(self.frame_stats_content, text=header, font=("Arial", 12, "bold"), 
                    relief=tk.RIDGE, width=15).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
        
        # Datos de estadísticas
        filas = [
            ("Total Vehículos", stats["total_vehiculos"]["parqueo1"], stats["total_vehiculos"]["parqueo2"], stats["total_vehiculos"]["total"]),
            ("Ganancias (₡)", f"₡{stats['ganancias_colones']['parqueo1']:,.0f}", f"₡{stats['ganancias_colones']['parqueo2']:,.0f}", f"₡{stats['ganancias_colones']['total']:,.0f}"),
            ("Ganancias ($)", f"${stats['ganancias_dolares']['parqueo1']:.2f}", f"${stats['ganancias_dolares']['parqueo2']:.2f}", f"${stats['ganancias_dolares']['total']:.2f}")
        ]
        
        for row, datos in enumerate(filas, 1):
            for col, dato in enumerate(datos):
                tk.Label(self.frame_stats_content, text=str(dato), font=("Arial", 10),
                        relief=tk.RIDGE, width=15).grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
        
        # Configurar expansión de columnas
        for i in range(len(headers)):
            self.frame_stats_content.columnconfigure(i, weight=1)
    
    def run(self):
        """Ejecutar la aplicación"""
        if hasattr(self, 'conexion_exitosa') and self.conexion_exitosa:
            self.root.mainloop()
        else:
            print("Conexión cancelada o fallida. Cerrando aplicación.")
            self.root.quit()

if __name__ == "__main__":
    try:
        app = ParqueoGUI()
        app.run()
    except KeyboardInterrupt:
        print("\nAplicación cerrada por el usuario")
    except Exception as e:
        print(f"Error crítico: {e}")
        messagebox.showerror("Error", f"Error crítico en la aplicación: {e}")
