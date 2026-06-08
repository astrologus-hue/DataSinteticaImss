# validar_dataset.py
# Ejecutar desde la raiz del proyecto: python validar_dataset.py
"""
Validador Estratificado del Dataset Sintético — IMSS CDMX

Compara las distribuciones del CSV contra fuentes oficiales usando
tasas estratificadas por grupo de edad y sexo cuando el dato existe,
y totales cuando solo se dispone del agregado nacional.

Fuentes de referencia:
    Censo INEGI 2020    — sexo, edad
    ENSANUT 2018        — estado nutricional por edad y sexo (dato directo)
    MOPRADEF 2025       — actividad física por edad y sexo (dato directo)
    ENSANUT 2022        — diabetes 18.3%, HTA 29.4% (dato directo total)
    ENSANUT 2016        — RM por edad para diabetes (usado para derivar)
    ENSA 2004 CDMX      — dislipidemia por IMC y comorbilidades (dato directo)
    ENSANUT 2022        — tabaquismo, alcoholismo (dato directo)
    ENSANUT 2012/Gto22  — antecedentes heredofamiliares (dato directo)

Nota sobre validaciones DERIVADAS:
    Las prevalencias de diabetes e HTA por grupo de edad NO están
    publicadas directamente en el ENSANUT 2022. Se calcularon usando
    las razones de momios (RM) del ENSANUT 2016 calibradas para
    reproducir exactamente el total reportado en ENSANUT 2022.
    Estas se marcan como DERIVADO en el código y en las gráficas.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

# --- Colores consola ---
VERDE    = '\x1b[32m'
ROJO     = '\x1b[31m'
AMARILLO = '\x1b[33m'
RESET    = '\x1b[0m'
BOLD     = '\x1b[1m'
TOLERANCIA = 0.05

# --- Paleta gráficas ---
C_DATASET = '#1A237E'
C_REF     = '#4FC3F7'
C_OK      = '#2E7D32'
C_WARN    = '#F9A825'
C_ERROR   = '#C62828'
BG        = '#F8FAFD'


def semaforo(diff, tol=TOLERANCIA):
    if diff <= tol:       return f'{VERDE}✓ OK{RESET}'
    elif diff <= tol * 2: return f'{AMARILLO}~ ACEPTABLE{RESET}'
    return f'{ROJO}✗ REVISAR{RESET}'


def color_barra(diff, tol=TOLERANCIA):
    if diff <= tol:       return C_OK
    elif diff <= tol * 2: return C_WARN
    return C_ERROR


def grupo_edad(edad):
    if edad <= 19:   return '18-19'
    elif edad <= 29: return '20-29'
    elif edad <= 59: return '30-59'
    else:            return '60+'


def grupo_edad_amplio(edad):
    if edad <= 39:   return '18-39'
    elif edad <= 59: return '40-59'
    else:            return '60+'


# ===========================================================================
# RECOLECCIÓN DE DATOS
# ===========================================================================
def recolectar(df):
    """Calcula todas las métricas y las retorna como dict."""
    dm2    = df[df['diabetes']    == 'Sí']
    no_dm2 = df[df['diabetes']    == 'No']
    hta_sin = df[(df['hipertension'] == 'Sí') & (df['diabetes'] == 'No')]

    datos = {}

    # ------------------------------------------------------------------
    # SEXO — Censo INEGI 2020 CDMX (dato directo)
    # ------------------------------------------------------------------
    sexo = df['sexo'].value_counts(normalize=True)
    datos['sexo'] = {
        'Femenino':  {'real': sexo.get('Femenino',  0), 'ref': 0.522},
        'Masculino': {'real': sexo.get('Masculino', 0), 'ref': 0.478},
    }

    # ------------------------------------------------------------------
    # ESTADO NUTRICIONAL — ENSANUT 2018 (dato directo promedio ponderado)
    # ------------------------------------------------------------------
    nut = df['estado_nutricional'].value_counts(normalize=True)
    datos['nutricional'] = {
        'Normal':    {'real': nut.get('Normal',    0), 'ref': 0.26},
        'Sobrepeso': {'real': nut.get('Sobrepeso', 0), 'ref': 0.39},
        'Obesidad':  {'real': nut.get('Obesidad',  0), 'ref': 0.35},
    }

    # ------------------------------------------------------------------
    # ACTIVIDAD FÍSICA — MOPRADEF 2025 (dato directo)
    # ------------------------------------------------------------------
    act = df['actividad_fisica'].value_counts(normalize=True)
    datos['actividad'] = {
        'Activo':     {'real': act.get('Activo',     0), 'ref': 0.417},
        'Sedentario': {'real': act.get('Sedentario', 0), 'ref': 0.583},
    }

    # ------------------------------------------------------------------
    # ENFERMEDADES — totales directos (ENSANUT 2022 / ENSA 2004)
    # ------------------------------------------------------------------
    datos['enfermedades'] = {
        'Diabetes':     {'real': (df['diabetes']    == 'Sí').mean(), 'ref': 0.183},
        'Hipertensión': {'real': (df['hipertension']== 'Sí').mean(), 'ref': 0.294},
        'Dislipidemia': {'real': (df['dislipidemia']== 'Sí').mean(), 'ref': 0.433},
    }

    # ------------------------------------------------------------------
    # DIABETES POR GRUPO DE EDAD — DERIVADO
    # Método: RM del ENSANUT 2016 (40-59=9.2x, 60+=24.6x vs 20-39)
    # calibrados para reproducir exactamente 18.3% total (ENSANUT 2022)
    # NOTA: NO son tablas directas del ENSANUT 2022. Son estimaciones
    # derivadas usadas únicamente para validación relativa entre grupos.
    # ------------------------------------------------------------------
    datos['diabetes_edad'] = {
        '20-39 (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '18-39']['diabetes'] == 'Sí').mean(),
            'ref':  0.021
        },
        '40-59 (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '40-59']['diabetes'] == 'Sí').mean(),
            'ref':  0.196
        },
        '60+   (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '60+']['diabetes'] == 'Sí').mean(),
            'ref':  0.524
        },
    }

    # ------------------------------------------------------------------
    # HTA POR GRUPO DE EDAD — DERIVADO
    # Método: RP estimadas (40-59≈3.0x, 60+≈5.5x vs 20-39)
    # calibradas para reproducir exactamente 29.4% total (ENSANUT 2022)
    # NOTA: NO son tablas directas del ENSANUT 2022. Son estimaciones
    # derivadas usadas únicamente para validación relativa entre grupos.
    # ------------------------------------------------------------------
    datos['hta_edad'] = {
        '20-39 (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '18-39']['hipertension'] == 'Sí').mean(),
            'ref':  0.113
        },
        '40-59 (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '40-59']['hipertension'] == 'Sí').mean(),
            'ref':  0.339
        },
        '60+   (DERIV.)': {
            'real': (df[df['grupo_edad_amplio'] == '60+']['hipertension'] == 'Sí').mean(),
            'ref':  0.622
        },
    }

    # ------------------------------------------------------------------
    # COMORBILIDADES EN DIABÉTICOS — ENSA 2004 CDMX (dato directo)
    # ------------------------------------------------------------------
    datos['comorbilidades'] = {}
    if len(dm2) > 0:
        datos['comorbilidades']['HTA|DM2'] = {
            'real': (dm2['hipertension'] == 'Sí').mean(), 'ref': 0.46}
        datos['comorbilidades']['HCL|DM2'] = {
            'real': (dm2['dislipidemia'] == 'Sí').mean(),  'ref': 0.552}
    if len(hta_sin) > 0:
        datos['comorbilidades']['HCL|HTA sin DM2'] = {
            'real': (hta_sin['dislipidemia'] == 'Sí').mean(), 'ref': 0.525}

    # ------------------------------------------------------------------
    # TABAQUISMO — ENSANUT 2022 (dato directo)
    # ------------------------------------------------------------------
    tab = df['tabaquismo'].value_counts(normalize=True)
    datos['tabaquismo'] = {
        'Activo':     {'real': tab.get('Activo',     0), 'ref': 0.195},
        'Ex-fumador': {'real': tab.get('Ex-fumador', 0), 'ref': 0.178},
        'Nunca':      {'real': tab.get('Nunca',       0), 'ref': 0.627},
    }

    # ------------------------------------------------------------------
    # ALCOHOLISMO — ENSANUT 2022 (dato directo)
    # ------------------------------------------------------------------
    alc = df['alcoholismo'].value_counts(normalize=True)
    datos['alcoholismo'] = {
        'No consume': {'real': alc.get('No consume', 0), 'ref': 0.445},
        'Consume':    {'real': alc.get('Consume',    0), 'ref': 0.331},
        'Excesivo':   {'real': alc.get('Excesivo',   0), 'ref': 0.224},
    }

    # ------------------------------------------------------------------
    # ANTECEDENTES HEREDOFAMILIARES — ENSANUT 2012/Gto2022 (dato directo)
    # ------------------------------------------------------------------
    datos['antecedentes'] = {
        'AHF DM2 (general)': {
            'real': (df['antecedente_familiar_dm2'] == 'Sí').mean(), 'ref': 0.318},
        'AHF HTA (general)': {
            'real': (df['antecedente_familiar_hta'] == 'Sí').mean(), 'ref': 0.314},
    }
    if len(dm2) > 0:
        datos['antecedentes']['AHF DM2 (diabéticos)'] = {
            'real': (dm2['antecedente_familiar_dm2'] == 'Sí').mean(), 'ref': 0.5446}
        datos['antecedentes']['AHF DM2 (no diabét.)'] = {
            'real': (no_dm2['antecedente_familiar_dm2'] == 'Sí').mean(), 'ref': 0.3481}

    # ------------------------------------------------------------------
    # ESTADO NUTRICIONAL ESTRATIFICADO — ENSANUT 2018 (dato directo)
    # ------------------------------------------------------------------
    ref_nut_strat = {
        ('18-19', 'Masculino'): {'Normal': 0.64, 'Sobrepeso': 0.21, 'Obesidad': 0.15},
        ('18-19', 'Femenino'):  {'Normal': 0.59, 'Sobrepeso': 0.27, 'Obesidad': 0.14},
        ('20-29', 'Masculino'): {'Normal': 0.34, 'Sobrepeso': 0.42, 'Obesidad': 0.24},
        ('20-29', 'Femenino'):  {'Normal': 0.37, 'Sobrepeso': 0.37, 'Obesidad': 0.26},
        ('30-59', 'Masculino'): {'Normal': 0.23, 'Sobrepeso': 0.42, 'Obesidad': 0.35},
        ('30-59', 'Femenino'):  {'Normal': 0.17, 'Sobrepeso': 0.37, 'Obesidad': 0.46},
        ('60+',   'Masculino'): {'Normal': 0.32, 'Sobrepeso': 0.42, 'Obesidad': 0.26},
        ('60+',   'Femenino'):  {'Normal': 0.23, 'Sobrepeso': 0.37, 'Obesidad': 0.40},
    }
    datos['nut_estratificado'] = {}
    for (ge, sx), ref in ref_nut_strat.items():
        sub = df[(df['grupo_edad'] == ge) & (df['sexo'] == sx)]
        if len(sub) < 30:
            continue
        nut_r = sub['estado_nutricional'].value_counts(normalize=True)
        for estado, esp in ref.items():
            key = f"{ge} {sx}\n{estado}"
            datos['nut_estratificado'][key] = {'real': nut_r.get(estado, 0), 'ref': esp}

    return datos


# ===========================================================================
# CONSOLA
# ===========================================================================
def imprimir_consola(datos):
    print("=" * 70)
    print(f"{BOLD} VALIDACIÓN ESTRATIFICADA — DATASET SINTÉTICO IMSS CDMX{RESET}")
    print("=" * 70)

    secciones = [
        ('SEXO — Censo INEGI 2020 [DATO DIRECTO]',                   'sexo'),
        ('ESTADO NUTRICIONAL — ENSANUT 2018 [DATO DIRECTO]',         'nutricional'),
        ('ACTIVIDAD FÍSICA — MOPRADEF 2025 [DATO DIRECTO]',          'actividad'),
        ('ENFERMEDADES TOTALES — ENSANUT 2022 [DATO DIRECTO]',       'enfermedades'),
        ('DIABETES POR EDAD — RM ENSANUT 2016 x ENSANUT 2022 [DERIVADO]', 'diabetes_edad'),
        ('HTA POR EDAD — RP estimadas x ENSANUT 2022 [DERIVADO]',    'hta_edad'),
        ('COMORBILIDADES — ENSA 2004 CDMX [DATO DIRECTO]',           'comorbilidades'),
        ('TABAQUISMO — ENSANUT 2022 [DATO DIRECTO]',                  'tabaquismo'),
        ('ALCOHOLISMO — ENSANUT 2022 [DATO DIRECTO]',                 'alcoholismo'),
        ('ANTECEDENTES HEREDOFAMILIARES — ENSANUT 2012 [DATO DIRECTO]', 'antecedentes'),
    ]

    for titulo, key in secciones:
        print(f"\n{BOLD}{titulo}{RESET}")
        for cat, vals in datos[key].items():
            real = vals['real']
            ref  = vals['ref']
            diff = abs(real - ref)
            print(f"  {semaforo(diff)}  {cat}: dataset={real:.1%}  ref={ref:.1%}  diff={diff:.1%}")

    print(f"\n{'=' * 70}")
    print(f"  {VERDE}✓ OK{RESET}        diff ≤ 5%")
    print(f"  {AMARILLO}~ ACEPTABLE{RESET}  diff ≤ 10%")
    print(f"  {ROJO}✗ REVISAR{RESET}   diff > 10%")
    print(f"  [DERIVADO] = estimación calculada, no tabla directa de la encuesta")
    print("=" * 70)


# ===========================================================================
# GRÁFICAS
# ===========================================================================
def graficar_comparacion(nombre, datos_seccion, ax, fuente=''):
    cats  = list(datos_seccion.keys())
    reals = [datos_seccion[c]['real'] for c in cats]
    refs  = [datos_seccion[c]['ref']  for c in cats]
    diffs = [abs(r - e) for r, e in zip(reals, refs)]

    x = np.arange(len(cats))
    w = 0.35

    barras_ref  = ax.bar(x - w/2, refs,  w, label='Referencia oficial',
                         color=C_REF,     alpha=0.85, edgecolor='white')
    barras_real = ax.bar(x + w/2, reals, w, label='Dataset sintético',
                         color=C_DATASET, alpha=0.85, edgecolor='white')

    for bar, diff in zip(barras_real, diffs):
        bar.set_edgecolor(color_barra(diff))
        bar.set_linewidth(2.5)

    for bar in barras_ref:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.005,
                f'{h:.1%}', ha='center', va='bottom', fontsize=7, color='#555')
    for bar, diff in zip(barras_real, diffs):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.005,
                f'{h:.1%}', ha='center', va='bottom', fontsize=7,
                color=color_barra(diff), fontweight='bold')

    ax.set_title(nombre, fontsize=9, fontweight='bold', color='#1A237E', pad=6)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=7, rotation=45, ha='right')
    ax.set_ylim(0, max(max(refs), max(reals)) * 1.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_facecolor(BG)
    if fuente:
        ax.text(0.99, 0.97, fuente, transform=ax.transAxes,
                fontsize=6, ha='right', va='top', color='#888', style='italic')


def generar_graficas(df, datos):
    ruta = os.path.join(config.DIR_OUTPUT, 'validacion_dataset.png')

    fig = plt.figure(figsize=(22, 30))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        'Validación del Dataset Sintético IMSS CDMX\n'
        'Comparación con Fuentes Oficiales',
        fontsize=16, fontweight='bold', color='#1A237E', y=0.99
    )

    gs = GridSpec(5, 3, figure=fig, hspace=0.65, wspace=0.38)

    # Fila 0
    ax1  = fig.add_subplot(gs[0, 0])
    ax2  = fig.add_subplot(gs[0, 1])
    ax3  = fig.add_subplot(gs[0, 2])
    # Fila 1
    ax4  = fig.add_subplot(gs[1, 0])
    ax5  = fig.add_subplot(gs[1, 1])
    ax6  = fig.add_subplot(gs[1, 2])
    # Fila 2
    ax7  = fig.add_subplot(gs[2, 0])
    ax8  = fig.add_subplot(gs[2, 1])
    ax9  = fig.add_subplot(gs[2, 2])
    # Fila 3 — derivados
    ax_dm = fig.add_subplot(gs[3, 0])
    ax_ht = fig.add_subplot(gs[3, 1])
    ax_err = fig.add_subplot(gs[3, 2])
    # Fila 4 — resumen global
    ax10 = fig.add_subplot(gs[4, :])

    graficar_comparacion('Sexo\n[DATO DIRECTO]',
                         datos['sexo'], ax1, 'Censo INEGI 2020')
    graficar_comparacion('Estado Nutricional\n[DATO DIRECTO]',
                         datos['nutricional'], ax2, 'ENSANUT 2018')
    graficar_comparacion('Actividad Física\n[DATO DIRECTO]',
                         datos['actividad'], ax3, 'MOPRADEF 2025')
    graficar_comparacion('Enfermedades Totales\n[DATO DIRECTO]',
                         datos['enfermedades'], ax4, 'ENSANUT 2022 / ENSA 2004')
    graficar_comparacion('Comorbilidades\n[DATO DIRECTO]',
                         datos['comorbilidades'], ax5, 'ENSA 2004 CDMX')
    graficar_comparacion('Tabaquismo\n[DATO DIRECTO]',
                         datos['tabaquismo'], ax6, 'ENSANUT 2022')
    graficar_comparacion('Alcoholismo\n[DATO DIRECTO]',
                         datos['alcoholismo'], ax7, 'ENSANUT 2022')
    graficar_comparacion('Antecedentes Heredofam.\n[DATO DIRECTO]',
                         datos['antecedentes'], ax8, 'ENSANUT 2012 / Gto 2022')

    # Panel 9 — error nutricional estratificado
    nut_strat = datos['nut_estratificado']
    if nut_strat:
        cats_s  = list(nut_strat.keys())
        diffs_s = [abs(nut_strat[c]['real'] - nut_strat[c]['ref']) for c in cats_s]
        colores = [color_barra(d) for d in diffs_s]
        y_pos   = np.arange(len(cats_s))
        ax9.barh(y_pos, diffs_s, color=colores, edgecolor='white', height=0.6)
        ax9.set_yticks(y_pos)
        ax9.set_yticklabels(cats_s, fontsize=6, rotation=45, ha='right')
        ax9.axvline(TOLERANCIA,     color=C_OK,   linestyle='--', alpha=0.7, lw=1.2, label='5% (OK)')
        ax9.axvline(TOLERANCIA * 2, color=C_WARN, linestyle='--', alpha=0.7, lw=1.2, label='10% (lím.)')
        ax9.set_title('Error absoluto\nNutricional estratificado (edad×sexo)\n[DATO DIRECTO]',
                      fontsize=9, fontweight='bold', color='#1A237E')
        ax9.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
        ax9.spines[['top', 'right']].set_visible(False)
        ax9.set_facecolor(BG)
        ax9.legend(fontsize=7)

    # Panel 10 — diabetes por edad DERIVADO
    graficar_comparacion(
        'Diabetes por edad\n[DERIVADO: RM ENSANUT 2016 → total 18.3% ENSANUT 2022]',
        datos['diabetes_edad'], ax_dm,
        'Estimación derivada — no tabla directa ENSANUT 2022')

    # Panel 11 — HTA por edad DERIVADO
    graficar_comparacion(
        'HTA por edad\n[DERIVADO: RP estimadas → total 29.4% ENSANUT 2022]',
        datos['hta_edad'], ax_ht,
        'Estimación derivada — no tabla directa ENSANUT 2022')

    # Panel 12 — error absoluto todas las variables
    todas_cats  = []
    todos_diffs = []
    for sec, items in datos.items():
        if sec == 'nut_estratificado':
            continue
        for cat, vals in items.items():
            label = cat.replace('\n', ' ')
            todas_cats.append(f"{sec}: {label}")
            todos_diffs.append(abs(vals['real'] - vals['ref']))

    orden     = np.argsort(todos_diffs)[::-1]
    cats_ord  = [todas_cats[i]  for i in orden]
    diffs_ord = [todos_diffs[i] for i in orden]
    cols_ord  = [color_barra(d) for d in diffs_ord]

    y_pos = np.arange(len(cats_ord))
    ax_err.barh(y_pos, diffs_ord, color=cols_ord, edgecolor='white', height=0.6)
    ax_err.set_yticks(y_pos)
    ax_err.set_yticklabels(cats_ord, fontsize=6, rotation=45, ha='right')
    ax_err.axvline(TOLERANCIA,     color=C_OK,   linestyle='--', alpha=0.8, lw=1.5, label='5% OK')
    ax_err.axvline(TOLERANCIA * 2, color=C_WARN, linestyle='--', alpha=0.8, lw=1.5, label='10% lím.')
    ax_err.set_title('Errores absolutos — todas las variables',
                     fontsize=9, fontweight='bold', color='#1A237E')
    ax_err.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
    ax_err.spines[['top', 'right']].set_visible(False)
    ax_err.set_facecolor(BG)
    ax_err.legend(fontsize=7)

    # Panel 13 — resumen global
    y_pos2 = np.arange(len(cats_ord))
    ax10.barh(y_pos2, diffs_ord, color=cols_ord, edgecolor='white', height=0.6)
    ax10.set_yticks(y_pos2)
    ax10.set_yticklabels(cats_ord, fontsize=7, rotation=45, ha='right')
    ax10.axvline(TOLERANCIA,     color=C_OK,   linestyle='--', alpha=0.8, lw=1.5, label='5% — OK')
    ax10.axvline(TOLERANCIA * 2, color=C_WARN, linestyle='--', alpha=0.8, lw=1.5, label='10% — Límite')
    ax10.set_title('Resumen — diferencias absolutas ordenadas de mayor a menor',
                   fontsize=11, fontweight='bold', color='#1A237E', pad=8)
    ax10.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
    ax10.spines[['top', 'right']].set_visible(False)
    ax10.set_facecolor(BG)
    ax10.legend(fontsize=9)

    # Leyenda global
    handles = [
        mpatches.Patch(color=C_REF,     label='Referencia oficial'),
        mpatches.Patch(color=C_DATASET, label='Dataset sintético'),
        mpatches.Patch(color=C_OK,      label='✓ OK  (diff ≤ 5%)'),
        mpatches.Patch(color=C_WARN,    label='~ Aceptable  (diff ≤ 10%)'),
        mpatches.Patch(color=C_ERROR,   label='✗ Revisar  (diff > 10%)'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=5,
               fontsize=9, bbox_to_anchor=(0.5, -0.01), framealpha=0.9)

    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f"\n  [✓] Gráfica guardada en: {ruta}")


# ===========================================================================
# MAIN
# ===========================================================================
def validar():
    df = pd.read_csv(config.SALIDA_CSV)
    df['grupo_edad']        = df['edad'].apply(grupo_edad)
    df['grupo_edad_amplio'] = df['edad'].apply(grupo_edad_amplio)

    print(f"\n  Cargando dataset: {len(df):,} pacientes...")
    datos = recolectar(df)
    imprimir_consola(datos)
    generar_graficas(df, datos)


if __name__ == "__main__":
    validar()