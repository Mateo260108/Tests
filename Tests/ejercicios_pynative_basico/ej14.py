str_x = "Emma is good developer. Emma is a writer"
phrases = str_x.split(".")
words = []
words.append(phrases[0].split(" "))
words.append(phrases[1].split(" "))
count = 0
for word in words:
    if "Emma" in word:
        count += 1

print("Emma appeared", count, "times")


