# historial.py
# Ejecutar desde la raiz del proyecto: python historial.py
# Genera: output/historial_medico.csv y output/historial_medico.xlsx
"""
Generador de Historial Médico — Modelo AR(1)
10 años de seguimiento por paciente — Diabetes e Hipertensión
Analyt-IA PoC — IMSS-Bienestar CDMX

El historial médico es la parte DINÁMICA del expediente clínico.
Lee el CSV de pacientes (perfil estático) y genera N visitas por
paciente usando un modelo AR(1) para cada variable clínica.

Modelo AR(1):
    x(t) = α × x(t-1) + (1-α) × μ_estado + deriva + ε

Donde:
    x(t-1)   : valor anterior de la variable
    α        : inercia clínica (cuánto depende del pasado)
    μ_estado : media objetivo del estado clínico actual
    deriva   : tendencia de largo plazo según adherencia
    ε        : ruido gaussiano ~ N(0, σ)

Variables generadas por visita:
    glucosa_ayuno_mgdl  → cada visita (NOM-015-SSA2)
    hba1c_pct           → cada 90 días (laboratorio trimestral)
    tas_mmhg            → cada visita (signo vital)
    tad_mmhg            → cada visita (signo vital)
    peso_kg             → cada visita
    imc                 → calculado desde peso y estatura

Estados clínicos:
    Diabetes:
        Sano              → glucosa 70-99,  HbA1c < 5.7%
        Prediabetes       → glucosa 100-125, HbA1c 5.7-6.4%
        DM_controlada     → glucosa 70-130, HbA1c < 7.0%
        DM_descontrolada  → glucosa > 130,  HbA1c ≥ 7.0%

    Hipertensión (criterio JNC-8):
        Sin_HTA           → TAS < 140, TAD < 90
        HTA_controlada    → TAS < 140, TAD < 90 (con tratamiento)
        HTA_descontrolada → TAS ≥ 140 o TAD ≥ 90

Frecuencia de visitas — NOM-015-SSA2-2010:
    DM_descontrolada  : 6 visitas/año
    DM_controlada     : 4 visitas/año
    Prediabetes       : 2 visitas/año
    Solo HTA          : 4 visitas/año
    Sano              : 1 visita/año

Adherencia — ENSANUT 2022:
    36.1% de diabéticos con control glucémico (HbA1c < 7%)
    Adherencia cambia año a año probabilísticamente

Fuentes:
    NOM-015-SSA2-2010  — rangos clínicos, frecuencia visitas
    ENSANUT 2022       — adherencia 36.1%, control glucémico
    JNC-8              — criterios HTA (TAS ≥ 140 o TAD ≥ 90)
"""
import os
import sys
import random
from datetime import date, timedelta

import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

# ===========================================================================
# PARÁMETROS DEL MODELO AR(1)
# ===========================================================================

# Coeficientes de autorregresión — inercia clínica por variable
ALPHA = {
    'glucosa': 0.85,   # cambia en semanas
    'hba1c':   0.92,   # muy inerte — refleja 3 meses
    'tas':     0.75,   # cambia en días
    'tad':     0.75,
    'peso':    0.95,   # muy inerte — cambia en meses
}

# Media objetivo (μ) por estado clínico — NOM-015-SSA2-2010
MU = {
    'Sano': {
        'glucosa': 85.0, 'hba1c': 5.1,
        'tas': 112.0,    'tad': 70.0,
    },
    'Prediabetes': {
        'glucosa': 112.0, 'hba1c': 6.1,
        'tas': 120.0,     'tad': 76.0,
    },
    'DM_controlada': {
        'glucosa': 108.0, 'hba1c': 6.5,
        'tas': 126.0,     'tad': 79.0,
    },
    'DM_descontrolada': {
        'glucosa': 210.0, 'hba1c': 9.0,
        'tas': 138.0,     'tad': 86.0,
    },
}

# Media objetivo HTA — estados independientes
MU_HTA = {
    'Sin_HTA':           {'tas': 112.0, 'tad': 70.0},
    'HTA_controlada':    {'tas': 128.0, 'tad': 78.0},
    'HTA_descontrolada': {'tas': 152.0, 'tad': 94.0},
}

# Desviación estándar del ruido ε por variable
SIGMA = {
    'glucosa': 12.0,
    'hba1c':    0.3,
    'tas':      7.0,
    'tad':      5.0,
    'peso':     0.4,
}

