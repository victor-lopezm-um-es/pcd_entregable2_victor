# Código Sistema de gestión de datos en un entorno IoT

from functools import reduce

def calculo_estadisticos_basicos(temperaturas):
    n = len(temperaturas)
    E_X = reduce(lambda x, y: x + y, temperaturas)/n
    print('Media: ' + str(E_X))

    tem_ord = zip(sorted(temperaturas), range(1,n+1))
    medianas = list(filter(lambda x: esMediana(x[1], n), tem_ord))
    medianas = list(map(lambda x: x[0], medianas))

    if len(medianas) == 1:
        mediana = medianas[0]

    else: 
        mediana = sum(medianas) / 2

    print('Mediana(s): ' + str(mediana))

    S2 = reduce(lambda x,y: x + y, map(lambda x: (1/n) * (x - E_X)**2, temperaturas))
    S = S2 ** (1/2)
    
    print("Desviación típica: " + str(S))

def esMediana(ind, n):
    if n%2 == 1:
        return (n // 2) + 1 == ind
    
    else:
        return (n // 2) == ind or (n // 2) + 1 == ind
    

def sobrepasaTemperatura(temperaturas, umbral):
    return any(map(lambda t: t > umbral, temperaturas))