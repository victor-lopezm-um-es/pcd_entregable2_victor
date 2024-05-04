# Código Sistema de gestión de datos en un entorno IoT

from functools import reduce
from abc import ABC, abstractmethod
import asyncio
from queue import Queue
import random
import time
from datetime import datetime

# Patrón Strategy
class Context:
    def __init__(self, strategy=None):
        self._strategy = strategy

    def establecerEstrategia(self, strategy):
        self._strategy = strategy

    def hacerAlgo(self, data):
        return self._strategy.aplicarAlgoritmo(data)

class ComputoEstadistico: #Interfaz de Estrategia
    def aplicarAlgoritmo(self, data):
        pass
    
class Media_y_DesvTip(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        n = len(data)
        media = reduce(lambda x, y: x + y, data) / n

        varianza = reduce(lambda x, y: x + y,
                          map(lambda x: (1/n) * (x - media)**2, data ) )
        desv_tip = varianza ** (.5)

        return media, desv_tip

class Cuantiles(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        datos_ord = sorted(data)
        n = len(datos_ord)

        def cuartil(q):
            if n == 1:
                return datos_ord[0]

            indice = q * (n + 1) / 4

            if indice % 1 == 0:
                return datos_ord[int(indice) - 1]

            else: 
                if int(indice) == n and q == 3:
                    return datos_ord[-1]
                else:
                    return (datos_ord[int(indice) - 1] + datos_ord[int(indice)]) / 2

        return tuple(map(cuartil, [1, 2, 3]))


class Maximos_y_Minimos(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        maximo = reduce(lambda x, y: x if x > y else y, data)
        minimo = reduce(lambda x, y: x if x < y else y, data)

        return maximo, minimo
    
# Patrón Chain of Responsability
class ManejadorTemperaturas:
    def __init__(self, succesor=None):
        self.succesor = succesor

    def manejarTemperaturas(self, request, data):
        pass

class ManejadorTempEstadisticos(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        if request.level == "TempEstadisticos":
            contexto = Context()

            contexto.establecerEstrategia(Media_y_DesvTip())
            media, desv_tip = contexto.hacerAlgo(data)

            contexto.establecerEstrategia(Cuantiles())
            q1, q2, q3 = contexto.hacerAlgo(data)

            contexto.establecerEstrategia(Maximos_y_Minimos())
            max, min = contexto.hacerAlgo(data)

            return media, desv_tip, q1, q2, q3, max, min

        elif self.succesor:
            return self.succesor.manejarTemperaturas(request, data)

class ManejadorLimTemp(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        umbral = 31

        if request.level == "LimTemp":
            ultima_temperatura = data[-1]
            return ultima_temperatura > umbral

        elif self.succesor:
            return self.succesor.manejarTemperaturas(request, data)

class ManejadorAumentoTemp(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        delta_umbral = 10
        n = len(data)
        pivote = max((0, n-6))

        if request.level == "AumentoTemp":
            data_30s = data[pivote:]

            contexto = Context()
            contexto.establecerEstrategia(Maximos_y_Minimos())
            maximo, minimo = contexto.hacerAlgo(data_30s)

            return abs(maximo - minimo) > delta_umbral
        
        elif self.succesor:
            return self.succesor.manejarTemperaturas(request, data)

class Request:
    def __init__(self, level):
        self.level = level


# Patrón Observer
class GeneradorTemperaturas:
    def __init__(self, ultima_temperatura=30, desviacion_tipica=3):
        self._ultima_temperatura = ultima_temperatura
        self._desviacion_tipica = desviacion_tipica

    def generar_temperatura(self):
        # Generar una temperatura aleatoria basada en la última temperatura registrada
        nueva_temperatura = random.normalvariate(self._ultima_temperatura, self._desviacion_tipica)

        # Actualizar la última temperatura registrada
        self._ultima_temperatura = nueva_temperatura

        # Obtener el timestamp actual
        timestamp = int(time.time())

        return (timestamp, nueva_temperatura)

class Observable:
    def __init__(self):
        self._observers = []

    def register_observer(self, observer):
        self._observers.append(observer)

    def remove_observer(self, observer):
        self._observers.remove(observer)

    def notify_observers(self, data):
        for observer in self._observers:
            observer.update(data)

class Observer(ABC):
    @abstractmethod
    def update(self, data):
        pass

class Publisher(Observable):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.value = ""

    def set_value(self, value):
        self.value = value
        self.notify_observers(self.value)

    async def detectarTemperatura(self):
        generador = GeneradorTemperaturas()
        while True:
            nuevoRegistro = generador.generar_temperatura()
            self.set_value(nuevoRegistro)
            await asyncio.sleep(5)


class Operator(Observer):
    def __init__(self, name):
        self.name = name
        self._cola = Queue()

    def update(self, registro):
        if len(self._cola.queue) == 12: # número de registros en 1 min
            self._cola.get()
        self._cola.put(registro)

        self._realizarPasosEncadenados()

    def _transformar_cola_a_lista(self, cola):
        lista = list()
        
        for _ in range(len(cola)):
            elem = cola.get()
            lista.append(elem)

        return lista

    def _realizarPasosEncadenados(self):
        cola = self._cola.queue
        # lista_registros = self._transformar_cola_a_lista(cola)
        fechas, temperaturas = zip(*cola)

        fecha_actual = datetime.fromtimestamp(fechas[-1])
        fecha_actual = fecha_actual.strftime('%d-%m-%Y %H:%M:%S')

        temperaturas = list(temperaturas)

        manejador_te= ManejadorTempEstadisticos()
        manejador_lt= ManejadorLimTemp(succesor=manejador_te)
        manejador_at= ManejadorAumentoTemp(succesor=manejador_lt)

        request1 = Request("TempEstadisticos")
        request2 = Request("LimTemp")
        request3 = Request("AumentoTemp")

        media, dt, q1, q2, q3, max, min = manejador_at.manejarTemperaturas(request1, temperaturas)
        superaUmbral = manejador_at.manejarTemperaturas(request2, temperaturas)
        superaDeltaUmbral = manejador_at.manejarTemperaturas(request3, temperaturas)

        print("-----------------------")
        print(f"<<Fecha: {fecha_actual}>>")
        print(f"Temperatura: {temperaturas[-1]}", end = " | ")
        print(f"Media: {media}", end=" | ")
        print(f"Desviación Típica: {dt}", end=" | ")
        print(f"Q1: {q1}", end=" | ")
        print(f"Mediana: {q2}", end=" | ")
        print(f"Q3: {q3}", end=" | \n")
        print(f"Máximo: {max}", end=" | ")
        print(f"Mínimo: {min}", end=" | ")
        print(f"Supera Umbral: {superaUmbral}", end=" | ")
        print(f"Supera Delta Umbral: {superaDeltaUmbral}")
        print("-----------------------")

class Singleton:
    _unicaInstancia = None

    def __init__(self):
        self.productor = Publisher("Sensor")
        self.subscriptor = Operator("Operador")

    @classmethod
    def obtener_instancia(cls):
        if not cls._unicaInstancia:
            cls._unicaInstancia = cls()
        return cls._unicaInstancia
    
    def iniciar_sgd_IoT(self):
        self.productor.register_observer(self.subscriptor)
        asyncio.run(self.productor.detectarTemperatura())

if __name__ == "__main__":
    singleton = Singleton.obtener_instancia()
    singleton.iniciar_sgd_IoT()

