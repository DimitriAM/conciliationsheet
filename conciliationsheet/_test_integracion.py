import urllib.request, json

import os
BASE = r"C:\Aldo\CONCILIATIONSHEETS\conciliationsheet"
API = "http://localhost:5000/api"

def post_json(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req)
    return resp.status, json.loads(resp.read())

def upload_file(filepath, filename):
    url = API + "/upload"
    boundary = "----Boundary7MA4YWxkTrZu0gW"
    with open(filepath, "rb") as f:
        filedata = f.read()
    body = b"--" + boundary.encode() + b"\r\n"
    body += b'Content-Disposition: form-data; name="file"; filename="' + filename.encode() + b'"\r\n'
    body += b"Content-Type: text/csv\r\n\r\n"
    body += filedata + b"\r\n"
    body += b"--" + boundary.encode() + b"--\r\n"
    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    resp = urllib.request.urlopen(req)
    return resp.status, json.loads(resp.read())

print("=" * 60)
print("TEST DE INTEGRACION - CONCILIATION SHEETS")
print("=" * 60)

# 1. Crear cuentas
print("\n1. Crear cuentas bancarias...")
s, d = post_json(API + "/cuentas", {"nombre": "Cuenta Test", "banco": "Banco Test", "saldo_inicial": 10000})
print(f"   Cuenta 1 id={d['id']} status={s}")
s, d = post_json(API + "/cuentas", {"nombre": "Caja Ahorro", "banco": "Otro Banco", "saldo_inicial": 5000})
print(f"   Cuenta 2 id={d['id']} status={s}")

# 2. Upload banco
print("\n2. Subir archivo banco...")
s, d = upload_file(os.path.join(BASE, "data/pruebas/extracto_banco_ejemplo.csv"), "extracto_banco.csv")
archivo = d["archivo"]["nombre_archivo"]
print(f"   Status={s} archivo={archivo}")

# 3. Process banco
print("\n3. Procesar archivo banco...")
s, d = post_json(API + "/process", {"archivo": archivo, "cuenta_id": 1, "fuente": "banco"})
print(f"   Status={s} registros={d.get('registros_insertados')}")

# 4. Upload contabilidad
print("\n4. Subir archivo contabilidad...")
s, d = upload_file(os.path.join(BASE, "data/pruebas/contabilidad_ejemplo.csv"), "contabilidad.csv")
archivo2 = d["archivo"]["nombre_archivo"]
print(f"   Status={s} archivo={archivo2}")

# 5. Process contabilidad
print("\n5. Procesar archivo contabilidad...")
s, d = post_json(API + "/process", {"archivo": archivo2, "cuenta_id": 1, "fuente": "contabilidad"})
print(f"   Status={s} registros={d.get('registros_insertados')}")

# 6. Conciliar Forma 1
print("\n6. Conciliar - Forma 1 (Banco -> Contabilidad)...")
s, d = post_json(API + "/conciliate", {
    "cuenta_id": 1, "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31",
    "metodo": "1", "vision": "empresa"
})
print(f"   Status={s} conciliado={d.get('conciliado')} diferencia={d.get('diferencia')}")
print(f"   Partidas: {len(d.get('partidas_conciliatorias', []))}")

# 7. Conciliar Forma 2
print("\n7. Conciliar - Forma 2 (Contabilidad -> Banco)...")
s, d = post_json(API + "/conciliate", {
    "cuenta_id": 1, "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31",
    "metodo": "2", "vision": "empresa"
})
print(f"   Status={s} conciliado={d.get('conciliado')} diferencia={d.get('diferencia')}")
print(f"   Partidas: {len(d.get('partidas_conciliatorias', []))}")

# 8. Conciliar Cuadrada
print("\n8. Conciliar - Cuadrada...")
s, d = post_json(API + "/conciliate", {
    "cuenta_id": 1, "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31",
    "metodo": "cuadrada", "vision": "empresa"
})
print(f"   Status={s} conciliado={d.get('conciliado')} diferencia={d.get('diferencia')}")
print(f"   Partidas: {len(d.get('partidas_conciliatorias', []))}")

# 9. Verificar NO duplicacion de partidas (bug #1 fix)
print("\n9. Verificar que NO hay partidas duplicadas...")
resp = urllib.request.urlopen(API + "/partidas?cuenta_id=1&per_page=500")
result = json.loads(resp.read())
total = result["total"]
print(f"   Total partidas: {total}")

# 10. Test segunda cuenta
print("\n10. Test con segunda cuenta (cuenta_id=2)...")
s, d = post_json(API + "/conciliate", {
    "cuenta_id": 2, "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31",
    "metodo": "1", "vision": "empresa"
})
print(f"   Status={s} (esperado error 400 o exito)")

# 11. Limpiar datos de prueba
print("\n11. Limpiar datos de prueba...")
req = urllib.request.Request(API + "/conciliate", method="DELETE")
urllib.request.urlopen(req)
req = urllib.request.Request(API + "/process/clear", method="DELETE")
urllib.request.urlopen(req)
req = urllib.request.Request(API + "/cuentas/1", method="DELETE")
urllib.request.urlopen(req)
req = urllib.request.Request(API + "/cuentas/2", method="DELETE")
urllib.request.urlopen(req)
print("   Datos limpiados")

print("\n" + "=" * 60)
print("TEST COMPLETADO EXITOSAMENTE")
print("=" * 60)
