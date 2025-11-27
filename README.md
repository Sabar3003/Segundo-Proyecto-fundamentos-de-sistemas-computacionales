# Sistema de Parqueos Inteligente - Dual Raspberry Pi

## Descripción del Sistema

Este sistema divide el parqueo inteligente en **dos unidades independientes**, cada una controlada por una Raspberry Pi diferente, con una GUI centralizada que se conecta a ambas antes de permitir el acceso al sistema.

### Funcionalidades Principales

1. **Cálculo de Costo de Parqueo**
   - Tarifa: ₡1000 por cada 10 segundos
   - Registro automático de hora de entrada y salida
   - Conversión automática a dólares usando API de tipo de cambio

2. **Visualización en Tiempo Real**
   - Espacios disponibles por parqueo (2 espacios cada uno = 4 total)
   - Lista de vehículos activos
   - Tiempo transcurrido por vehículo

3. **Control Remoto de LEDs**
   - Control individual de cada espacio (2 por parqueo)
   - Actualización automática del contador de espacios
   - Interfaz visual intuitiva

4. **Control de Barrera**
   - Comandos: SUBIR, BAJAR, ABRIR_PASO
   - Comunicación con Raspberry Pi via socket
   - Secuencia automática para paso de vehículos

5. **Estadísticas Históricas**
   - Total de vehículos por parqueo
   - Ganancias en colones y dólares
   - Datos por parqueo individual y consolidados

## Instalación

### Requisitos
- Python 3.7 o superior
- Tkinter (incluido en Python)
- Requests (para API de tipo de cambio)

### Instalación de dependencias
```bash
pip install requests
```

## Configuración

### 1. Configurar IP de Raspberry Pi
Editar el archivo `config.json` o modificar directamente en `GUI.py`:
```python
RASPBERRY_IP = "192.168.1.XXX"  # IP de tu Raspberry Pi
RASPBERRY_PORT = 1718
```

### 2. Configurar Parámetros del Sistema
En `config.json` puedes modificar:
- Número de espacios por parqueo
- Tarifa por tiempo
- URLs de APIs

## Uso de la Aplicación

### 1. Ejecutar la Aplicación
```bash
python GUI.py
```

### 2. Pestañas Principales

#### **Control Principal**
- **Espacios Disponibles**: Muestra en tiempo real los espacios libres
- **Control de Barrera**: Botones para manejar la barrera de entrada
- **Registro de Vehículos**: Entrada y salida de vehículos con cálculo automático de costos

#### **Control de LEDs**
- **Parqueo 1 y 2**: Botones individuales para cada espacio
- **Estados**: Gris = Libre, Rojo = Ocupado
- **Actualización Automática**: El contador se actualiza al cambiar estados

#### **Estadísticas**
- **Métricas Históricas**: Total de vehículos y ganancias
- **Conversión Automática**: Colones y dólares
- **Datos Segregados**: Por parqueo individual y totales

### 3. Flujo de Trabajo Típico

1. **Llegada de Vehículo**:
   - Ingresar ID del vehículo
   - Seleccionar parqueo (1 o 2)
   - Clic en "REGISTRAR ENTRADA"
   - Usar "ABRIR_PASO" para levantar barrera

2. **Salida de Vehículo**:
   - Ingresar ID del vehículo
   - Clic en "REGISTRAR SALIDA"
   - Sistema calcula automáticamente el costo
   - Usar "ABRIR_PASO" para permitir salida

3. **Control Manual**:
   - Usar botones de LEDs para simular ocupación
   - Control manual de barrera con SUBIR/BAJAR

## Modos de Operación del Sistema

### **Modo Completo** (Ambas Raspberry Pi Conectadas)
- Funcionalidad completa de ambos parqueos
- Todos los controles habilitados
- Estadísticas completas
- Redundancia total del sistema

### **Modo Limitado** (Solo una Raspberry Pi Conectada)
- Funcionalidad del parqueo conectado únicamente
- Controles deshabilitados para el parqueo desconectado
- Indicadores visuales muestran estado de conexión
- Sistema permite operar con funcionalidad reducida

### **Sin Servicio** (Ninguna Raspberry Pi Conectada)
- Sistema no permite iniciar la interfaz
- Se requiere al menos una conexión para continuar

### Indicadores Visuales de Conexión
- **Círculo Verde**: Parqueo conectado y operativo
- **Círculo Rojo**: Parqueo desconectado o no disponible
- **Botones Deshabilitados**: Controles no disponibles para parqueos desconectados
- **Combo de Parqueos**: Solo muestra parqueos disponibles

## Características Técnicas

### Cálculo de Costos
- **Fórmula**: `ceil(tiempo_segundos / 10) * 1000`
- **Mínimo**: ₡1000 (aunque sea menos de 10 segundos)
- **Ejemplo**: 25 segundos = 3 bloques = ₡3000

### Comunicación con Hardware
- **Protocolo**: TCP Socket
- **Puerto**: 1718
- **Comandos**: "SUBIR", "BAJAR", "ABRIR_PASO"
- **Timeout**: 5 segundos

### Persistencia de Datos
- **Archivo**: `parqueo_datos.json`
- **Contenido**: Vehículos activos, historial, estados de LEDs
- **Backup Automático**: Cada cambio se guarda automáticamente

### API Externa
- **Tipo de Cambio**: exchangerate-api.com
- **Fallback**: ₡520 por $1 USD
- **Actualización**: Al iniciar la aplicación

## Solución de Problemas

### Error de Conexión con Raspberry Pi
1. Verificar que la Raspberry Pi esté encendida
2. Confirmar la IP en la red local
3. Verificar que el puerto 1718 esté abierto
4. Probar conexión manual: `telnet IP_RASPBERRY 1718`

### Datos No Se Guardan
1. Verificar permisos de escritura en el directorio
2. Comprobar espacio en disco
3. Revisar que no haya otro proceso usando el archivo

### API de Tipo de Cambio No Funciona
- La aplicación usa un valor por defecto
- Verificar conexión a internet
- Revisar firewall/proxy

## Personalización

### Modificar Tarifas
En `GUI.py`, línea:
```python
TARIFA_POR_10_SEGUNDOS = 1000  # Cambiar valor
```

### Cambiar Número de Espacios
```python
ESPACIOS_TOTALES = 10  # Modificar según necesidad
```

### Agregar Nuevos Comandos de Barrera
En el método `controlar_barrera()`, agregar nuevos casos.

## Archivos del Sistema

- `GUI.py`: Aplicación principal
- `servomotor.py`: Código para Raspberry Pi
- `config.json`: Configuración del sistema
- `parqueo_datos.json`: Datos persistentes (creado automáticamente)
- `requirements.txt`: Dependencias de Python

## Soporte

Para problemas técnicos:
1. Revisar logs en la consola
2. Verificar archivo `parqueo_datos.json` para corrupción
3. Reiniciar la aplicación
4. Verificar conexión de red con Raspberry Pi