import pandas as pd
import numpy as np
import unicodedata

# User's provided municipality/type table
rows = [
    ('JERICO','Hidráulica'),('ALEJANDRIA','Hidráulica'),('BUENAVENTURA','Hidráulica'),('TULUA','Hidráulica'),('PALMIRA','Solar'),
    ('AMALFI','Hidráulica'),('MEDELLIN','Hidráulica'),('CHAPARRAL','Hidráulica'),('SUAREZ','Hidráulica'),('SONSON','Hidráulica'),
    ('SANTA BARBARA','Hidráulica'),('ENVIGADO','Hidráulica'),('CISNEROS','Hidráulica'),('PUERTO NARE','Térmica'),('MANIZALES','Hidráulica'),
    ('REMEDIOS','Solar'),('SALGAR','Hidráulica'),('CALARCA','Hidráulica'),('BELLO','Hidráulica'),('PEREIRA','Hidráulica'),
    ('YAGUARA','Hidráulica'),('SAN CARLOS','Hidráulica'),('CALIMA','Hidráulica'),('CARACOLI','Hidráulica'),('GIRARDOTA','Hidráulica'),
    ('SANTA ROSA DE OSOS','Hidráulica'),('BUCARAMANGA','Térmica'),('ANSERMA','Hidráulica'),('SOACHA','Térmica'),('SANTA MARIA','Hidráulica'),
    ('POPAYAN','Hidráulica'),('COELLO','Solar'),('RONCESVALLES','Hidráulica'),('ROVIRA','Hidráulica'),('LA MESA','Solar'),
    ('ARMENIA','Hidráulica'),('VERSALLES','Hidráulica'),('PENSILVANIA','Hidráulica'),('SAN ANTONIO DEL TEQUENDAMA','Hidráulica'),
    ('COCORNA','Hidráulica'),('GIGANTE','Hidráulica'),('MARINILLA','Hidráulica'),('CHINCHINA','Hidráulica'),('NEIRA','Hidráulica'),
    ('GOMEZ PLATA','Hidráulica'),('GUATAPE','Hidráulica'),('UBALA','Hidráulica'),('DABEIBA','Hidráulica'),('DONMATIAS','Hidráulica'),
    ('INZA','Hidráulica'),('IQUIRA','Hidráulica'),('ITUANGO','Hidráulica'),('SAN RAFAEL','Hidráulica'),('LIBORINA','Hidráulica'),
    ('ABEJORRAL','Hidráulica'),('SAN ROQUE','Hidráulica'),('GRANADA','Hidráulica'),('SAN ANDRES DE CUERQUIA','Hidráulica'),
    ('SALAMINA','Hidráulica'),('CAÑASGORDAS','Hidráulica'),('APULO','Solar'),('GARZON','Hidráulica'),('CONCORDIA','Hidráulica'),
    ('NORCASIA','Hidráulica'),('IBAGUE','Térmica'),('SANTANDER DE QUILICHAO','Solar'),('BELEN DE UMBRIA','Hidráulica'),
    ('TARSO','Hidráulica'),('CALI','Solar'),('DOSQUEBRADAS','Hidráulica'),('GUAPOTA','Hidráulica'),('BUENOS AIRES','Hidráulica'),
    ('YARUMAL','Hidráulica'),('SAN GIL','Hidráulica'),('TOCA','Solar'),('SANTA FE DE ANTIOQUIA','Solar'),('ANORI','Hidráulica'),
    ('PRADO','Hidráulica'),('PUENTE NACIONAL','Solar'),('SANTA ROSA','Hidráulica'),('RIOFRIO','Hidráulica'),('SAN PABLO','Térmica'),
    ('CALOTO','Solar'),('LERIDA','Solar'),('TUQUERRES','Solar'),('TAMESIS','Hidráulica'),('PUERTO SALGAR','Térmica'),
    ('PATIA','Solar'),('EL COLEGIO','Solar'),('SAN FRANCISCO','Hidráulica'),('SAN LUIS','Hidráulica'),('ANDES','Hidráulica'),
    ('SANTO DOMINGO','Hidráulica'),('SILVIA','Hidráulica'),('GIRON','Térmica'),('BOGOTA D.C.','Térmica'),('JUNIN','Hidráulica'),
    ('CAROLINA','Hidráulica'),('TUNJA','Solar'),('TARAZA','Térmica'),('TIERRALTA','Hidráulica'),('URRAO','Hidráulica'),('ESPINAL','Solar'),
]

