# personas/enfermedades.py
"""
Módulo de asignación de enfermedades crónicas con comorbilidades.

Enfermedades modeladas:
    - Diabetes tipo 2
    - Hipertensión arterial

Fuentes:
    ENSANUT 2022 — prevalencia total de diabetes (18.3%) e hipertensión (29.4%)
    ENSANUT 2016 — razones de momios por edad y estado nutricional para diabetes
    INSP         — factores de riesgo de hipertensión por edad y sexo

Metodología:
    1. Diabetes tipo 2:
       P(diabetes | edad, IMC, actividad) =
           prob_base(edad) × factor_IMC × factor_actividad
       Acotada a [0, 1].

    2. Hipertensión arterial:
       P(hta | edad, sexo, diabetes) =
           prob_base(edad, sexo) × factor_comorbilidad_diabetes
       Acotada a [0, 1].
"""
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def _grupo_enfermedad(edad: int) -> str:
    """Mapea edad al grupo epidemiológico de enfermedades crónicas."""
    if edad <= 39:
        return 'Jovenes_18_39'
    elif edad <= 59:
        return 'Adultos_40_59'
    else:
        return 'Adultos_Mayores_60_Mas'


def asignar_enfermedades(edad: int, sexo: str,
                          estado_nutricional: str,
                          actividad_fisica: str) -> dict:
    """
    Asigna diabetes tipo 2 e hipertensión arterial al paciente
    considerando edad, sexo, estado nutricional, actividad física
    y comorbilidad entre enfermedades.

    Parámetros
    ----------
    edad               : int — edad del paciente en años
    sexo               : str — 'Masculino', 'Femenino', 'Otro', 'Desconocido'
    estado_nutricional : str — 'Normal', 'Sobrepeso', 'Obesidad'
    actividad_fisica   : str — 'Activo', 'Sedentario'

    Retorna
    -------
    dict con claves:
        'diabetes'     : 'Sí' | 'No'
        'hipertension' : 'Sí' | 'No'
    """
    grupo  = _grupo_enfermedad(edad)
    sexo_k = sexo if sexo in ['Masculino', 'Femenino'] else 'Otro'

    # ------------------------------------------------------------------
    # 1. Diabetes tipo 2
    #    P = prob_base(edad) × factor_IMC × factor_actividad
    # ------------------------------------------------------------------
    prob_dm = (
        config.PROB_DIABETES_BASE[grupo] *
        config.FACTOR_DIABETES_IMC.get(estado_nutricional, 1.0) *
        config.FACTOR_DIABETES_ACTIVIDAD.get(actividad_fisica, 1.0)
    )
    prob_dm  = min(prob_dm, 1.0)
    tiene_dm = random.random() < prob_dm
    diabetes = 'Sí' if tiene_dm else 'No'

    # ------------------------------------------------------------------
    # 2. Hipertensión arterial
    #    P = prob_base(edad, sexo) × factor_comorbilidad_diabetes
    # ------------------------------------------------------------------
    prob_hta = config.PROB_HIPERTENSION_BASE[grupo][sexo_k]

    if tiene_dm:
        prob_hta *= config.FACTOR_HIPERTENSION_DIABETES

    prob_hta     = min(prob_hta, 1.0)
    hipertension = 'Sí' if random.random() < prob_hta else 'No'

    return {
        'diabetes':     diabetes,
        'hipertension': hipertension
    }