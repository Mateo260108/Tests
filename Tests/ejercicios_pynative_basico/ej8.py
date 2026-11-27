def reverse_string(my_string: str):
    return my_string[::-1]

if __name__ == "__main__":
    str_input = input("Introduce a string: ")
    result = reverse_string(str_input)
    print(f"The resversed string is: {result}")