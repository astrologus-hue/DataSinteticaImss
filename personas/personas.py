# personas/personas.py
import os
import sys
import random
import unicodedata
from datetime import date, timedelta
import pandas as pd
from faker import Faker

# --- PARCHE DE RUTAS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config as config

import talla
import demografia
import edad
import enfermedades
import historia_clinica

# --- CARGA CATÁLOGO SEPOMEX ---
if config.RUTA_ZIPCODE.endswith('.csv'):
    zipcode = pd.read_csv(
        config.RUTA_ZIPCODE,
        dtype={
            'cp': str, 'c_estado': str, 'c_oficina': str, 'c_CP': str,
            'c_tipo_asenta': str, 'c_mnpio': str,
            'id_asenta_cpcons': str, 'c_cve_ciudad': str,
        }
    )
else:
    zipcode = pd.read_excel(config.RUTA_ZIPCODE, dtype=str)

print(f'  [personas] Total filas catálogo SEPOMEX: {len(zipcode):,}')

zipcode_cdmx   = zipcode[zipcode['c_estado'] == '09'].copy()
zipcode_cdmx['cp'] = zipcode_cdmx['cp'].astype(str).str.zfill(5)
pool_geo       = zipcode_cdmx[['cp', 'd_asenta', 'municipio', 'd_ciudad']].drop_duplicates().reset_index(drop=True)
pool_registros = pool_geo.to_dict(orient='records')

# --- LÓGICA CURP Y NSS ---
CLAVE_CURP_CDMX = 'DF'
CONSONANTES = 'BCDFGHJKLMNPQRSTVWXYZ'
VOCALES     = 'AEIOU'
ALFABETO    = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def normaliza(texto):
    if not isinstance(texto, str):
        return ''
    s = unicodedata.normalize('NFKD', texto)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.upper()

def primera_consonante_interna(palabra):
    for c in normaliza(palabra)[1:]:
        if c in CONSONANTES:
            return c
    return 'X'

def primera_vocal_interna(palabra):
    for c in normaliza(palabra)[1:]:
        if c in VOCALES:
            return c
    return 'X'

ALTISONANTES = {
    'BACA','BAKA','BUEI','BUEY','CACA','CACO','CAGA','CAGO','CAKA','CAKO',
    'COGE','COGI','COJA','COJE','COJI','COJO','COLA','CULO','FALO','FETO',
    'GETA','GUEI','GUEY','JETA','JOTO','KACA','KACO','KAGA','KAGO','KAKA',
    'KAKO','KOGE','KOGI','KOJA','KOJE','KOJI','KOJO','KOLA','KULO','LILO',
    'LOCA','LOCO','LOKA','LOKO','MAME','MAMO','MEAR','MEAS','MEON','MIAR',
    'MION','MOCO','MOKO','MULA','MULO','NACA','NACO','PEDA','PEDO','PENE',
    'PIPI','PITO','POPO','PUTA','PUTO','QULO','RATA','ROBA','ROBE','ROBO',
    'RUIN','SENO','TETA','VACA','VAGA','VAGO','VAKA','VUEI','VUEY','WUEI','WUEY'
}

def generar_curp_sintetico(nombre, primer_ap, segundo_ap, fecha_nac, sexo):
    p_ap = normaliza(primer_ap) or 'X'
    s_ap = normaliza(segundo_ap) or 'X'
    nom  = normaliza(nombre).split()[0] if nombre else 'X'

    l1 = p_ap[0] if p_ap else 'X'
    l2 = primera_vocal_interna(p_ap)
    l3 = s_ap[0] if s_ap else 'X'
    l4 = nom[0]  if nom  else 'X'

    if (l1 + l2 + l3 + l4) in ALTISONANTES:
        l2 = 'X'

    fecha_str  = fecha_nac.strftime('%y%m%d')
    sexo_letra = {'Masculino': 'H', 'Femenino': 'M'}.get(sexo, 'X')

    c1 = primera_consonante_interna(p_ap)
    c2 = primera_consonante_interna(s_ap)
    c3 = primera_consonante_interna(nom)

    homoclave   = random.choice('0123456789') if fecha_nac.year < 2000 else random.choice(ALFABETO)
    verificador = random.choice('0123456789')

    return f'{l1}{l2}{l3}{l4}{fecha_str}{sexo_letra}{CLAVE_CURP_CDMX}{c1}{c2}{c3}{homoclave}{verificador}'

