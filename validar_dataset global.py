# validar_dataset.py
# Ejecutar desde la raiz del proyecto: python validar_dataset.py
# Compara las distribuciones del dataset sintético contra las fuentes oficiales.
"""
Validador del Dataset Sintético — IMSS CDMX
Compara cada variable del CSV contra el valor reportado en la fuente oficial.

Fuentes de referencia:
    Censo INEGI 2020         — sexo, edad
    ENSANUT 2018             — estado nutricional
    MOPRADEF 2025            — actividad física
    ENSANUT 2022             — diabetes, hipertensión, prediabetes
    ENSA 2004 CDMX           — dislipidemia, comorbilidades
    ENSANUT 2022             — tabaquismo, alcoholismo
    ENSANUT 2012             — antecedentes heredofamiliares
"""
import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

# Colores para la consola
VERDE  = '\x1b[32m'
ROJO   = '\x1b[31m'
AMARILLO = '\x1b[33m'
RESET  = '\x1b[0m'
BOLD   = '\x1b[1m'

TOLERANCIA = 0.05   # ±5 puntos porcentuales se considera aceptable

def check(nombre, valor_real, valor_esperado, fuente, tolerancia=TOLERANCIA):
    """Imprime el resultado de una validación con color."""
    diff = abs(valor_real - valor_esperado)
    if diff <= tolerancia:
        estado = f'{VERDE}✓ OK{RESET}'
    elif diff <= tolerancia * 2:
        estado = f'{AMARILLO}~ ACEPTABLE{RESET}'
    else:
        estado = f'{ROJO}✗ REVISAR{RESET}'

    print(f"  {estado}  {nombre}")
    print(f"         Dataset: {valor_real:.1%}  |  Esperado: {valor_esperado:.1%}  |  Diff: {diff:.1%}  |  [{fuente}]")


