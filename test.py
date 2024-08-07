ships = ["blue-cru", "red-drd", "blue-int"]

for i in ships:
    if "cru" in i:
        print("yay")
    else:
        print("boo")

color = ships[0].split("-")[0]
print(color)