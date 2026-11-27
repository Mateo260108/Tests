def odd_slicing(my_string: str):
    return my_string[::2]

if __name__ == "__main__":
    a_string = input("Enter a string: ")
    result = odd_slicing(a_string)
    print(f"The characters at odd indices are: {result}")