def validar():
    print("=" * 70)
    print(f"{BOLD} VALIDACIÓN DEL DATASET SINTÉTICO — IMSS CDMX{RESET}")
    print("=" * 70)

    df = pd.read_csv(config.SALIDA_CSV)
    n  = len(df)
    print(f"\n  Total pacientes: {n:,}\n")

    # ==================================================================
    # 1. SEXO — Censo INEGI 2020 CDMX
    # ==================================================================
    print(f"{BOLD}1. DISTRIBUCIÓN POR SEXO — Censo INEGI 2020 CDMX{RESET}")
    sexo = df['sexo'].value_counts(normalize=True)
    check('Femenino',    sexo.get('Femenino',0),   0.522, 'Censo INEGI 2020')
    check('Masculino',   sexo.get('Masculino',0),  0.478, 'Censo INEGI 2020')

    # ==================================================================
    # 2. EDAD — Censo INEGI 2020 CDMX
    # ==================================================================
    print(f"\n{BOLD}2. DISTRIBUCIÓN DE EDAD — Censo INEGI 2020 CDMX{RESET}")
    grupos_edad = pd.cut(df['edad'],
        bins=[18,29,39,49,59,75],
        labels=['18-29','30-39','40-49','50-59','60-75'],
        right=True
    ).value_counts(normalize=True).sort_index()
    # Proporciones esperadas del Censo (rango 18-75 normalizado)
    esperado_edad = {'18-29': 0.268, '30-39': 0.220, '40-49': 0.209,
                     '50-59': 0.178, '60-75': 0.125}
    for g, esp in esperado_edad.items():
        check(f'Grupo {g}', grupos_edad.get(g, 0), esp, 'Censo INEGI 2020')

    # ==================================================================
    # 3. ESTADO NUTRICIONAL — ENSANUT 2018
    # ==================================================================
    print(f"\n{BOLD}3. ESTADO NUTRICIONAL — ENSANUT 2018{RESET}")
    nut = df['estado_nutricional'].value_counts(normalize=True)
    # Promedio ponderado ENSANUT 2018 para población 18-75
    check('Normal',    nut.get('Normal',0),    0.26, 'ENSANUT 2018')
    check('Sobrepeso', nut.get('Sobrepeso',0), 0.39, 'ENSANUT 2018')
    check('Obesidad',  nut.get('Obesidad',0),  0.35, 'ENSANUT 2018')

    # ==================================================================
    # 4. ACTIVIDAD FÍSICA — MOPRADEF 2025
    # ==================================================================
    print(f"\n{BOLD}4. ACTIVIDAD FÍSICA — MOPRADEF 2025{RESET}")
    act = df['actividad_fisica'].value_counts(normalize=True)
    check('Activo',     act.get('Activo',0),     0.417, 'MOPRADEF 2025')
    check('Sedentario', act.get('Sedentario',0), 0.583, 'MOPRADEF 2025')

    # ==================================================================
    # 5. ENFERMEDADES CRÓNICAS — ENSANUT 2022 + ENSA 2004
    # ==================================================================
    print(f"\n{BOLD}5. ENFERMEDADES CRÓNICAS{RESET}")
    check('Diabetes',     (df['diabetes']=='Sí').mean(),     0.183, 'ENSANUT 2022')
    check('Hipertensión', (df['hipertension']=='Sí').mean(), 0.294, 'ENSANUT 2022')
    check('Dislipidemia', (df['dislipidemia']=='Sí').mean(), 0.433, 'ENSA 2004 CDMX')

    # ==================================================================
    # 6. COMORBILIDADES — ENSA 2004 CDMX
    # ==================================================================
    print(f"\n{BOLD}6. COMORBILIDADES (sobre diabéticos){RESET}")
    dm2 = df[df['diabetes'] == 'Sí']
    if len(dm2) > 0:
        check('HTA dado DM2',
              (dm2['hipertension']=='Sí').mean(), 0.46,  'ENSA 2004 CDMX')
        check('Dislipidemia dado DM2',
              (dm2['dislipidemia']=='Sí').mean(), 0.552, 'ENSA 2004 CDMX')

    hta_sin_dm2 = df[(df['hipertension']=='Sí') & (df['diabetes']=='No')]
    if len(hta_sin_dm2) > 0:
        check('Dislipidemia dado HTA sin DM2',
              (hta_sin_dm2['dislipidemia']=='Sí').mean(), 0.525, 'ENSA 2004 CDMX')

    # ==================================================================
    # 7. TABAQUISMO — ENSANUT 2022
    # ==================================================================
    print(f"\n{BOLD}7. TABAQUISMO — ENSANUT Continua 2022{RESET}")
    tab = df['tabaquismo'].value_counts(normalize=True)
    check('Activo',     tab.get('Activo',0),     0.195, 'ENSANUT 2022')
    check('Ex-fumador', tab.get('Ex-fumador',0), 0.178, 'ENSANUT 2022')
    check('Nunca',      tab.get('Nunca',0),       0.627, 'ENSANUT 2022')

    # ==================================================================
    # 8. ALCOHOLISMO — ENSANUT 2022
    # ==================================================================
    print(f"\n{BOLD}8. ALCOHOLISMO — ENSANUT Continua 2022{RESET}")
    alc = df['alcoholismo'].value_counts(normalize=True)
    check('No consume', alc.get('No consume',0), 0.445, 'ENSANUT 2022')
    check('Consume',    alc.get('Consume',0),    0.331, 'ENSANUT 2022')
    check('Excesivo',   alc.get('Excesivo',0),   0.224, 'ENSANUT 2022')

    # ==================================================================
    # 9. ANTECEDENTES HEREDOFAMILIARES — ENSANUT 2012
    # ==================================================================
    print(f"\n{BOLD}9. ANTECEDENTES HEREDOFAMILIARES{RESET}")
    check('Antec. familiar DM2 (población general)',
          (df['antecedente_familiar_dm2']=='Sí').mean(), 0.318, 'ENSANUT Gto 2022')
    check('Antec. familiar HTA (población general)',
          (df['antecedente_familiar_hta']=='Sí').mean(), 0.314, 'ENSANUT Gto 2022')

    # Verificar coherencia: diabéticos deben tener más antecedente familiar
    dm2_con_antec = (dm2['antecedente_familiar_dm2']=='Sí').mean() if len(dm2) > 0 else 0
    check('Antec. familiar DM2 en diabéticos',
          dm2_con_antec, 0.5446, 'ENSANUT 2012')

    # ==================================================================
    # 10. VALORES INICIALES CLÍNICOS — NOM-015-SSA2
    # ==================================================================
    print(f"\n{BOLD}10. VALORES INICIALES CLÍNICOS — NOM-015-SSA2{RESET}")
    print(f"  Glucosa inicial (todos):")
    print(f"    Media:  {df['glucosa_inicial'].mean():.1f} mg/dL")
    print(f"    Mediana:{df['glucosa_inicial'].median():.1f} mg/dL")
    print(f"    Min:    {df['glucosa_inicial'].min():.1f}  |  Max: {df['glucosa_inicial'].max():.1f}")
    if len(dm2) > 0:
        print(f"  Glucosa inicial (diabéticos):")
        print(f"    Media:  {dm2['glucosa_inicial'].mean():.1f} mg/dL  (esperado >126 NOM-015)")
        print(f"  HbA1c inicial (diabéticos):")
        print(f"    Media:  {dm2['hba1c_inicial'].mean():.1f}%  (esperado >6.5% NOM-015)")

    # ==================================================================
    # RESUMEN FINAL
    # ==================================================================
    print(f"\n{'=' * 70}")
    print(f"{BOLD} LEYENDA:{RESET}")
    print(f"  {VERDE}✓ OK{RESET}         → diferencia ≤ {TOLERANCIA:.0%}")
    print(f"  {AMARILLO}~ ACEPTABLE{RESET} → diferencia ≤ {TOLERANCIA*2:.0%}")
    print(f"  {ROJO}✗ REVISAR{RESET}   → diferencia > {TOLERANCIA*2:.0%}")
    print("=" * 70)


if __name__ == "__main__":
    validar()



    