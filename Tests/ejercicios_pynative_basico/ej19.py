def tax_bracket(income: int):
    if income >= 10000:
        if income >= 20000:
            first_bracket = 10000 * 0.1
            second_bracket = (income - 20000) * 0.2
            return first_bracket + second_bracket
        else:
            return (income - 10000) * 0.1
    else:
        return 0

if __name__ == "__main__":
    income = int(input("Enter your income: "))
    tax = tax_bracket(income)
    print(f"The tax for an income of {income} is: {tax}")