# Límites fisiológicos
LIMITES = {
    'glucosa': (55,  450),
    'hba1c':   (3.5, 15.0),
    'tas':     (85,  220),
    'tad':     (50,  130),
    'peso':    (35,  200),
}

# Frecuencia de visitas por año — NOM-015-SSA2-2010
VISITAS_ANUALES = {
    'Sano':             1,
    'Prediabetes':      2,
    'DM_controlada':    4,
    'DM_descontrolada': 6,
    'solo_HTA':         4,
}

# Laboratorio trimestral — días entre mediciones de HbA1c
FREQ_LAB_DIAS = 90

# Probabilidades de adherencia — ENSANUT 2022
PROB_ADHERENTE_INICIAL = 0.361   # 36.1% control glucémico
PROB_GANAR_ADHERENCIA  = 0.20    # probabilidad anual de volverse adherente
PROB_PERDER_ADHERENCIA = 0.15    # probabilidad anual de perder adherencia

# Tasas de transición anuales
TRANS = {
    'sano_a_prediabetes':      0.02,
    'prediabetes_revierte':    0.15,
    'prediabetes_a_dm':        0.10,
    'descontrol_a_control':    0.30,   # si adherente
    'control_a_descontrol':    0.15,   # si no adherente
    'hta_descontrol_control':  0.25,   # si adherente
    'hta_control_descontrol':  0.10,   # si no adherente
}


# ===========================================================================
# MODELO AR(1)
# ===========================================================================

def ar1(x_prev, variable, estado_dm, deriva=0.0, estado_hta=None):
    """
    Paso AR(1): x(t) = α×x(t-1) + (1-α)×μ + deriva + ε

    Para TAS y TAD usa la media del estado HTA si se proporciona,
    sino usa la media del estado DM.
    """
    alpha = ALPHA[variable]

    if variable in ('tas', 'tad') and estado_hta is not None:
        mu = MU_HTA[estado_hta][variable]
    elif variable == 'peso':
        mu = x_prev   # el peso no tiene media objetivo — solo deriva y ruido
    else:
        mu = MU[estado_dm][variable]

    eps   = random.gauss(0, SIGMA[variable])
    x_new = alpha * x_prev + (1 - alpha) * mu + deriva + eps

    lo, hi = LIMITES[variable]
    return round(max(lo, min(hi, x_new)), 1)


def calcular_deriva(estado_dm, adherente_dm, estado_hta, adherente_hta):
    """
    Deriva anual por variable según estado y adherencia.
    Valores en unidades/año — se dividen por visitas al aplicar.
    """
    # --- Glucosa y HbA1c ---
    if estado_dm == 'DM_descontrolada' and not adherente_dm:
        d_glucosa = random.uniform(10.0, 25.0)
        d_hba1c   = random.uniform(0.3,  0.6)
    elif estado_dm == 'DM_descontrolada' and adherente_dm:
        d_glucosa = random.uniform(-20.0, -8.0)
        d_hba1c   = random.uniform(-0.5,  -0.2)
    elif estado_dm == 'DM_controlada' and adherente_dm:
        d_glucosa = random.uniform(-3.0, 2.0)
        d_hba1c   = random.uniform(-0.05, 0.05)
    elif estado_dm == 'DM_controlada' and not adherente_dm:
        d_glucosa = random.uniform(5.0, 12.0)
        d_hba1c   = random.uniform(0.1, 0.25)
    elif estado_dm == 'Prediabetes':
        d_glucosa = random.uniform(0.5, 3.0)
        d_hba1c   = random.uniform(0.02, 0.08)
    else:  # Sano
        d_glucosa = random.uniform(-1.0, 1.0)
        d_hba1c   = random.uniform(-0.02, 0.02)

    # --- TAS y TAD ---
    if estado_hta == 'HTA_descontrolada' and not adherente_hta:
        d_tas = random.uniform(2.0, 6.0)
        d_tad = random.uniform(1.0, 3.0)
    elif estado_hta == 'HTA_descontrolada' and adherente_hta:
        d_tas = random.uniform(-8.0, -3.0)
        d_tad = random.uniform(-4.0, -1.0)
    elif estado_hta == 'HTA_controlada' and adherente_hta:
        d_tas = random.uniform(-1.0, 1.0)
        d_tad = random.uniform(-0.5, 0.5)
    elif estado_hta == 'HTA_controlada' and not adherente_hta:
        d_tas = random.uniform(2.0, 5.0)
        d_tad = random.uniform(1.0, 2.5)
    else:  # Sin_HTA
        d_tas = random.uniform(-0.5, 0.5)
        d_tad = random.uniform(-0.3, 0.3)

    # --- Peso ---
    if estado_dm == 'DM_descontrolada' and not adherente_dm:
        d_peso = random.uniform(1.0, 3.0)
    elif estado_dm in ('DM_controlada', 'DM_descontrolada') and adherente_dm:
        d_peso = random.uniform(-1.5, 0.5)
    else:
        d_peso = random.uniform(-0.5, 1.0)

    return {
        'glucosa': d_glucosa,
        'hba1c':   d_hba1c,
        'tas':     d_tas,
        'tad':     d_tad,
        'peso':    d_peso,
    }


