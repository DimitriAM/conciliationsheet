import urllib.request, json
API = "http://localhost:5000/api"
resp = urllib.request.urlopen(API + "/cuentas")
for c in json.loads(resp.read()):
    r = urllib.request.Request(API + "/cuentas/" + str(c["id"]), method="DELETE")
    try:
        urllib.request.urlopen(r)
        print("Deleted cuenta " + str(c["id"]) + ": " + c["nombre"])
    except Exception as e:
        print("Error deleting " + str(c["id"]) + ": " + str(e))
for ep in ["/conciliate", "/process/clear"]:
    try:
        r = urllib.request.Request(API + ep, method="DELETE")
        urllib.request.urlopen(r)
    except:
        pass
print("Cleanup done")