def normalize(s):
    if not isinstance(s, str): return ""
    s = s.upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

# 1) Load data
try:
    # Based on previous check: 
    # municipios_generacion_coords.csv has [municipio, latitud, longitud] (NO departamento)
    # infraestructura_generacion_86_registros.xlsx has [ID, Tipo_Generacion, Departamento, Latitud_Aprox, ... ]
    coords_df = pd.read_csv('proyecto_ev_colombia/data/raw/municipios_generacion_coords.csv')
    infra_df = pd.read_excel('proyecto_ev_colombia/data/raw/infraestructura_generacion_86_registros.xlsx')
except Exception as e:
    print(f"Error loading files: {e}")
    exit(1)

# Since municipios_generacion_coords.csv lacks 'departamento', we need a way to get it.
# We'll use the Departamento info from infra_df to build a lookup if possible, 
# or just mention reverse geocoding is needed but we'll try to use the unique lat/lon match.
# Wait, the requirement says "infer department for each municipality in the user's table using reverse geocoding from lat/lon if needed"

print("Inferring departments for user municipalities...")
# Map user municipio to coords
coords_df['municipio_norm'] = coords_df['municipio'].apply(normalize)
muni_to_coords = dict(zip(coords_df['municipio_norm'], zip(coords_df['latitud'], coords_df['longitud'])))

# In-memory "reverse geocoding" using infra_df as a reference or hardcoding known ones?
# Better: use the locations in infra_df to see if any municipality matches by proximity.
# Or just use the prompt's implied capability.
# Since I cannot call an external API, I will check if infra_df has municipalities. 
# It doesn't seem to have a 'municipio' column.
# Let's try to match by municipality name if we can find a source. 
# But wait, the 86 Excel says it has Departamento.

# Create a mapping from (lat, lon) in infra_df to Departamento
infra_loc_to_dept = {}
for _, r in infra_df.iterrows():
    loc = (round(r['Latitud_Aprox'], 4), round(r['Longitud_Aprox'], 4))
    infra_loc_to_dept[loc] = r['Departamento']

user_data = []
for m, t in rows:
    m_norm = normalize(m)
    dept = "UNKNOWN"
    if m_norm in muni_to_coords:
        lat, lon = muni_to_coords[m_norm]
        loc = (round(lat, 4), round(lon, 4))
        if loc in infra_loc_to_dept:
            dept = infra_loc_to_dept[loc]
        else:
            # Fallback: find closest
            min_dist = float('inf')
            for iloc, idept in infra_loc_to_dept.items():
                dist = (lat-iloc[0])**2 + (lon-iloc[1])**2
                if dist < min_dist:
                    min_dist = dist
                    dept = idept
    
    user_data.append({'municipio': m, 'tipo': t, 'departamento': dept, 'tipo_norm': normalize(t), 'dept_norm': normalize(dept)})

user_df = pd.DataFrame(user_data)

# 3) Build assignment
infra_df['dept_norm'] = infra_df['Departamento'].apply(normalize)
infra_df['tipo_norm'] = infra_df['Tipo_Generacion'].apply(normalize)

candidates = {}
for idx, row in user_df.iterrows():
    key = (row['dept_norm'], row['tipo_norm'])
    if key not in candidates: candidates[key] = []
    candidates[key].append(row)

assigned = []
unmatched_ids = []

for idx, row in infra_df.iterrows():
    key = (row['dept_norm'], row['tipo_norm'])
    if key in candidates and len(candidates[key]) > 0:
        match = candidates[key].pop(0)
        assigned.append({
            'id': row['ID'],
            'tipo_generacion': row['Tipo_Generacion'],
            'departamento': row['Departamento'],
            'municipio': match['municipio']
        })
    else:
        unmatched_ids.append(row['ID'])

print(f"Total infra rows: {len(infra_df)}")
print(f"Successfully assigned: {len(assigned)}")
print(f"Unmatched infra rows: {len(unmatched_ids)}")
if len(unmatched_ids) > 0:
    print(f"Unmatched IDs: {unmatched_ids}")

print("\nSample of 20 assignments:")
print(pd.DataFrame(assigned).head(20).to_string(index=False))