# ===========================================================================
# ESTADO INICIAL DESDE CSV
# ===========================================================================

def estado_inicial_dm(glucosa_inicial, tiene_diabetes):
    """Determina estado DM inicial desde glucosa_inicial del CSV."""
    if not tiene_diabetes:
        if glucosa_inicial < 100:
            return 'Sano'
        else:
            return 'Prediabetes'
    else:
        if glucosa_inicial <= 130:
            return 'DM_controlada'
        else:
            return 'DM_descontrolada'


def estado_inicial_hta(tiene_hta):
    """Determina estado HTA inicial."""
    if not tiene_hta:
        return 'Sin_HTA'
    else:
        # HTA recién diagnosticada — 2/3 descontrolada, 1/3 controlada
        return 'HTA_descontrolada' if random.random() < 0.667 else 'HTA_controlada'


# ===========================================================================
# TRANSICIONES DE ESTADO
# ===========================================================================

def transicion_dm(estado_dm, adherente, glucosa_actual, hba1c_actual,
                  tiene_dm_base, factor_riesgo=1.0):
    """Transición anual de estado DM."""
    nuevo = estado_dm

    if estado_dm == 'Sano':
        if random.random() < TRANS['sano_a_prediabetes'] * factor_riesgo:
            nuevo = 'Prediabetes'

    elif estado_dm == 'Prediabetes':
        if random.random() < TRANS['prediabetes_revierte']:
            nuevo = 'Sano'
        elif random.random() < TRANS['prediabetes_a_dm']:
            nuevo = 'DM_descontrolada'

    elif estado_dm == 'DM_descontrolada':
        if adherente and random.random() < TRANS['descontrol_a_control']:
            nuevo = 'DM_controlada'
        # Validación con glucosa real
        if glucosa_actual <= 130 and hba1c_actual < 7.0:
            nuevo = 'DM_controlada'

    elif estado_dm == 'DM_controlada':
        if not adherente and random.random() < TRANS['control_a_descontrol']:
            nuevo = 'DM_descontrolada'
        # Validación con glucosa real
        if glucosa_actual > 130 or hba1c_actual >= 7.0:
            nuevo = 'DM_descontrolada'

    return nuevo


def transicion_hta(estado_hta, adherente_hta, tas_actual, tad_actual):
    """Transición anual de estado HTA."""
    nuevo = estado_hta

    if estado_hta == 'Sin_HTA':
        # puede desarrollar HTA si presión sube
        if tas_actual >= 140 or tad_actual >= 90:
            nuevo = 'HTA_descontrolada'

    elif estado_hta == 'HTA_descontrolada':
        if adherente_hta and random.random() < TRANS['hta_descontrol_control']:
            nuevo = 'HTA_controlada'
        if tas_actual < 140 and tad_actual < 90:
            nuevo = 'HTA_controlada'

    elif estado_hta == 'HTA_controlada':
        if not adherente_hta and random.random() < TRANS['hta_control_descontrol']:
            nuevo = 'HTA_descontrolada'
        if tas_actual >= 140 or tad_actual >= 90:
            nuevo = 'HTA_descontrolada'

    return nuevo


# ===========================================================================
# SIMULADOR POR PACIENTE
# ===========================================================================

