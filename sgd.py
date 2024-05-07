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
    def __init__(self):
        self._strategy = None

    def establecerEstrategia(self, strategy):
        self._strategy = strategy

    def algoritmo_en_contexto(self, data):
        return self._strategy.aplicarAlgoritmo(data)

class ComputoEstadistico: # Interfaz de Estrategia
    def aplicarAlgoritmo(self, data):
        pass
    
class Media_y_DesvTip(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        n = len(data)
        media = reduce(lambda x, y: x + y, data) / n # con reduce hacemos un sumatorio de los datos

        varianza = reduce(lambda x, y: x + y,  # 2.con reduce obtengo el sumatorio (varianza)
                          map(lambda x: (1/n) * (x - media)**2, data ) ) # 1.con map obtengo las diferencias de los datos con la media al cuadrado
        desv_tip = varianza ** (.5)                                      # ponderadas por 1/n

        return media, desv_tip

class Cuantiles(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        datos_ord = sorted(data)
        n = len(datos_ord)

        def cuartil(q):
            if n == 1:
                return datos_ord[0] # Si solo tengo un elemento, salida directa

            indice = q * (n+1) / 4
            parte_decimal = indice % 1

            if parte_decimal == 0:
                return datos_ord[int(indice) - 1]

            else: 
                if int(indice) == n and q == 3: # Para procurar que los índices no salgan del rango permitido
                    return datos_ord[-1]
                else:
                    return (datos_ord[int(indice) - 1] + datos_ord[int(indice)]) / 2 # Calculo el cuartil haciendo una media

        return tuple(map(cuartil, [1, 2, 3])) # con map obtengo un iterable con los valores de cada cuartil


class Maximos_y_Minimos(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        maximo = reduce(lambda x, y: x if x > y else y, data) # el reduce me permite quedarme con el máximo y mínimo
        minimo = reduce(lambda x, y: x if x < y else y, data)

        return maximo, minimo
    
# Patrón Chain of Responsibility
class ManejadorTemperaturas:
    def __init__(self, succesor=None):
        self.succesor = succesor

    def manejarTemperaturas(self, request, data):
        pass

class ManejadorTempEstadisticos(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        if request.level == "TempEstadisticos":
            contexto = Context()
        # Aquí voy cambiando de contexto y aplicando su debido algoritmo
        # para sus respectivos estadísticos
            contexto.establecerEstrategia(Media_y_DesvTip())
            media, desv_tip = contexto.algoritmo_en_contexto(data)

            contexto.establecerEstrategia(Cuantiles())
            q1, q2, q3 = contexto.algoritmo_en_contexto(data)

            contexto.establecerEstrategia(Maximos_y_Minimos())
            max, min = contexto.algoritmo_en_contexto(data)

            return media, desv_tip, q1, q2, q3, max, min

        # Si no se trata de computar estadísticos, paso la tarea al sucesor
        elif self.succesor:
            return self.succesor.manejarTemperaturas(request, data)

class ManejadorLimTemp(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        umbral = 31
        # Establezco si el último dato supera el umbral
        if request.level == "LimTemp":
            ultima_temperatura = data[-1]
            return ultima_temperatura > umbral
        # Si no se trata de computar estadísticos, paso la tarea al sucesor
        elif self.succesor:
            return self.succesor.manejarTemperaturas(request, data)

class ManejadorAumentoTemp(ManejadorTemperaturas):
    def manejarTemperaturas(self, request, data):
        if request.level == "AumentoTemp":    
            delta_umbral = 10
            n = len(data)
            pivote = max((0, n-6)) # establezco un pivote para quedarme con los datos de los últimos 30 s
        
            data_30s = data[pivote:]

            # Me quedo con el máximo y mínimo del subconjunto y establezco si la temperatura
            # varía significativamente
            contexto = Context()
            contexto.establecerEstrategia(Maximos_y_Minimos())
            maximo, minimo = contexto.algoritmo_en_contexto(data_30s)

            return abs(maximo - minimo) > delta_umbral
        # Si no se trata de computar estadísticos, paso la tarea al sucesor
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
        # Genera una temperatura aleatoria basada en la última temperatura registrada (usando una distribución normal)
        nueva_temperatura = random.normalvariate(self._ultima_temperatura, self._desviacion_tipica)

        # Actualiza la última temperatura registrada
        self._ultima_temperatura = nueva_temperatura

        # Obtiene el timestamp actual
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

class PublicadorDatosSensor(Observable):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.value = tuple()

    def set_value(self, value):
        self.value = value
        self.notify_observers(self.value)

    async def detectarTemperatura(self): # corrutina asíncrona para detectar datos
        generador = GeneradorTemperaturas() # puesto que no detecta más hasta dentro de 5 segundo
        while True:
            nuevoRegistro = generador.generar_temperatura()
            self.set_value(nuevoRegistro)
            await asyncio.sleep(5) 

class Operator(Observer):
    def __init__(self, name):
        self.name = name
        self.cola = Queue()

    def update(self, registro):
        if len(self.cola.queue) == 12: # número de registros en 1 min
            self.cola.get() # me aseguro que solo halla datos del último minuto

        self.cola.put(registro) # coloco enla cola el último dato

        self._realizarPasosEncadenados()

    def _realizarPasosEncadenados(self):
        cola = self.cola.queue # obtengo la cola en forma de lista
        fechas, temperaturas = zip(*cola) # descomprimo para tener en dos estructuras las fechas y las temperaturas

        fecha_actual = datetime.fromtimestamp(fechas[-1])
        fecha_actual = fecha_actual.strftime('%d-%m-%Y %H:%M:%S') # obtengo la última fecha

        temperaturas = list(temperaturas) # convierto a lista para poder operar más adelante

        # Establecemos los manejadores
        manejador_te= ManejadorTempEstadisticos()
        manejador_lt= ManejadorLimTemp(succesor=manejador_te)
        manejador_at= ManejadorAumentoTemp(succesor=manejador_lt)

        # Las peticiones
        request1 = Request("TempEstadisticos")
        request2 = Request("LimTemp")
        request3 = Request("AumentoTemp")

        # Se procesa y obtiene toda la información deseada
        media, dt, q1, q2, q3, max, min = manejador_at.manejarTemperaturas(request1, temperaturas)
        superaUmbral = manejador_at.manejarTemperaturas(request2, temperaturas)
        superaDeltaUmbral = manejador_at.manejarTemperaturas(request3, temperaturas)

        # Se imprime en este formato todos los cálculos de los datos procesados
        print("-----------------------")
        print(f"<<Fecha: {fecha_actual}>>")
        print(f"Temperatura: {round(temperaturas[-1], 2)}", end = " | ")
        print(f"Media: {round(media, 2)}", end=" | ")
        print(f"Desviación Típica: {round(dt, 2)}", end=" | ")
        print(f"Q1: {round(q1, 2)}", end=" | ")
        print(f"Mediana: {round(q2, 2)}", end=" | ")
        print(f"Q3: {round(q3, 2)}", end=" | \n")
        print(f"Máximo: {round(max, 2)}", end=" | ")
        print(f"Mínimo: {round(min, 2)}", end=" | ")
        print(f"Supera Umbral: {superaUmbral}", end=" | ")
        print(f"Supera Delta Umbral: {superaDeltaUmbral}")
        print("-----------------------")
        
# Patrón Singleton
class Singleton_Sis_IoT:
    _unicaInstancia = None

    def __init__(self):
        self._productor = PublicadorDatosSensor("Sensor") # Se le atribuye al sistema un sensor que publica los datos
        self._operador = Operator("Operador")             # y un observador que procesa esos datos y opera con ellos

    @classmethod
    def obtener_instancia(cls): # nos aseguramos de obtener una única instancia
        if not cls._unicaInstancia:
            cls._unicaInstancia = cls()
        return cls._unicaInstancia
    
    def iniciar_sgd_IoT(self): # con esta función se inicia el sistema automáticamente
        self._productor.register_observer(self._operador)
        asyncio.run(self._productor.detectarTemperatura())

# Código principal
if __name__ == "__main__":
    singleton = Singleton_Sis_IoT.obtener_instancia() 
    singleton.iniciar_sgd_IoT()

