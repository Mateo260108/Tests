result = 0
for i in range(10):
    term1 = i
    term2 = i - 1 if i > 0 else 0
    result = term1 + term2
    print(f"Current number: {i}     ; Previous number: {i - 1}      ; Sum: {result}")