# personas/personas.py
import os
import sys
import random
import unicodedata
from datetime import date
import pandas as pd
from faker import Faker

# --- PARCHE DE RUTAS PARA SUB-CARPETA ---
# Añade la carpeta raíz (..) al entorno de búsqueda de Python para encontrar config.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config as config
from personas import talla

# --- CARGA Y LIMPIEZA DE ARCHIVO DE CÓDIGOS POSTALES ---
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

print(f'Total filas catálogo SEPOMEX: {len(zipcode):,}')

zipcode_cdmx = zipcode[zipcode['c_estado'] == '09'].copy()
zipcode_cdmx['cp'] = zipcode_cdmx['cp'].astype(str).str.zfill(5)

pool_geo = zipcode_cdmx[['cp', 'd_asenta', 'municipio', 'd_ciudad']].drop_duplicates().reset_index(drop=True)
pool_registros = pool_geo.to_dict(orient='records') 

# --- LÓGICA DE CONTROL (CURP Y NSS) ---
CLAVE_CURP_CDMX = 'DF'
CONSONANTES = 'BCDFGHJKLMNPQRSTVWXYZ'
VOCALES = 'AEIOU'
ALFABETO = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def normaliza(texto):
    if not isinstance(texto, str):
        return ''
    s = unicodedata.normalize('NFKD', texto)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.upper()

def primera_consonante_interna(palabra):
    palabra = normaliza(palabra)
    for c in palabra[1:]:
        if c in CONSONANTES:
            return c
    return 'X'

def primera_vocal_interna(palabra):
    palabra = normaliza(palabra)
    for c in palabra[1:]:
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
    nom = normaliza(nombre).split()[0] if nombre else 'X'

    l1 = p_ap[0] if p_ap else 'X'
    l2 = primera_vocal_interna(p_ap)
    l3 = s_ap[0] if s_ap else 'X'
    l4 = nom[0] if nom else 'X'

    if (l1 + l2 + l3 + l4) in ALTISONANTES:
        l2 = 'X'

    fecha_str = fecha_nac.strftime('%y%m%d')
    sexo_letra = {'Masculino': 'H', 'Femenino': 'M'}.get(sexo, 'X')

    c1 = primera_consonante_interna(p_ap) if p_ap else 'X'
    c2 = primera_consonante_interna(s_ap) if s_ap else 'X'
    c3 = primera_consonante_interna(nom) if nom else 'X'

    homoclave = random.choice('0123456789') if fecha_nac.year < 2000 else random.choice(ALFABETO)
    verificador = random.choice('0123456789')

    return f'{l1}{l2}{l3}{l4}{fecha_str}{sexo_letra}{CLAVE_CURP_CDMX}{c1}{c2}{c3}{homoclave}{verificador}'

def generar_nss():
    return ''.join(random.choices('0123456789', k=11))

# --- CONFIGURACIÓN DE ENTORNOS ALEATORIOS ---
random.seed(config.SEED)
Faker.seed(config.SEED)

fake = Faker('es_MX')
HOY = date.today()

OPCIONES_SEXO = list(config.PESOS_SEXO.keys())
PROBS_SEXO = list(config.PESOS_SEXO.values())

pacientes = []
nss_usados = set()

print(f'Generando {config.N_PACIENTES:,} registros sintéticos con reglas INEGI / ENSANUT...')

while len(pacientes) < config.N_PACIENTES:
    nss = generar_nss()
    if nss in nss_usados:
        continue
    nss_usados.add(nss)

    sexo = random.choices(OPCIONES_SEXO, weights=PROBS_SEXO, k=1)[0]

    if sexo == 'Masculino':
        nombre = fake.first_name_male()
    elif sexo == 'Femenino':
        nombre = fake.first_name_female()
    else:
        nombre = fake.first_name()

    primer_apellido = fake.last_name()
    segundo_apellido = fake.last_name() if random.random() < config.PROB_SEGUNDO_APELLIDO else None

    fecha_nac = fake.date_of_birth(minimum_age=config.EDAD_MINIMA, maximum_age=config.EDAD_MAXIMA)
    edad = (HOY - fecha_nac).days // 365

    # Consumo del módulo hermano de la subcarpeta
    estatura_cm, imc, peso, estado_nutricional = talla.calcular_antropometria(sexo, edad)

    geo = random.choice(pool_registros)
    curp = generar_curp_sintetico(nombre, primer_apellido, segundo_apellido or '', fecha_nac, sexo)

    pacientes.append({
        'nss': nss,
        'curp_sintetico': curp,
        'nombre': nombre,
        'primer_apellido': primer_apellido,
        'segundo_apellido': segundo_apellido,
        'fecha_nacimiento': fecha_nac.strftime('%d/%m/%Y'), # Formato DD/MM/YYYY solicitado
        'edad': edad,
        'sexo': sexo,
        'estatura_cm': estatura_cm, # Entero absoluto
        'imc': imc,
        'peso_kg': peso,
        'estado_nutricional': estado_nutricional,
        'entidad_federativa': 'CDMX',
        'municipio': geo['municipio'],
        'cp': geo['cp'],
        'colonia': geo['d_asenta'],
        'ciudad': geo['d_ciudad'],
    })

# --- CONVERSIÓN Y EXPORTACIÓN FINAL ---
df_pacientes = pd.DataFrame(pacientes)
os.makedirs(config.DIR_OUTPUT, exist_ok=True)

df_pacientes.to_csv(config.SALIDA_CSV, index=False, encoding='utf-8')
df_pacientes.to_excel(config.SALIDA_XLSX, index=False)

print(f'\x1b[32mProceso finalizado con éxito.\x1b[0m')
print(f'-> Registros guardados en CSV: {config.SALIDA_CSV}')
print(f'-> Registros guardados en Excel: {config.SALIDA_XLSX}')