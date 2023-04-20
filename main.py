# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # import datetime

    def sum(a, b):
        return (a + b)


    def mul(a, b):
        return a, b


    a = [1, 3, 5]
    b = [2, 4, 6, 9]

    c = list(map(mul, a, b))

    print(map.__dict__)
    # tod = datetime.datetime.today()
    # print(tod)
    # print(str(tod))
    # file = open("inpute_data.txt")
    #
    # tiket_list = []
    #
    # for line in file:
    #     tiket = line.split(',')
    #     tiket_correct = (tiket[0], tiket[1].split(" ")[1], tiket[1].split(" ")[-1], *tiket[2:])
    #     tiket_list.append(tiket_correct)
    #
    # print(tiket_list)
