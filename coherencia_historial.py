# revisar_coherencia.py
# Ejecutar desde la raiz del proyecto: python revisar_coherencia.py
"""
Revisor de Coherencia Médica — DM2 + HTA
Dataset Sintético IMSS CDMX

Revisa tres niveles de coherencia médica específicos para
Diabetes tipo 2 e Hipertensión arterial como comorbilidad:

NIVEL 1 — Valores individuales vs rangos NOM-015-SSA2 / JNC-8
    Cada medición debe estar dentro del rango clínico
    correcto para el estado del paciente.

NIVEL 2 — Coherencia entre variables (correlación clínica)
    HbA1c y glucosa deben ir en la misma dirección.
    Fórmula ADA: glucosa_estimada = 28.7 × HbA1c - 46.7

NIVEL 3 — Coherencia temporal (evolución clínica AR(1))
    No debe haber saltos imposibles entre visitas consecutivas.
    La HbA1c no puede contradecir la tendencia de glucosa.

Fuentes de referencia:
    NOM-015-SSA2-2010  — metas de control DM2 + HTA
    JNC-8              — criterios y metas HTA en diabéticos
    ADA 2023           — fórmula glucosa estimada desde HbA1c
    IMSS Guía GPC      — frecuencias y metas de control
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

# Colores consola
VERDE    = '\x1b[32m'
ROJO     = '\x1b[31m'
AMARILLO = '\x1b[33m'
RESET    = '\x1b[0m'
BOLD     = '\x1b[1m'

# Paleta gráficas
C_OK    = '#2E7D32'
C_WARN  = '#F9A825'
C_ERROR = '#C62828'
C_AZUL  = '#1A237E'
C_REF   = '#4FC3F7'
BG      = '#F8FAFD'


def sem(n, total, umbral_pct=0.05):
    """Semáforo por porcentaje de incoherencias."""
    pct = n / total if total > 0 else 0
    if pct <= umbral_pct:
        return f'{VERDE}✓ OK{RESET}', C_OK
    elif pct <= umbral_pct * 3:
        return f'{AMARILLO}~ REVISAR{RESET}', C_WARN
    return f'{ROJO}✗ INCOHERENTE{RESET}', C_ERROR


def imprimir_regla(codigo, descripcion, n_casos, total, detalle=None):
    icono, _ = sem(n_casos, total)
    pct = n_casos / total * 100 if total > 0 else 0
    print(f"  {icono}  {codigo} — {descripcion}")
    print(f"         {n_casos:,} casos ({pct:.2f}%)  de {total:,} visitas evaluadas")
    if detalle and n_casos > 0:
        print(f"         Muestra: {detalle}")


# ===========================================================================
# CARGAR DATOS
# ===========================================================================
def cargar():
    ruta_hist = os.path.join(config.DIR_OUTPUT, 'historial_medico.csv')
    if not os.path.exists(ruta_hist):
        print(f"\n{ROJO}ERROR: No se encuentra historial_medico.csv{RESET}")
        print("Ejecuta primero: python historial.py")
        sys.exit(1)

    df_pac = pd.read_csv(config.SALIDA_CSV)
    df_pac['nss'] = df_pac['nss'].astype(str).str.zfill(11)

    dh = pd.read_csv(ruta_hist)
    dh['nss'] = dh['nss'].astype(str).str.zfill(11)

    # Parsear fecha
    dh['fecha_dt'] = pd.to_datetime(dh['fecha_visita'], format='%d/%m/%Y')

    # Agregar estatura del CSV base para calcular IMC
    dh = dh.merge(
        df_pac[['nss','estatura_cm','diabetes','hipertension']],
        on='nss', how='left'
    )

    print(f"  Historial cargado: {len(dh):,} visitas | {dh['nss'].nunique():,} pacientes")
    return df_pac, dh


# ===========================================================================
# NIVEL 1 — VALORES INDIVIDUALES vs NOM-015-SSA2 / JNC-8
# ===========================================================================
def nivel_1(dh):
    print(f"\n{'='*70}")
    print(f"{BOLD}NIVEL 1 — VALORES INDIVIDUALES (NOM-015-SSA2 / JNC-8){RESET}")
    print("Cada medición debe estar en el rango correcto para su estado clínico.")
    print(f"{'='*70}\n")

    resultados = {}
    total = len(dh)

    # --- GLUCOSA ---
    print(f"{BOLD}Glucosa en ayuno:{RESET}")

    # R01: Sano con glucosa ≥ 126
    r01 = dh[(dh['estado_dm']=='Sano') & (dh['glucosa_ayuno_mgdl'] >= 126)]
    imprimir_regla('R01', 'Estado=Sano pero glucosa ≥ 126 mg/dL (criterio DM2, NOM-015)',
                   len(r01), total)
    resultados['R01'] = len(r01)

    # R02: DM_controlada con glucosa > 130
    r02 = dh[(dh['estado_dm']=='DM_controlada') & (dh['glucosa_ayuno_mgdl'] > 130)]
    imprimir_regla('R02', 'Estado=DM_controlada pero glucosa > 130 mg/dL (meta NOM-015)',
                   len(r02), total)
    resultados['R02'] = len(r02)

    # R03: DM_descontrolada con glucosa < 70
    r03 = dh[(dh['estado_dm']=='DM_descontrolada') & (dh['glucosa_ayuno_mgdl'] < 70)]
    imprimir_regla('R03', 'Estado=DM_descontrolada pero glucosa < 70 mg/dL (hipoglucemia)',
                   len(r03), total)
    resultados['R03'] = len(r03)

    # R04: glucosa imposible
    r04 = dh[(dh['glucosa_ayuno_mgdl'] < 40) | (dh['glucosa_ayuno_mgdl'] > 500)]
    imprimir_regla('R04', 'Glucosa fuera de rango fisiológico (< 40 o > 500 mg/dL)',
                   len(r04), total)
    resultados['R04'] = len(r04)

    # --- HbA1c ---
    lab = dh[dh['es_laboratorio']=='Sí'].copy()
    total_lab = len(lab)
    print(f"\n{BOLD}HbA1c (solo visitas con laboratorio — {total_lab:,}):{RESET}")

    # R05: DM_controlada con HbA1c ≥ 7%
    r05 = lab[(lab['estado_dm']=='DM_controlada') & (lab['hba1c_pct'] >= 7.0)]
    imprimir_regla('R05', 'Estado=DM_controlada pero HbA1c ≥ 7% (NOM-015 meta)',
                   len(r05), total_lab)
    resultados['R05'] = len(r05)

    # R06: Sano con HbA1c ≥ 6.5%
    r06 = lab[(lab['estado_dm']=='Sano') & (lab['hba1c_pct'] >= 6.5)]
    imprimir_regla('R06', 'Estado=Sano pero HbA1c ≥ 6.5% (criterio diagnóstico DM2)',
                   len(r06), total_lab)
    resultados['R06'] = len(r06)

    # R07: HbA1c imposible
    r07 = lab[(lab['hba1c_pct'] < 3.0) | (lab['hba1c_pct'] > 16.0)]
    imprimir_regla('R07', 'HbA1c fuera de rango fisiológico (< 3% o > 16%)',
                   len(r07), total_lab)
    resultados['R07'] = len(r07)

    # --- PRESIÓN ARTERIAL (metas específicas para DM2, JNC-8) ---
    print(f"\n{BOLD}Presión arterial — metas DM2+HTA más estrictas (JNC-8 / NOM-015):{RESET}")

    dm_hta = dh[(dh['diabetes']=='Sí') & (dh['hipertension']=='Sí')]
    total_dm_hta = len(dm_hta)
    print(f"  Visitas de pacientes DM2+HTA: {total_dm_hta:,}")

    # R08: TAS < TAD (imposible fisiológicamente)
    r08 = dh[dh['tas_mmhg'] < dh['tad_mmhg']]
    imprimir_regla('R08', 'TAS < TAD (sistólica menor que diastólica — imposible)',
                   len(r08), total)
    resultados['R08'] = len(r08)

    # R09: HTA_controlada con TAS ≥ 140 o TAD ≥ 90
    r09 = dh[(dh['estado_hta']=='HTA_controlada') &
             ((dh['tas_mmhg'] >= 140) | (dh['tad_mmhg'] >= 90))]
    imprimir_regla('R09', 'Estado=HTA_controlada pero TAS ≥ 140 o TAD ≥ 90 (JNC-8)',
                   len(r09), total)
    resultados['R09'] = len(r09)

    # R10: Sin_HTA con TAS ≥ 160 o TAD ≥ 100
    r10 = dh[(dh['estado_hta']=='Sin_HTA') &
             ((dh['tas_mmhg'] >= 160) | (dh['tad_mmhg'] >= 100))]
    imprimir_regla('R10', 'Estado=Sin_HTA pero TAS ≥ 160 o TAD ≥ 100 (HTA estadio 2)',
                   len(r10), total)
    resultados['R10'] = len(r10)

    # R11: Meta especial DM2+HTA: TAS > 130 mmHg
    if total_dm_hta > 0:
        r11 = dm_hta[dm_hta['tas_mmhg'] > 130]
        pct_r11 = len(r11) / total_dm_hta * 100
        icono, _ = sem(len(r11), total_dm_hta, umbral_pct=0.50)
        print(f"\n  {BOLD}Meta especial DM2+HTA (NOM-015 + JNC-8):{RESET}")
        print(f"  {icono}  R11 — Diabético+hipertenso con TAS > 130 mmHg")
        print(f"         {len(r11):,} visitas ({pct_r11:.1f}%) — meta es TAS ≤ 130")
        print(f"         (nota: esto incluye visitas de HTA_descontrolada, es esperado)")
        resultados['R11'] = len(r11)

    return resultados


# ===========================================================================
# NIVEL 2 — COHERENCIA ENTRE VARIABLES (correlación clínica)
# ===========================================================================
def nivel_2(dh):
    print(f"\n{'='*70}")
    print(f"{BOLD}NIVEL 2 — COHERENCIA ENTRE VARIABLES{RESET}")
    print("HbA1c debe ser coherente con el nivel de glucosa (fórmula ADA 2023).")
    print(f"{'='*70}\n")

    lab = dh[dh['es_laboratorio']=='Sí'].copy()
    total_lab = len(lab)

    # Glucosa estimada desde HbA1c — fórmula ADA 2023
    # glucosa_estimada (mg/dL) = 28.7 × HbA1c(%) - 46.7
    lab['glucosa_estimada_ada'] = 28.7 * lab['hba1c_pct'] - 46.7
    lab['diff_glucosa_hba1c']   = (lab['glucosa_ayuno_mgdl'] - lab['glucosa_estimada_ada']).abs()

    print(f"{BOLD}Coherencia Glucosa ↔ HbA1c (Fórmula ADA: G = 28.7×HbA1c - 46.7):{RESET}")
    print(f"  Total visitas con laboratorio: {total_lab:,}\n")

    # R12: diferencia > 50 mg/dL (incoherencia moderada)
    r12 = lab[lab['diff_glucosa_hba1c'] > 50]
    imprimir_regla('R12',
        'Glucosa y HbA1c inconsistentes (diff > 50 mg/dL vs glucosa estimada ADA)',
        len(r12), total_lab)

    # R13: diferencia > 100 mg/dL (incoherencia severa)
    r13 = lab[lab['diff_glucosa_hba1c'] > 100]
    imprimir_regla('R13',
        'Glucosa y HbA1c MUY inconsistentes (diff > 100 mg/dL) — incoherencia severa',
        len(r13), total_lab)

    # Estadístico: diferencia media por estado
    print(f"\n  {BOLD}Diferencia media glucosa_real vs glucosa_estimada_ADA por estado:{RESET}")
    resumen = lab.groupby('estado_dm')['diff_glucosa_hba1c'].agg(['mean','median','max']).round(1)
    resumen.columns = ['Media diff', 'Mediana diff', 'Max diff']
    print(resumen.to_string())
    print(f"\n  Referencia: diff < 30 mg/dL es excelente | < 50 aceptable | > 50 revisar")

    # R14: HbA1c sube pero glucosa bajó (contradicción temporal)
    # Solo para pacientes con diabetes — comparar visitas de lab consecutivas
    print(f"\n{BOLD}Contradicción temporal HbA1c ↔ glucosa:{RESET}")
    dm_lab = lab[lab['estado_dm'].isin(['DM_controlada','DM_descontrolada'])].copy()
    dm_lab = dm_lab.sort_values(['nss','fecha_dt'])

    dm_lab['hba1c_prev']   = dm_lab.groupby('nss')['hba1c_pct'].shift(1)
    dm_lab['glucosa_prev']  = dm_lab.groupby('nss')['glucosa_ayuno_mgdl'].shift(1)
    dm_lab['delta_hba1c']   = dm_lab['hba1c_pct'] - dm_lab['hba1c_prev']
    dm_lab['delta_glucosa'] = dm_lab['glucosa_ayuno_mgdl'] - dm_lab['glucosa_prev']

    # HbA1c subió >1% pero glucosa bajó >40 mg/dL
    r14 = dm_lab[
        (dm_lab['delta_hba1c'] > 1.0) &
        (dm_lab['delta_glucosa'] < -40) &
        dm_lab['hba1c_prev'].notna()
    ]
    total_pares = dm_lab['hba1c_prev'].notna().sum()
    imprimir_regla('R14',
        'HbA1c subió >1% pero glucosa bajó >40 mg/dL (contradicción temporal)',
        len(r14), total_pares)

    return {'R12': len(r12), 'R13': len(r13), 'R14': len(r14)}


# ===========================================================================
# NIVEL 3 — COHERENCIA TEMPORAL (saltos en el AR(1))
# ===========================================================================
def nivel_3(dh):
    print(f"\n{'='*70}")
    print(f"{BOLD}NIVEL 3 — COHERENCIA TEMPORAL (evolución AR(1)){RESET}")
    print("No debe haber saltos imposibles entre visitas consecutivas.")
    print(f"{'='*70}\n")

    dh_ord = dh.sort_values(['nss','fecha_dt']).copy()
    dh_ord['glucosa_prev'] = dh_ord.groupby('nss')['glucosa_ayuno_mgdl'].shift(1)
    dh_ord['tas_prev']     = dh_ord.groupby('nss')['tas_mmhg'].shift(1)
    dh_ord['peso_prev']    = dh_ord.groupby('nss')['peso_kg'].shift(1)
    dh_ord['dias_entre']   = dh_ord.groupby('nss')['fecha_dt'].diff().dt.days

    pares = dh_ord[dh_ord['glucosa_prev'].notna()].copy()
    total_pares = len(pares)

    print(f"{BOLD}Saltos en glucosa entre visitas consecutivas:{RESET}")

    # R15: Salto glucosa > 150 mg/dL en < 60 días
    r15 = pares[
        (pares['glucosa_ayuno_mgdl'] - pares['glucosa_prev']).abs() > 150
    ]
    imprimir_regla('R15',
        'Glucosa cambia > 150 mg/dL entre visitas consecutivas',
        len(r15), total_pares)

    # R16: Salto TAS > 60 mmHg entre visitas
    r16 = pares[
        (pares['tas_mmhg'] - pares['tas_prev']).abs() > 60
    ]
    imprimir_regla('R16',
        'TAS cambia > 60 mmHg entre visitas consecutivas',
        len(r16), total_pares)

    # R17: Peso cambia > 10 kg entre visitas
    r17 = pares[
        (pares['peso_kg'] - pares['peso_prev']).abs() > 10
    ]
    imprimir_regla('R17',
        'Peso cambia > 10 kg entre visitas consecutivas',
        len(r17), total_pares)

    # Estadísticos de cambio entre visitas
    print(f"\n{BOLD}Estadísticos de cambio entre visitas consecutivas:{RESET}")
    delta_g = (pares['glucosa_ayuno_mgdl'] - pares['glucosa_prev']).abs()
    delta_t = (pares['tas_mmhg'] - pares['tas_prev']).abs()
    delta_p = (pares['peso_kg'] - pares['peso_prev']).abs()

    print(f"  Glucosa: media={delta_g.mean():.1f}  p95={delta_g.quantile(.95):.1f}  max={delta_g.max():.1f} mg/dL")
    print(f"  TAS:     media={delta_t.mean():.1f}  p95={delta_t.quantile(.95):.1f}  max={delta_t.max():.1f} mmHg")
    print(f"  Peso:    media={delta_p.mean():.1f}  p95={delta_p.quantile(.95):.1f}  max={delta_p.max():.1f} kg")
    print(f"\n  Referencia glucosa: cambio < 30 mg/dL entre visitas es normal")
    print(f"  Referencia TAS:     cambio < 20 mmHg entre visitas es normal")

    # Distribución de días entre visitas
    print(f"\n{BOLD}Distribución de intervalos entre visitas:{RESET}")
    print(f"  Media:   {pares['dias_entre'].mean():.1f} días")
    print(f"  Mediana: {pares['dias_entre'].median():.1f} días")
    print(f"  Min:     {pares['dias_entre'].min():.0f} días")
    print(f"  Max:     {pares['dias_entre'].max():.0f} días")
    print(f"  P25-P75: {pares['dias_entre'].quantile(.25):.0f} – {pares['dias_entre'].quantile(.75):.0f} días")

    return {'R15': len(r15), 'R16': len(r16), 'R17': len(r17)}


# ===========================================================================
# GRÁFICAS
# ===========================================================================
def generar_graficas(dh, res_n1, res_n2, res_n3):
    ruta = os.path.join(config.DIR_OUTPUT, 'coherencia_medica.png')
    lab  = dh[dh['es_laboratorio']=='Sí'].copy()

    fig = plt.figure(figsize=(20, 22))
    fig.patch.set_facecolor(BG)
    fig.suptitle(
        'Coherencia Médica del Historial Sintético — DM2 + HTA\n'
        'IMSS CDMX — NOM-015-SSA2 / JNC-8 / ADA 2023',
        fontsize=15, fontweight='bold', color=C_AZUL, y=0.99
    )
    gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.55, wspace=0.38)

    # --- Panel 1: Resumen de incoherencias por nivel ---
    ax1 = fig.add_subplot(gs[0, :])
    todas = {**res_n1, **res_n2, **res_n3}
    total_vis = len(dh)
    cats  = list(todas.keys())
    vals  = [v/total_vis*100 for v in todas.values()]
    colores = [C_OK if v<=5 else (C_WARN if v<=15 else C_ERROR) for v in vals]

    bars = ax1.bar(cats, vals, color=colores, edgecolor='white', alpha=0.85)
    for bar, v in zip(bars, vals):
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                 f'{v:.1f}%', ha='center', va='bottom', fontsize=8,
                 color=bar.get_facecolor(), fontweight='bold')
    ax1.axhline(5,  color=C_OK,    linestyle='--', lw=1.2, alpha=0.7, label='5% OK')
    ax1.axhline(15, color=C_WARN,  linestyle='--', lw=1.2, alpha=0.7, label='15% Revisar')
    ax1.set_title('Resumen — % de incoherencias por regla',
                  fontsize=11, fontweight='bold', color=C_AZUL, pad=8)
    ax1.set_ylabel('% del total de visitas')
    ax1.spines[['top','right']].set_visible(False)
    ax1.set_facecolor(BG)
    ax1.legend(fontsize=9)

    # --- Panel 2: Distribución glucosa por estado DM ---
    ax2 = fig.add_subplot(gs[1, 0])
    estados_dm = ['Sano','Prediabetes','DM_controlada','DM_descontrolada']
    colores_dm = [C_OK, C_WARN, C_REF, C_ERROR]
    for estado, color in zip(estados_dm, colores_dm):
        sub = dh[dh['estado_dm']==estado]['glucosa_ayuno_mgdl']
        if len(sub) > 0:
            ax2.hist(sub, bins=30, alpha=0.6, color=color, label=estado, edgecolor='white')
    ax2.axvline(70,  color='gray',  linestyle=':', lw=1)
    ax2.axvline(100, color=C_WARN,  linestyle='--', lw=1.2, label='100 (NOM)')
    ax2.axvline(126, color=C_ERROR, linestyle='--', lw=1.2, label='126 (DM)')
    ax2.axvline(130, color=C_AZUL,  linestyle='--', lw=1.2, label='130 (meta ctrl)')
    ax2.set_title('Glucosa por estado DM\n(NOM-015-SSA2)',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax2.set_xlabel('mg/dL')
    ax2.legend(fontsize=6)
    ax2.spines[['top','right']].set_visible(False)
    ax2.set_facecolor(BG)

    # --- Panel 3: Distribución HbA1c por estado DM ---
    ax3 = fig.add_subplot(gs[1, 1])
    for estado, color in zip(estados_dm, colores_dm):
        sub = lab[lab['estado_dm']==estado]['hba1c_pct']
        if len(sub) > 0:
            ax3.hist(sub, bins=25, alpha=0.6, color=color, label=estado, edgecolor='white')
    ax3.axvline(5.7, color=C_WARN,  linestyle='--', lw=1.2, label='5.7% (prediab)')
    ax3.axvline(6.5, color=C_ERROR, linestyle='--', lw=1.2, label='6.5% (DM)')
    ax3.axvline(7.0, color=C_AZUL,  linestyle='--', lw=1.2, label='7% (meta ctrl)')
    ax3.set_title('HbA1c por estado DM\n(NOM-015-SSA2)',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax3.set_xlabel('%')
    ax3.legend(fontsize=6)
    ax3.spines[['top','right']].set_visible(False)
    ax3.set_facecolor(BG)

    # --- Panel 4: Distribución TAS por estado HTA ---
    ax4 = fig.add_subplot(gs[1, 2])
    estados_hta = ['Sin_HTA','HTA_controlada','HTA_descontrolada']
    colores_hta = [C_OK, C_WARN, C_ERROR]
    for estado, color in zip(estados_hta, colores_hta):
        sub = dh[dh['estado_hta']==estado]['tas_mmhg']
        if len(sub) > 0:
            ax4.hist(sub, bins=30, alpha=0.6, color=color, label=estado, edgecolor='white')
    ax4.axvline(130, color=C_AZUL,  linestyle='--', lw=1.2, label='130 (meta DM2+HTA)')
    ax4.axvline(140, color=C_ERROR, linestyle='--', lw=1.2, label='140 (HTA criterio)')
    ax4.set_title('TAS por estado HTA\n(JNC-8 / NOM-015)',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax4.set_xlabel('mmHg')
    ax4.legend(fontsize=6)
    ax4.spines[['top','right']].set_visible(False)
    ax4.set_facecolor(BG)

    # --- Panel 5: Glucosa real vs glucosa estimada por HbA1c (ADA) ---
    ax5 = fig.add_subplot(gs[2, 0:2])
    lab_dm = lab[lab['estado_dm'].isin(['DM_controlada','DM_descontrolada'])].sample(
        min(2000, len(lab)), random_state=42)
    lab_dm['glucosa_est'] = 28.7 * lab_dm['hba1c_pct'] - 46.7
    ax5.scatter(lab_dm['glucosa_est'], lab_dm['glucosa_ayuno_mgdl'],
                alpha=0.2, s=8, color=C_AZUL)
    lims = [40, 400]
    ax5.plot(lims, lims, 'r--', lw=1.5, label='Perfecta coherencia')
    ax5.fill_between(lims,
                     [l-50 for l in lims], [l+50 for l in lims],
                     alpha=0.1, color=C_OK, label='Rango ±50 mg/dL (aceptable)')
    ax5.set_xlim(40, 400)
    ax5.set_ylim(40, 400)
    ax5.set_xlabel('Glucosa estimada desde HbA1c — ADA (mg/dL)')
    ax5.set_ylabel('Glucosa real en visita (mg/dL)')
    ax5.set_title('Coherencia Glucosa ↔ HbA1c\n(Fórmula ADA 2023: G = 28.7×HbA1c - 46.7)',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax5.legend(fontsize=8)
    ax5.spines[['top','right']].set_visible(False)
    ax5.set_facecolor(BG)

    # --- Panel 6: Distribución de días entre visitas ---
    ax6 = fig.add_subplot(gs[2, 2])
    dh_ord = dh.sort_values(['nss','fecha_dt'])
    dias_entre = dh_ord.groupby('nss')['fecha_dt'].diff().dt.days.dropna()
    ax6.hist(dias_entre, bins=40, color=C_AZUL, alpha=0.8, edgecolor='white')
    ax6.axvline(60,  color=C_ERROR, linestyle='--', lw=1.2, label='60d (DM descontrol)')
    ax6.axvline(90,  color=C_WARN,  linestyle='--', lw=1.2, label='90d (DM control)')
    ax6.axvline(180, color=C_OK,    linestyle='--', lw=1.2, label='180d (prediab)')
    ax6.set_title('Intervalo entre visitas\n(NOM-015-SSA2)',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax6.set_xlabel('Días entre visitas')
    ax6.legend(fontsize=7)
    ax6.spines[['top','right']].set_visible(False)
    ax6.set_facecolor(BG)

    # --- Panel 7: Evolución glucosa media por año ---
    ax7 = fig.add_subplot(gs[3, 0])
    evol = dh.groupby(['anio_seguimiento','estado_dm'])['glucosa_ayuno_mgdl'].mean().unstack()
    for col in evol.columns:
        ax7.plot(evol.index, evol[col], marker='o', markersize=4, label=col)
    ax7.axhline(130, color='gray', linestyle='--', lw=1, alpha=0.7)
    ax7.set_title('Glucosa media por año y estado DM',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax7.set_xlabel('Año de seguimiento')
    ax7.set_ylabel('Glucosa (mg/dL)')
    ax7.legend(fontsize=7)
    ax7.spines[['top','right']].set_visible(False)
    ax7.set_facecolor(BG)

    # --- Panel 8: Evolución TAS media por año ---
    ax8 = fig.add_subplot(gs[3, 1])
    evol_tas = dh.groupby(['anio_seguimiento','estado_hta'])['tas_mmhg'].mean().unstack()
    for col in evol_tas.columns:
        ax8.plot(evol_tas.index, evol_tas[col], marker='o', markersize=4, label=col)
    ax8.axhline(130, color=C_AZUL, linestyle='--', lw=1, alpha=0.7, label='130 meta DM+HTA')
    ax8.axhline(140, color=C_ERROR, linestyle='--', lw=1, alpha=0.7, label='140 HTA criterio')
    ax8.set_title('TAS media por año y estado HTA',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax8.set_xlabel('Año de seguimiento')
    ax8.set_ylabel('TAS (mmHg)')
    ax8.legend(fontsize=7)
    ax8.spines[['top','right']].set_visible(False)
    ax8.set_facecolor(BG)

    # --- Panel 9: Evolución distribución estados DM por año ---
    ax9 = fig.add_subplot(gs[3, 2])
    dist = dh.groupby(['anio_seguimiento','estado_dm']).size().unstack(fill_value=0)
    dist_pct = dist.div(dist.sum(axis=1), axis=0) * 100
    colores_apil = [C_OK, C_WARN, C_REF, C_ERROR]
    bottom = np.zeros(len(dist_pct))
    for i, col in enumerate(dist_pct.columns):
        ax9.bar(dist_pct.index, dist_pct[col], bottom=bottom,
                color=colores_apil[i % len(colores_apil)], label=col,
                alpha=0.85, edgecolor='white')
        bottom += dist_pct[col].values
    ax9.set_title('Distribución estados DM por año',
                  fontsize=10, fontweight='bold', color=C_AZUL)
    ax9.set_xlabel('Año de seguimiento')
    ax9.set_ylabel('%')
    ax9.legend(fontsize=7, loc='upper right')
    ax9.spines[['top','right']].set_visible(False)
    ax9.set_facecolor(BG)

    plt.savefig(ruta, dpi=150, bbox_inches='tight', facecolor=BG)
    print(f"\n  [✓] Gráfica guardada en: {ruta}")


# ===========================================================================
# RESUMEN FINAL
# ===========================================================================
def resumen_final(res_n1, res_n2, res_n3, total_vis):
    print(f"\n{'='*70}")
    print(f"{BOLD}RESUMEN FINAL{RESET}")
    print(f"{'='*70}")

    todos = {**res_n1, **res_n2, **res_n3}
    total_incoherencias = sum(todos.values())
    pct_total = total_incoherencias / total_vis * 100

    print(f"\n  Total visitas analizadas:     {total_vis:,}")
    print(f"  Total incoherencias:          {total_incoherencias:,}  ({pct_total:.2f}%)")

    print(f"\n  Por nivel:")
    print(f"    Nivel 1 (valores individuales): {sum(res_n1.values()):,}")
    print(f"    Nivel 2 (glucosa ↔ HbA1c):      {sum(res_n2.values()):,}")
    print(f"    Nivel 3 (saltos temporales):     {sum(res_n3.values()):,}")

    if pct_total < 5:
        print(f"\n  {VERDE}✓ Dataset médicamente coherente (< 5% incoherencias){RESET}")
    elif pct_total < 15:
        print(f"\n  {AMARILLO}~ Coherencia aceptable — revisar reglas con más incoherencias{RESET}")
    else:
        print(f"\n  {ROJO}✗ Dataset con incoherencias significativas — revisar historial.py{RESET}")

    print(f"\n  Leyenda:")
    print(f"  {VERDE}✓ OK{RESET}        ≤ 5% de incoherencias")
    print(f"  {AMARILLO}~ REVISAR{RESET}   ≤ 15%")
    print(f"  {ROJO}✗ INCOHERENTE{RESET} > 15%")
    print("="*70)


# ===========================================================================
# MAIN
# ===========================================================================
def revisar():
    print("="*70)
    print(f"{BOLD} REVISIÓN DE COHERENCIA MÉDICA — DM2 + HTA{RESET}")
    print(" NOM-015-SSA2 / JNC-8 / ADA 2023 / IMSS CDMX")
    print("="*70)

    df_pac, dh = cargar()

    res_n1 = nivel_1(dh)
    res_n2 = nivel_2(dh)
    res_n3 = nivel_3(dh)

    generar_graficas(dh, res_n1, res_n2, res_n3)
    resumen_final(res_n1, res_n2, res_n3, len(dh))


if __name__ == "__main__":
    revisar()