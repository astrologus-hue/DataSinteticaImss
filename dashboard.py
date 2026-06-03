# dashboard_estadisticas.py
# Ejecutar desde la raiz del proyecto: python dashboard_estadisticas.py
# Requiere: pip install pandas matplotlib seaborn

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

# --- CARGA DE DATOS ---
df = pd.read_csv(config.SALIDA_CSV)
print(f"Total registros: {len(df):,}")
print("\n--- Distribución de diabetes ---")
print(df['diabetes'].value_counts())
print("\n--- Diabetes por estado nutricional y actividad ---")
print(
    df.groupby(['estado_nutricional', 'actividad_fisica'])['diabetes']
    .value_counts(normalize=True)
    .round(2)
)

# --- PALETA DE COLORES ---
COLOR_ACTIVO     = '#4FC3F7'
COLOR_SEDENTARIO = '#1A237E'
COLOR_SI         = '#1A237E'
COLOR_NO         = '#4FC3F7'
COLOR_FEM        = '#90CAF9'
COLOR_MAS        = '#1565C0'
COLOR_OTRO       = '#B0BEC5'
COLOR_DESC       = '#CFD8DC'
BG               = '#F8FAFD'

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.patch.set_facecolor(BG)
fig.suptitle(
    'Dashboard de Estadísticas — Datos Sintéticos IMSS CDMX',
    fontsize=16, fontweight='bold', y=0.98, color='#1A237E'
)

# =========================================================================
# GRÁFICA 1 — Estado nutricional × actividad física (barras apiladas 100%)
# =========================================================================
ax1 = axes[0, 0]
ax1.set_facecolor(BG)

orden_estados = ['Obesidad', 'Normal', 'Sobrepeso']
ct = pd.crosstab(
    df['estado_nutricional'],
    df['actividad_fisica'],
    normalize='index'
).reindex(orden_estados) * 100

ct[['Activo', 'Sedentario']].plot(
    kind='bar', stacked=True, ax=ax1,
    color=[COLOR_ACTIVO, COLOR_SEDENTARIO],
    edgecolor='white', linewidth=0.5, width=0.5
)
ax1.set_title('Estado nutricional por actividad física', fontweight='bold', color='#1A237E')
ax1.set_xlabel('Estado nutricional', labelpad=8)
ax1.set_ylabel('Porcentaje (%)')
ax1.set_ylim(0, 110)
ax1.set_xticklabels(orden_estados, rotation=0)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.0f}%'))
ax1.legend(['Activo', 'Sedentario'], loc='upper right', framealpha=0.9)
ax1.spines[['top', 'right']].set_visible(False)

# Etiquetas dentro de barras
for container in ax1.containers:
    for bar in container:
        h = bar.get_height()
        if h > 5:
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + h / 2,
                f'{h:.1f}%',
                ha='center', va='center',
                fontsize=9, color='white', fontweight='bold'
            )

# =========================================================================
# GRÁFICA 2 — Suma NSS por sexo
# =========================================================================
ax2 = axes[0, 1]
ax2.set_facecolor(BG)

conteo_sexo = df['sexo'].value_counts()
colores_sexo = {
    'Femenino':    COLOR_FEM,
    'Masculino':   COLOR_MAS,
    'Otro':        COLOR_OTRO,
    'Desconocido': COLOR_DESC
}
colores_barras = [colores_sexo.get(s, COLOR_OTRO) for s in conteo_sexo.index]

bars = ax2.bar(
    conteo_sexo.index, conteo_sexo.values,
    color=colores_barras, edgecolor='white', linewidth=0.5, width=0.5
)
ax2.set_title('Distribución por sexo', fontweight='bold', color='#1A237E')
ax2.set_xlabel('Sexo', labelpad=8)
ax2.set_ylabel('Número de pacientes')
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax2.spines[['top', 'right']].set_visible(False)

for bar in bars:
    h = bar.get_height()
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        h + 30, f'{h:,}',
        ha='center', va='bottom', fontsize=9, color='#1A237E'
    )

# =========================================================================
# GRÁFICA 3 — Diabetes (barras horizontales con actividad física)
# =========================================================================
ax3 = axes[1, 0]
ax3.set_facecolor(BG)

ct_dm = pd.crosstab(df['diabetes'], df['actividad_fisica'])
ct_dm = ct_dm.reindex(['Sí', 'No'])

ct_dm[['Activo', 'Sedentario']].plot(
    kind='barh', stacked=True, ax=ax3,
    color=[COLOR_ACTIVO, COLOR_SEDENTARIO],
    edgecolor='white', linewidth=0.5
)
ax3.set_title('Diabetes por actividad física', fontweight='bold', color='#1A237E')
ax3.set_xlabel('Número de pacientes')
ax3.set_ylabel('Diabetes')
ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))
ax3.legend(['Activo', 'Sedentario'], loc='lower right', framealpha=0.9)
ax3.spines[['top', 'right']].set_visible(False)

for container in ax3.containers:
    for bar in container:
        w = bar.get_width()
        if w > 100:
            ax3.text(
                bar.get_x() + w / 2,
                bar.get_y() + bar.get_height() / 2,
                f'{int(w):,}',
                ha='center', va='center',
                fontsize=9, color='white', fontweight='bold'
            )

# =========================================================================
# GRÁFICA 4 — Diabetes por estado nutricional y actividad (heatmap %)
# =========================================================================
ax4 = axes[1, 1]
ax4.set_facecolor(BG)

pivot = df[df['diabetes'] == 'Sí'].groupby(
    ['estado_nutricional', 'actividad_fisica']
).size().unstack(fill_value=0)

pivot_pct = (
    pivot.div(
        df.groupby(['estado_nutricional', 'actividad_fisica']).size().unstack(fill_value=1)
    ) * 100
).round(1)

sns.heatmap(
    pivot_pct,
    ax=ax4,
    annot=True,
    fmt='.1f',
    cmap='Blues',
    linewidths=0.5,
    linecolor='white',
    cbar_kws={'label': '% con diabetes'},
    annot_kws={'size': 11, 'weight': 'bold'}
)
ax4.set_title('% con diabetes por estado nutricional y actividad', fontweight='bold', color='#1A237E')
ax4.set_xlabel('Actividad física', labelpad=8)
ax4.set_ylabel('Estado nutricional')
ax4.tick_params(axis='x', rotation=0)
ax4.tick_params(axis='y', rotation=0)

# --- GUARDAR ---
plt.tight_layout(rect=[0, 0, 1, 0.96])
ruta_salida = os.path.join(config.DIR_OUTPUT, 'dashboard_estadisticas.png')
plt.savefig(ruta_salida, dpi=150, bbox_inches='tight', facecolor=BG)
print(f"\n[✓] Dashboard guardado en: {ruta_salida}")
plt.show()