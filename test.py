ships = ["blue-cru", "red-drd", "blue-int"]

for i in ships:
    if "cru" in i:
        print("yay")
    else:
        print("boo")

for i in enumerate(ships):
    print(i)