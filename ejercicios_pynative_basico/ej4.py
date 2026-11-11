def truncate_string(my_string: str, length: int):
    if length < 0:
        raise ValueError("Length must be a non-negative integer.")
    return my_string[length:]

if __name__ == "__main__":
    a_string = input("Enter a string: ")
    length = int(input("Enter the length to truncate to: "))
    result = truncate_string(a_string, length)
    print(f"The truncated string is: {result}")