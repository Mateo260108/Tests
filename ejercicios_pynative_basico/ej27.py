list_a = [1, 2, 3, 4, 5]
list_b = [4, 5, 6, 7, 8]

#matches = []
#for num in list_a:
#    if num in list_b:
#        matches.append(num)
#print(f"Common elements: {matches}")

#Solution using set intersection:
set_a = set(list_a)
set_b = set(list_b) 

matches = set_a & set_b
print(f"Common elements: {matches}")