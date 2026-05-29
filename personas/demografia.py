# personas/demografia.py
import random
import sys
import os

# Asegurar herencia de rutas en caso de pruebas unitarias locales sueltas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config as config

def asignar_sexo():
    """
    Asigna sexo con los pesos del Censo de Población y Vivienda 2020 CDMX.
    Mujeres: 52.2% | Hombres: 47.8%
    Fuente: INEGI, Censo 2020 — 9,209,944 habitantes CDMX.
    """
    opciones = list(config.PESOS_SEXO.keys())
    pesos    = list(config.PESOS_SEXO.values())
    return random.choices(opciones, weights=pesos, k=1)[0]