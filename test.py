unit_list = ["blue"]
x = ["blue", "blue", "blue"]

for i in unit_list:
    if i in x:
        x.remove(i)


print(x)