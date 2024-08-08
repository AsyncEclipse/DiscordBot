

listey = ["ioc", "ioc", "fus", "empty"]
replace = "fus"
new = "lel"

for i,name in enumerate(listey):
    if name == replace:
        listey[i] = new
        break

print(listey)