Limit = 20
primes = []
for num in range(2, Limit + 1):
    divisible = False
    for i in range(2, num):
        print(num, i)
        if num % i == 0:
            divisible = True
            break

    if divisible == False:
        primes.append(num)

alternate_primes = primes[::2]
print(alternate_primes)