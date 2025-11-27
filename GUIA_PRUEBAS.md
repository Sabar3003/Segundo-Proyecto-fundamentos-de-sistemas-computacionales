# Guía de Pruebas - Sistema de Parqueos Dual

## Cómo Probar el Sistema

### Opción 1: Prueba con Simuladores (Recomendado para desarrollo)

1. **Ejecutar simuladores de Raspberry Pi:**
   ```bash
   python test_mock_raspberry.py
   ```
   - Esto inicia dos servidores simulados en puertos 1718 y 1719
   - Simula ambas Raspberry Pi funcionando correctamente

2. **Ejecutar GUI:**
   ```bash
   python GUI.py
   ```
   - En la ventana de conexión, usar `localhost` para ambas IPs
   - Parqueo 1: `localhost` (puerto 1718)
   - Parqueo 2: `localhost` (puerto 1719)

### Opción 2: Prueba con Raspberry Pi Reales

1. **Configurar y ejecutar en cada Raspberry Pi:**
   ```bash
   # En Raspberry Pi 1:
   python parqueo1_raspberry.py
   
   # En Raspberry Pi 2:
   python parqueo2_raspberry.py
   ```

2. **Verificar IPs mostradas:**
   - Ambas Raspberry Pi mostrarán su IP al conectarse a WiFi
   - Ejemplo de salida esperada:
     ```
     Parqueo 1 conectado a WiFi. IP: 192.168.1.100
     Parqueo 1 - Servidor remoto iniciado en 192.168.1.100:1718
     ```

3. **Ejecutar GUI:**
   ```bash
   python GUI.py
   ```
   - Usar las IPs reales mostradas por las Raspberry Pi

## Escenarios de Prueba

### Escenario 1: Ambas Raspberry Pi Conectadas (Modo Completo)
- Botón "Iniciar Sistema" habilitado en verde
- Todos los controles de barrera funcionan
- Indicadores de conexión en verde
- Ambos parqueos disponibles en combo
- Estadísticas completas

### Escenario 2: Solo una Raspberry Pi Conectada (Modo Limitado)
- Botón "Iniciar Sistema" habilitado en naranja
- Solo controles del parqueo conectado funcionan
- Un indicador verde y uno rojo
- Solo un parqueo disponible en combo
- Mensaje de advertencia al iniciar

### Escenario 3: Ninguna Raspberry Pi Conectada
- Botón "Iniciar Sistema" deshabilitado
- Todos los indicadores en rojo
- Mensaje de error en logs

## Funciones a Probar

### Control de Barreras:
1. **ABRIR PASO**: Secuencia completa
2. **SUBIR**: Solo levantar barrera
3. **BAJAR**: Solo bajar barrera

### Registro de Vehículos:
1. Registrar entrada con parqueo disponible
2. Intentar usar parqueo desconectado (debe mostrar error)
3. Registrar salida y verificar cálculo de costo

### Control de LEDs:
1. Toggle LEDs en parqueo conectado
2. Intentar toggle en parqueo desconectado (debe mostrar error)

### Monitoreo en Tiempo Real:
1. Verificar actualización de indicadores de conexión
2. Verificar reconexión automática (detener/reiniciar simulador)

## Verificación de Errores

### Errores Esperados (Funcionamiento Correcto):
- "Parqueo X no está conectado" al intentar usar parqueo desconectado
- "Se requiere al menos una Raspberry Pi" si ninguna está disponible

### Errores No Esperados (Requieren Corrección):
- GUI se cuelga al perder conexión
- Botones habilitados para parqueos desconectados
- Indicadores no se actualizan

## Verificación de Logs

### En Simuladores (test_mock_raspberry.py):
```
Mock Parqueo 1 iniciado en puerto 1718
Parqueo 1: Conexión desde ('127.0.0.1', 12345)
Parqueo 1: Comando recibido: ESTADO
Parqueo 1: Respuesta enviada: ESTADO_OK_PARQUEO_1
```

### En Raspberry Pi Reales:
```
Parqueo 1 conectado a WiFi. IP: 192.168.1.100
Parqueo 1 - Servidor remoto iniciado en 192.168.1.100:1718
Parqueo 1 - Comando remoto recibido: ESTADO
```

### En GUI:
```
[15:30:45] Iniciando pruebas de conexión...
[15:30:45] Probando conexión con Parqueo 1 (localhost:1718)...
[15:30:45] EXITO: Parqueo 1 conectado en localhost:1718
[15:30:46] ADVERTENCIA: Solo Parqueo 1 conectado. Sistema iniciará con funcionalidad limitada.
```

## Lista de Verificación

- [ ] Simuladores inician correctamente
- [ ] GUI detecta conexiones automáticamente
- [ ] Indicadores visuales funcionan
- [ ] Controles se habilitan/deshabilitan correctamente
- [ ] Sistema permite operar con una sola Raspberry Pi
- [ ] Mensajes de error son claros y útiles
- [ ] Reconexión automática funciona
- [ ] Estadísticas se calculan correctamente

Sistema listo para producción una vez que todas las verificaciones pasen.