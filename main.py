# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    file = open("inpute_data.txt")

    tiket_list = []

    for line in file:
        tiket = line.split(',')
        tiket_correct = (tiket[0], tiket[1].split(" ")[1], tiket[1].split(" ")[-1], *tiket[2:])
        tiket_list.append(tiket_correct)

    print(tiket_list)
