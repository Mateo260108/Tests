data = [1, 2, 2, 3, 4, 4, 4, 5]

my_list = []
for num in data:
    if num not in my_list:
        my_list.append(num)
print(my_list)
