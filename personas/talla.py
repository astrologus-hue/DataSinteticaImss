# personas/talla.py
import random
import sys
import os

# Asegurar herencia de rutas en caso de pruebas unitarias locales sueltas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config as config

def calcular_antropometria(sexo, edad):
    """
    Asigna estatura en cm (Entero) e IMC de acuerdo a las estadísticas de probabilidad 
    del INEGI segmentadas por grupo de edad y sexo (ENSANUT 2018).
    
    Regresa una tupla: (estatura_cm, imc, peso_kg, estado_nutricional)
    """
    # 1. Determinar el grupo epidemiológico del INEGI según la edad del paciente
    if edad >= 60:
        grupo_edad = 'Adultos_Mayores_60_Mas'
    else:
        grupo_edad = 'Adultos_30_59'

    sexo_cfg = sexo if sexo in ['Masculino', 'Femenino'] else 'Masculino'
    probs = config.ESTADISTICAS_INEGI[grupo_edad][sexo_cfg]

    # 2. Muestreo del Estado Nutricional usando los pesos estadísticos de tus imágenes
    estados_nutricionales = ['sobrepeso', 'obesidad', 'normal']
    pesos_probabilidad = [probs['sobrepeso'], probs['obesidad'], probs['normal']]
    
    estado_asignado = random.choices(estados_nutricionales, weights=pesos_probabilidad, k=1)[0]

    # 3. Generar el IMC aleatorio que pertenezca estrictamente a la categoría ganadora
    if estado_asignado == 'normal':
        imc = random.uniform(18.5, 24.9)
        etiqueta_estado = 'Normal'
    elif estado_asignado == 'sobrepeso':
        imc = random.uniform(25.0, 29.9)
        etiqueta_estado = 'Sobrepeso'
    else:  # obesidad
        imc = random.uniform(30.0, 42.0)
        etiqueta_estado = 'Obesidad'
    
    imc = round(imc, 1)

    # 4. Generar la Estatura en centímetros usando la campana de Gauss por sexo
    if sexo == 'Masculino':
        estatura_cm = random.gauss(config.ALTURA_MEDIA_MASCULINO, config.ALTURA_DESVIACION)
    elif sexo == 'Femenino':
        estatura_cm = random.gauss(config.ALTURA_MEDIA_FEMENINO, config.ALTURA_DESVIACION)
    else:
        estatura_cm = random.gauss(164.0, config.ALTURA_DESVIACION)

    # Acotar estaturas a los límites de las cartillas y convertir a ENTERO
    estatura_cm = max(144.0, min(184.0, estatura_cm))
    estatura_cm = int(round(estatura_cm))  # Redondeo final forzado a entero

    # 5. Calcular Peso Congruente (Convertimos estatura a metros solo para la fórmula)
    estatura_m = estatura_cm / 100.0
    peso_kg = imc * (estatura_m ** 2)
    peso_kg = round(peso_kg, 1)

    return estatura_cm, imc, peso_kg, etiqueta_estado