def generar_nss():
    return ''.join(random.choices('0123456789', k=11))

# --- GENERACIÓN ---
random.seed(config.SEED)
Faker.seed(config.SEED)

fake = Faker('es_MX')
HOY  = date.today()

pacientes  = []
nss_usados = set()

print(f'  [personas] Generando {config.N_PACIENTES:,} registros sintéticos (rango {config.EDAD_MINIMA}-{config.EDAD_MAXIMA} años)...')

while len(pacientes) < config.N_PACIENTES:
    nss = generar_nss()
    if nss in nss_usados:
        continue
    nss_usados.add(nss)

    sexo = demografia.asignar_sexo()

    if sexo == 'Masculino':
        nombre = fake.first_name_male()
    elif sexo == 'Femenino':
        nombre = fake.first_name_female()
    else:
        nombre = fake.first_name()

    primer_apellido  = fake.last_name()
    segundo_apellido = fake.last_name() if random.random() < config.PROB_SEGUNDO_APELLIDO else None

    edad_anos = edad.asignar_edad(sexo)
    fecha_nac = HOY.replace(year=HOY.year - edad_anos) - timedelta(days=random.randint(0, 364))
    edad_val  = (HOY - fecha_nac).days // 365

    estatura_cm, imc, peso, estado_nutricional, actividad_fisica = \
        talla.calcular_antropometria(sexo, edad_val)

    # Enfermedades crónicas con comorbilidades
    enfs = enfermedades.asignar_enfermedades(
        edad_val, sexo, estado_nutricional, actividad_fisica
    )

    # Historia clínica — antecedentes heredofamiliares y no patológicos
    hc = historia_clinica.generar_historia_clinica(
        enfs['diabetes'], enfs['hipertension']
    )

    geo  = random.choice(pool_registros)
    curp = generar_curp_sintetico(
        nombre, primer_apellido, segundo_apellido or '', fecha_nac, sexo
    )

    pacientes.append({
        # --- Identificación ---
        'nss':                       nss,
        'curp_sintetico':            curp,
        'nombre':                    nombre,
        'primer_apellido':           primer_apellido,
        'segundo_apellido':          segundo_apellido,
        'fecha_nacimiento':          fecha_nac.strftime('%d/%m/%Y'),
        'edad':                      edad_val,
        'sexo':                      sexo,
        # --- Antropometría y estilo de vida ---
        'actividad_fisica':          actividad_fisica,
        'estatura_cm':               estatura_cm,
        'imc':                       imc,
        'peso_kg':                   peso,
        'estado_nutricional':        estado_nutricional,
        # --- Enfermedades crónicas ---
        'diabetes':                  enfs['diabetes'],
        'hipertension':              enfs['hipertension'],
        'dislipidemia':              enfs['dislipidemia'],
        'glucosa_inicial':           enfs['glucosa_inicial'],
        'hba1c_inicial':             enfs['hba1c_inicial'],
        'diagnosticado_dm':          enfs['diagnosticado_dm'],
        # --- Historia clínica ---
        'antecedente_familiar_dm2':  hc['antecedente_familiar_dm2'],
        'antecedente_familiar_hta':  hc['antecedente_familiar_hta'],
        'tabaquismo':                hc['tabaquismo'],
        'alcoholismo':               hc['alcoholismo'],
        # --- Geografía ---
        'entidad_federativa':        'CDMX',
        'municipio':                 geo['municipio'],
        'cp':                        geo['cp'],
        'colonia':                   geo['d_asenta'],
        'ciudad':                    geo['d_ciudad'],
    })

# --- EXPORTACIÓN ---
df_pacientes = pd.DataFrame(pacientes)
os.makedirs(config.DIR_OUTPUT, exist_ok=True)

df_pacientes.to_csv(config.SALIDA_CSV,    index=False, encoding='utf-8')
df_pacientes.to_excel(config.SALIDA_XLSX, index=False, engine='xlsxwriter')

print(f'\x1b[32m  [personas] Proceso finalizado con éxito.\x1b[0m')
print(f'  -> CSV:   {config.SALIDA_CSV}')
print(f'  -> Excel: {config.SALIDA_XLSX}')