def simular_paciente(paciente):
    """
    Genera 10 años de historial médico para un paciente.
    Retorna lista de dicts — una fila por visita.
    """
    visitas = []

    nss              = str(paciente['nss']).zfill(11)
    edad_inicial     = int(paciente['edad'])
    sexo             = paciente['sexo']
    estatura_m       = float(paciente['estatura_cm']) / 100.0
    tiene_dm         = paciente['diabetes']     == 'Sí'
    tiene_hta        = paciente['hipertension'] == 'Sí'
    glucosa_ini      = float(paciente['glucosa_inicial'])
    hba1c_ini        = float(paciente['hba1c_inicial'])
    peso_base        = float(paciente['peso_kg'])
    estado_nutricional = paciente['estado_nutricional']
    actividad        = paciente['actividad_fisica']

    # Factor de riesgo para transiciones (sedentario + obeso → mayor riesgo)
    factor_riesgo = 1.0
    if estado_nutricional == 'Obesidad':  factor_riesgo *= 1.7
    if actividad == 'Sedentario':         factor_riesgo *= 1.2

    # --- Estado inicial ---
    estado_dm  = estado_inicial_dm(glucosa_ini, tiene_dm)
    estado_hta = estado_inicial_hta(tiene_hta)

    # --- Adherencia inicial ---
    adherente_dm  = random.random() < PROB_ADHERENTE_INICIAL if tiene_dm  else False
    adherente_hta = random.random() < PROB_ADHERENTE_INICIAL if tiene_hta else False

    # --- Valores iniciales del AR(1) ---
    glucosa = glucosa_ini + random.gauss(0, SIGMA['glucosa'] * 0.3)
    hba1c   = hba1c_ini  + random.gauss(0, SIGMA['hba1c']   * 0.3)
    tas     = MU_HTA[estado_hta]['tas'] + random.gauss(0, SIGMA['tas'])
    tad     = MU_HTA[estado_hta]['tad'] + random.gauss(0, SIGMA['tad'])
    peso    = peso_base

    # Acotar
    glucosa = max(LIMITES['glucosa'][0], min(LIMITES['glucosa'][1], glucosa))
    hba1c   = max(LIMITES['hba1c'][0],  min(LIMITES['hba1c'][1],  hba1c))
    tas     = max(LIMITES['tas'][0],    min(LIMITES['tas'][1],    tas))
    tad     = max(LIMITES['tad'][0],    min(LIMITES['tad'][1],    tad))

    # Fecha inicio: 10 años atrás
    fecha_inicio   = date.today() - timedelta(days=10 * 365)
    dias_desde_lab = 0   # contador para laboratorio trimestral
    num_visita_total = 0

    for anio in range(1, 11):
        edad_actual = edad_inicial + anio - 1

        # Determinar frecuencia de visitas del año
        if tiene_dm or estado_dm not in ('Sano', 'Prediabetes'):
            clave_vis = estado_dm
        elif tiene_hta or estado_hta != 'Sin_HTA':
            clave_vis = 'solo_HTA'
        else:
            clave_vis = 'Sano'

        n_visitas = VISITAS_ANUALES.get(clave_vis, 1)

        # Deriva anual dividida entre visitas
        deriva = calcular_deriva(estado_dm, adherente_dm, estado_hta, adherente_hta)

        # Generar fechas de visitas distribuidas en el año
        dias_anio = sorted(random.sample(range((anio-1)*365, anio*365), n_visitas))

        for i_vis, dia in enumerate(dias_anio):
            fecha  = fecha_inicio + timedelta(days=dia)
            deriva_visita = {k: v / n_visitas for k, v in deriva.items()}

            # --- Paso AR(1) para cada variable ---
            glucosa = ar1(glucosa, 'glucosa', estado_dm, deriva_visita['glucosa'])
            tas     = ar1(tas,     'tas',     estado_dm, deriva_visita['tas'],  estado_hta)
            tad     = ar1(tad,     'tad',     estado_dm, deriva_visita['tad'],  estado_hta)
            peso    = ar1(peso,    'peso',     estado_dm, deriva_visita['peso'])

            # --- HbA1c — solo cada 90 días ---
            dias_desde_lab += (365 // n_visitas)
            es_lab = dias_desde_lab >= FREQ_LAB_DIAS
            if es_lab:
                hba1c = ar1(hba1c, 'hba1c', estado_dm, deriva_visita['hba1c'])
                dias_desde_lab = 0

            # --- IMC calculado ---
            imc_actual = round(peso / (estatura_m ** 2), 1)

            num_visita_total += 1

            visitas.append({
                'nss':              nss,
                'fecha_visita':     fecha.strftime('%d/%m/%Y'),
                'anio_seguimiento': anio,
                'num_visita_anio':  i_vis + 1,
                'num_visita_total': num_visita_total,
                'edad_visita':      edad_actual,
                'sexo':             sexo,
                # --- Estados clínicos ---
                'estado_dm':        estado_dm,
                'estado_hta':       estado_hta,
                'adherente_dm':     'Sí' if adherente_dm  else 'No',
                'adherente_hta':    'Sí' if adherente_hta else 'No',
                # --- Variables clínicas ---
                'glucosa_ayuno_mgdl': round(glucosa, 1),
                'hba1c_pct':          round(hba1c, 1) if es_lab else None,
                'es_laboratorio':     'Sí' if es_lab else 'No',
                'tas_mmhg':           round(tas),
                'tad_mmhg':           round(tad),
                'peso_kg':            round(peso, 1),
                'imc':                imc_actual,
            })

        # ===================================================================
        # TRANSICIONES ANUALES (al final del año)
        # ===================================================================
        # 1. Cambio de adherencia
        if tiene_dm:
            if adherente_dm and random.random() < PROB_PERDER_ADHERENCIA:
                adherente_dm = False
            elif not adherente_dm and random.random() < PROB_GANAR_ADHERENCIA:
                adherente_dm = True

        if tiene_hta:
            if adherente_hta and random.random() < PROB_PERDER_ADHERENCIA:
                adherente_hta = False
            elif not adherente_hta and random.random() < PROB_GANAR_ADHERENCIA:
                adherente_hta = True

        # 2. Transición de estado DM
        estado_dm  = transicion_dm(
            estado_dm, adherente_dm, glucosa, hba1c, tiene_dm, factor_riesgo
        )
        # 3. Transición de estado HTA
        estado_hta = transicion_hta(estado_hta, adherente_hta, tas, tad)

        # 4. Si desarrolló DM en el seguimiento, activar adherencia inicial
        if estado_dm in ('DM_controlada', 'DM_descontrolada') and not tiene_dm:
            tiene_dm    = True
            adherente_dm = random.random() < PROB_ADHERENTE_INICIAL

        # 5. Si desarrolló HTA en el seguimiento
        if estado_hta != 'Sin_HTA' and not tiene_hta:
            tiene_hta    = True
            adherente_hta = random.random() < PROB_ADHERENTE_INICIAL

    return visitas


# ===========================================================================
# PIPELINE PRINCIPAL
# ===========================================================================

def generar_historial():
    print("=" * 70)
    print(" GENERANDO HISTORIAL MÉDICO — 10 AÑOS — MODELO AR(1)")
    print(" Variables: Glucosa, HbA1c, TAS, TAD, Peso, IMC")
    print(" Enfermedades: Diabetes tipo 2 + Hipertensión arterial")
    print("=" * 70)

    df_pacientes = pd.read_csv(config.SALIDA_CSV)
    n_pacientes  = len(df_pacientes)
    print(f"[*] Pacientes cargados: {n_pacientes:,}")

    random.seed(config.SEED)

    todas_visitas = []
    for i, (_, paciente) in enumerate(df_pacientes.iterrows()):
        if (i + 1) % 1000 == 0:
            print(f"    Procesando paciente {i+1:,} / {n_pacientes:,}...")
        todas_visitas.extend(simular_paciente(paciente.to_dict()))

    df = pd.DataFrame(todas_visitas)

    # Rutas de salida
    salida_csv  = os.path.join(config.DIR_OUTPUT, 'historial_medico.csv')
    salida_xlsx = os.path.join(config.DIR_OUTPUT, 'historial_medico.xlsx')

    df.to_csv(salida_csv, index=False, encoding='utf-8')
    df.to_excel(salida_xlsx, index=False, engine='xlsxwriter')

    # --- Resumen ---
    print(f"\n[✓] Historial generado: {len(df):,} visitas")
    print(f"    Promedio visitas por paciente: {len(df)/n_pacientes:.1f}")
    print(f"\n--- Distribución de estados DM (todas las visitas) ---")
    print(df['estado_dm'].value_counts().to_string())
    print(f"\n--- Distribución de estados HTA (todas las visitas) ---")
    print(df['estado_hta'].value_counts().to_string())
    print(f"\n--- Estadísticos glucosa en ayuno ---")
    print(df['glucosa_ayuno_mgdl'].describe().round(1).to_string())
    print(f"\n--- Estadísticos HbA1c (solo visitas con laboratorio) ---")
    lab = df[df['es_laboratorio'] == 'Sí']
    print(f"    Total mediciones HbA1c: {len(lab):,}")
    print(lab['hba1c_pct'].describe().round(2).to_string())
    print(f"\n[*] Archivos guardados:")
    print(f"    CSV:   {salida_csv}")
    print(f"    Excel: {salida_xlsx}")
    print("=" * 70)


if __name__ == "__main__":
    generar_historial()