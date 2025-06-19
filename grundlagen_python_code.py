# Syntaxbeispiel zu Bedingungen
x = 5
if x > 10:
    print("x ist größer als 10")
elif x == 10:
    print("x ist 10")
else:
    print("x ist kleiner als 10")

# Der Output wäre
# x is less than 10







# Syntaxbeispiel zu For-Schleifen
numbers = [1, 2, 3]
for e in numbers:
    e = e + 1
print(numbers)

# Der Output wäre
# [2, 3, 4]








# Syntaxbeispiel zu While-Schleifen

counter = 0
limit   = 5
while counter < limit:
    print(f"counter: {counter}")
    counter += 1 
print("finished")

# Der Output wäre
# 10