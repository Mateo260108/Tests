numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
for i in range(10):
    products_num = numbers[i]
    line = ""
    for j in range(1,11):
        product = products_num * j
        line += f"{product} "
    print(line)   