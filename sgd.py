# Código Sistema de gestión de datos en un entorno IoT

from functools import reduce

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
            indice = q * (n + 1) / 4

            if indice % 1 == 0:
                return datos_ord[int(indice) - 1]

            else: 
                return (datos_ord[int(indice) - 1] + datos_ord[int(indice)]) / 2

        return tuple(map(cuartil, [1, 2, 3]))



class Maximos_y_Minimos(ComputoEstadistico):
    def aplicarAlgoritmo(self, data):
        max = reduce(lambda x, y: x if x > y else y, data)
        min = reduce(lambda x, y: x if x < y else y, data)

        return max, min