def factorial_num(int1: int):
    result = int1
    for i in range(int1 - 1, 0, -1):
        result *= i

    return result

if __name__ == "__main__":
    my_num = int(input("Introduce an integer number: "))
    factorial_1 = factorial_num(my_num)
    print(f"The factorial of {my_num} is {factorial_1}")

