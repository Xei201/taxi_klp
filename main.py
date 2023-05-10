# Press the green button in the gutter to run the script.
import base64
import datetime
import matplotlib
matplotlib.use('Agg')
import io

if __name__ == '__main__':
    import pandas as pd
    import seaborn as sns

    test = [(1, 34), (2, 45), (4, 67)]

    df = pd.DataFrame(test, columns=['Round', 'Amount'], dtype=int)

    print(type(df))
    # tips = sns.load_dataset("tips")
    # scatter_plot = sns.barplot(x="Round", y="Amount", data=df)
    scatter_plot = sns.countplot(data=df)
    scatter_fig = scatter_plot.get_figure()
    print(type(scatter_plot))
    pic_IObytes = io.BytesIO()

    scatter_fig.savefig(pic_IObytes, format='png')
    pic_IObytes.seek(0)
    pic_hash = base64.b64encode(pic_IObytes.read()).decode('utf-8')
    pic_IObytes.close()
    print(pic_hash)
    # scatter_fig.savefig(f'test_seaborn/scatterplot{datetime.datetime.today()}.png')

    # import datetime
    #
    # def sum(a, b):
    #     return (a + b)
    #
    #
    # def mul(a, b):
    #     return a, b
    #
    #
    # a = [1, 3, 5]
    # b = [2, 4, 6, 9]
    #
    # c = list(map(mul, a, b))
    #
    # print(map.__dict__)
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
