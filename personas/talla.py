# personas/talla.py
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config as config


def _grupo_ensanut(edad: int) -> str:
    """Mapea edad al grupo del ENSANUT 2018."""
    if edad <= 19:
        return 'Jovenes_18_19'
    elif edad <= 29:
        return 'Adultos_20_29'
    elif edad <= 59:
        return 'Adultos_30_59'
    else:
        return 'Adultos_Mayores_60_Mas'


def _grupo_mopradef(edad: int) -> str:
    """Mapea edad al grupo del MOPRADEF 2025."""
    if edad <= 19:
        return 'Jovenes_18_19'
    elif edad <= 29:
        return 'Adultos_20_29'
    elif edad <= 39:
        return 'Adultos_30_39'
    elif edad <= 49:
        return 'Adultos_40_49'
    elif edad <= 59:
        return 'Adultos_50_59'
    else:
        return 'Adultos_Mayores_60_Mas'


def asignar_actividad_fisica(sexo: str, edad: int) -> str:
    """
    Asigna actividad física usando probabilidades reales del MOPRADEF 2025
    cruzadas por edad y sexo.
    Retorna 'Activo' o 'Sedentario'.
    """
    grupo  = _grupo_mopradef(edad)
    sexo_k = sexo if sexo in config.PROB_ACTIVIDAD_FISICA[grupo] else 'Otro'
    prob   = config.PROB_ACTIVIDAD_FISICA[grupo][sexo_k]
    return 'Activo' if random.random() < prob else 'Sedentario'


def calcular_antropometria(sexo: str, edad: int) -> tuple:
    """
    Asigna estatura (cm entero), IMC, peso, estado nutricional
    y actividad física.

    Metodología de correlación actividad ↔ estado nutricional:
    -----------------------------------------------------------
    Se usan los pesos reales del ENSANUT 2018 como base y se aplican
    multiplicadores para sesgar la distribución según actividad física,
    SIN inventar distribuciones nuevas:

        Activo:
            normal    × 2.5  → se favorece fuertemente
            sobrepeso × 1.0  → sin cambio
            obesidad  × 0.15 → se penaliza fuertemente (minoría)

        Sedentario:
            normal    × 0.15 → se penaliza fuertemente (minoría)
            sobrepeso × 1.0  → sin cambio
            obesidad  × 2.5  → se favorece fuertemente

    random.choices normaliza los pesos automáticamente, por lo que
    las proporciones relativas del ENSANUT se preservan dentro de
    cada subgrupo permitido.

    Fuentes:
        Estado nutricional base : ENSANUT 2018 por grupo de edad y sexo
        Actividad física        : MOPRADEF 2025 cruzado por edad y sexo

    Retorna
    -------
    tuple : (estatura_cm, imc, peso_kg, estado_nutricional, actividad_fisica)
    """
    # 1. Pesos base del ENSANUT 2018
    grupo_ensanut = _grupo_ensanut(edad)
    sexo_cfg      = sexo if sexo in ['Masculino', 'Femenino'] else 'Masculino'
    probs         = config.ESTADISTICAS_INEGI[grupo_ensanut][sexo_cfg]

    # 2. Actividad física — MOPRADEF 2025
    actividad = asignar_actividad_fisica(sexo, edad)

    # 3. Aplicar multiplicadores sobre pesos ENSANUT según actividad
    #    Los multiplicadores sesgan sin reemplazar la fuente estadística.
    #    random.choices normaliza internamente — no necesitan sumar 1.
    if actividad == 'Activo':
        pesos = [
            probs['normal']    * 2.0,   # favorecido
            probs['sobrepeso'] * 0.6,   # moderadamente penalizado
            probs['obesidad']  * 0.25,  # penalizado — minoría real (~11%)
        ]
    else:  # Sedentario
        pesos = [
            probs['normal']    * 0.25,  # penalizado — minoría real (~5%)
            probs['sobrepeso'] * 1.0,   # neutro
            probs['obesidad']  * 2.0,   # favorecido — mayoría real (~59%)
        ]

    estados = ['normal', 'sobrepeso', 'obesidad']
    estado  = random.choices(estados, weights=pesos, k=1)[0]

    if estado == 'normal':
        imc             = round(random.uniform(18.5, 24.9), 1)
        etiqueta_estado = 'Normal'
    elif estado == 'sobrepeso':
        imc             = round(random.uniform(25.0, 29.9), 1)
        etiqueta_estado = 'Sobrepeso'
    else:
        imc             = round(random.uniform(30.0, 42.0), 1)
        etiqueta_estado = 'Obesidad'

    # 4. Estatura — distribución gaussiana por sexo
    if sexo == 'Masculino':
        estatura_cm = random.gauss(config.ALTURA_MEDIA_MASCULINO, config.ALTURA_DESVIACION)
    elif sexo == 'Femenino':
        estatura_cm = random.gauss(config.ALTURA_MEDIA_FEMENINO, config.ALTURA_DESVIACION)
    else:
        estatura_cm = random.gauss(164.0, config.ALTURA_DESVIACION)

    estatura_cm = max(144.0, min(184.0, estatura_cm))
    estatura_cm = int(round(estatura_cm))

    # 5. Peso — derivado de IMC y estatura
    peso_kg = round(imc * (estatura_cm / 100.0) ** 2, 1)

    return estatura_cm, imc, peso_kg, etiqueta_estado, actividad