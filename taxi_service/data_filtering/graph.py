# Press the green button in the gutter to run the script.
import base64
import matplotlib
import io
import pandas as pd
import seaborn as sns
from abc import ABC, abstractmethod

from django.db.models import Sum
from django.db.models.functions import ExtractDay, TruncDate

from .models import SessionTaxi

# Setting matplotlib for back-end
matplotlib.use('Agg')


class GenerateGraph(ABC):
    AXIS_X = "Default x"
    AXIS_Y = "Default y"

    def __init__(self, type_graph=sns.barplot):
        self.type_graph = type_graph

    def get_graph_to_base64(self) -> str:
        pic_IObytes = io.BytesIO()
        scatter_fig = self._create_graph()
        scatter_fig.savefig(pic_IObytes, format='png', bbox_inches='tight')
        pic_IObytes.seek(0)
        pic_hash = base64.b64encode(pic_IObytes.read()).decode('utf-8')
        pic_IObytes.close()

        return pic_hash

    def _create_graph(self) -> matplotlib.axes._axes.Axes:
        pd_data_graph = self._get_params_pandas()
        scatter_plot = self.type_graph(x=self.AXIS_X, y=self.AXIS_Y, data=pd_data_graph)
        scatter_plot.set_xticklabels(scatter_plot.get_xticklabels(), rotation=45, horizontalalignment='right')
        scatter_fig = scatter_plot.get_figure()

        return scatter_fig

    def _get_params_pandas(self) -> pd.core.frame.DataFrame:
        data_graph = self._get_data_from_db()
        pd_data_graph = pd.DataFrame(data_graph, columns=[self.AXIS_X, self.AXIS_Y])

        return pd_data_graph

    @abstractmethod
    def _get_data_from_db(self) -> list:
        pass


class GG_Date2Price_AllTime(GenerateGraph):
    AXIS_X = "Date"
    AXIS_Y = "Price"

    def _get_data_from_db(self) -> list:
        data_graph = SessionTaxi.objects.annotate(
            date=TruncDate('date_session')
        ).values_list(
            "date"
        ).annotate(
            sum_money=Sum('price')
        )
        print(len(data_graph))
        return data_graph


class GG_Money_Per_Month(GenerateGraph):
    AXIS_X = "Date"
    AXIS_Y = "Price"

    def __init__(self, month, type_graph=sns.barplot):
        self.month = month
        super().__init__(type_graph=type_graph)

    def _get_data_from_db(self) -> list:
        data_graph = SessionTaxi.objects.filter(
            date_session__month=self.month
        ).annotate(
            month=ExtractDay('date_session')
        ).values_list(
            "month"
        ).annotate(
            sum_money=Sum('price')).order_by()

        print(data_graph)

        return data_graph