# PRUEBAS UNITARIAS PARA EL SISTEMA IoT

import pytest
from sgd import *
import numpy as np

# 1. Comprobamos que solo podemos obtener una única instancia del sistema
def test_unica_instancia():
    singleton_sis1 = Singleton_Sis_IoT.obtener_instancia()
    singleton_sis2 = Singleton_Sis_IoT.obtener_instancia()
    assert singleton_sis1 is singleton_sis2

# 2. Comprobamos que los datos enviados por el sensor son los que recibe el operador
def test_publicacion_datos_sensor():
    sensor = PublicadorDatosSensor("Sensor")
    operador = Operator("Operador")

    sensor.register_observer(operador)

    datos_enviados = [(1620095103, 25), (1620095108, 27), (1620095113, 28)]

    for registro in datos_enviados:
        sensor.set_value(registro)

    datos_recibidos = list(operador.cola.queue)

    assert datos_enviados == datos_recibidos

# 3. Comprobamos que los estadísticos se calculan correctamente
def test_manejador_temperaturas_estadisticos():
    temperaturas = [33, 26, 42, 21, 16, 8, 10, 11]

    # Cálculos usando los algoritmos del programa (funciones de segundo orden)

    manejador_te= ManejadorTempEstadisticos()
    manejador_lt= ManejadorLimTemp(succesor=manejador_te)
    manejador_at= ManejadorAumentoTemp(succesor=manejador_lt)

    request1 = Request("TempEstadisticos")
    request2 = Request("LimTemp")
    request3 = Request("AumentoTemp")

    media, dt, q1, q2, q3, maximo, minimo = manejador_at.manejarTemperaturas(request1, temperaturas)

    # Cálculos estadísticos usando numpy
    media_real = np.average(temperaturas); dt_real = np.std(temperaturas)
    q1_real = np.quantile(temperaturas, 0.25, method='averaged_inverted_cdf') # Elegimos el método que se corresponde con
    q2_real = np.quantile(temperaturas, 0.5, method='averaged_inverted_cdf')  # con la forma en la que hemos calculado
    q3_real = np.quantile(temperaturas, 0.75, method='averaged_inverted_cdf') # los cuantiles

    max_real = np.max(temperaturas)
    min_real = np.min(temperaturas)

    # Comprobación de los resultados
    assert round(media, 2) == round(media_real, 2)
    assert round(dt, 2) == round(dt_real, 2)
    assert round(q1, 2) == round(q1_real, 2)
    assert round(q2, 2) == round(q2_real, 2)
    assert round(q3, 2) == round(q3_real, 2)
    assert maximo == max_real
    assert minimo == min_real

# 4. Probamos si dectecta cuando supera el umbral
def test_limite_temperaturas():
    temperaturas = [33, 26, 42, 21, 16, 8, 10, 11]

    # Cálculos usando los algoritmos del programa (funciones de segundo orden)

    manejador_te= ManejadorTempEstadisticos()
    manejador_lt= ManejadorLimTemp(succesor=manejador_te)
    manejador_at= ManejadorAumentoTemp(succesor=manejador_lt)

    request1 = Request("TempEstadisticos")
    request2 = Request("LimTemp")
    request3 = Request("AumentoTemp")

    superaUmbral = manejador_at.manejarTemperaturas(request2, temperaturas)

    assert superaUmbral == (temperaturas[-1] > 31) # 31 es el umbral fijado por la clase

# 5. Probamos si detecta cuando aumenta significativamente la temperatura
def test_aumento_temperaturas():
    temperaturas = [33, 26, 42, 21, 16, 8, 10, 11]

    # Cálculos usando los algoritmos del programa (funciones de segundo orden)

    manejador_te= ManejadorTempEstadisticos()
    manejador_lt= ManejadorLimTemp(succesor=manejador_te)
    manejador_at= ManejadorAumentoTemp(succesor=manejador_lt)

    request1 = Request("TempEstadisticos")
    request2 = Request("LimTemp")
    request3 = Request("AumentoTemp")

    superaUmbral = manejador_at.manejarTemperaturas(request3, temperaturas)

    # Lo que debería salir
    datos_30s = temperaturas[2:]
    maximo = max(datos_30s); minimo = min(datos_30s)

    assert superaUmbral == (maximo - minimo > 10) # 31 es el umbral fijado por la clase
