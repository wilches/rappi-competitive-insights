import json

# Definimos la ruta del archivo
file_path = 'config/addresses.json'

# Abrimos y cargamos el archivo JSON
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Obtenemos la lista de direcciones
addresses = data.get("addresses", [])

# Imprimimos el total de direcciones
print(f"Total addresses: {len(addresses)}")

# Iteramos sobre la lista para imprimir cada address_id
for item in addresses:
    print(item['address_id'])
