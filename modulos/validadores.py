"""
Módulo de validaciones para la biblioteca virtual.
"""

def validar_cedula_ecuatoriana(cedula: str) -> bool:
    """
    Valida un número de cédula de identidad ecuatoriana utilizando el algoritmo
    oficial del dígito verificador (módulo 10).
    
    Reglas:
    - Longitud exacta de 10 dígitos numéricos.
    - Primeros 2 dígitos corresponden a una provincia válida (01 a 24) o 30 para inscritos en el exterior.
    - El tercer dígito debe ser menor a 6 (0-5) correspondiente a personas naturales.
    - Multiplicación de los primeros 9 dígitos por coeficientes alternados [2, 1, 2, 1, 2, 1, 2, 1, 2].
    - Si el producto es mayor o igual a 10, se le resta 9.
    - Se suman todos los productos y se calcula la decena superior menos la suma.
    - El resultado debe coincidir con el décimo dígito (dígito verificador).
    """
    if not cedula or not isinstance(cedula, str):
        return False
        
    cedula = ''.join(c for c in cedula if c.isdigit())
    if len(cedula) != 10:
        return False
        
    provincia = int(cedula[:2])
    if not ((1 <= provincia <= 24) or provincia == 30):
        return False
        
    tercer_digito = int(cedula[2])
    if tercer_digito >= 6:
        return False
        
    coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0
    for i in range(9):
        producto = int(cedula[i]) * coeficientes[i]
        if producto >= 10:
            producto -= 9
        suma += producto
        
    digito_verificador = 0 if suma % 10 == 0 else 10 - (suma % 10)
    return digito_verificador == int(cedula[9])
