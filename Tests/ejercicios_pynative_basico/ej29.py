words = ["Apple", "Banana", "Cherry", "Date", "Elderberry"]

length = [len(word) for word in words]
final = ""
for i in range(len(words)):
    final += f"{words[i]} - {length[i]} "

print(final)
