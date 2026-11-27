def suma_o_producto(int1, int2):
    result = 0
    if int1 * int2 > 1000:
        result = int1 + int2
    else:
        result = int1 * int2
    return result

if __name__ == "__main__":
    suma1 = suma_o_producto(20, 30)
    suma2 = suma_o_producto(40, 30)
    print(suma1)
    print(suma2)