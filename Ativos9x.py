import pandas_datareader as pdr
import pandas as pd

import datetime
import numpy as np
import plotly
import plotly.offline as py
import plotly.graph_objs as go


def get_ema(window, prices):
    me = prices.ewm(span=window).mean().dropna()

    data = pd.DataFrame(index=me.index)
    data['Price'] = prices
    data['EMA'] = me

    return data


# Lista de ativos a serem rastreados na B3
dfSymbols = pd.read_csv('AtivosB3.csv', sep=';')
dfRow = pd.DataFrame(columns=['Ativo', 'Operação', 'Dia', 'Start', 'Stop'])
dfResultado = dfRow

print('Possíveis 9.1 Compra/Venda')

for NomedoAtivo in dfSymbols.Asset:
    try:
        dfAtivoSemanal = pdr.get_data_yahoo(NomedoAtivo + '.SA',
                                            start=datetime.datetime(2020, 5, 1),
                                            end=datetime.datetime(2020, 6, 30))
    except:
        # print(Ativo, "Sem informações para esse ativo...")
        continue

    # Calculo de Média Móvel Curta Exponencial
    dfAtivoSemanal = dfAtivoSemanal.dropna()

    nPeriodos = 9  # Média Curta
    dfAtivoSemanal['MME9'] = dfAtivoSemanal.Close.ewm(span=nPeriodos).mean().dropna()
    dfAtivoSemanal['MM9'] = dfAtivoSemanal.Close.rolling(window=nPeriodos).mean().dropna()

    ## Slop of MME
    # dif > 0 diz que a MME9 está para cima ou tendência de alta
    # dif < 0 dia que a MME9 está para baixo ou tendência de baixa
    dif = dfAtivoSemanal.MME9 - dfAtivoSemanal.shift(1).MME9

    dfAtivoSemanal['mark_max'] = np.where(
        (dfAtivoSemanal.MME9 < dfAtivoSemanal.High) &
        (dfAtivoSemanal.MME9 > dfAtivoSemanal.Low) &
        (dif > 0),
        dfAtivoSemanal.High, 0)
    dfAtivoSemanal['mark_min'] = np.where(
        (dfAtivoSemanal.MME9 > dfAtivoSemanal.Low) &
        (dfAtivoSemanal.MME9 < dfAtivoSemanal.High) &
        (dif < 0),
        dfAtivoSemanal.Low, 0)

    # get start point
    dfAtivoSemanal['buy_start'] = np.where((dfAtivoSemanal.Low < dfAtivoSemanal.shift(1).mark_max) & (dfAtivoSemanal.High > dfAtivoSemanal.shift(1).mark_max),
                                  dfAtivoSemanal.shift(1).mark_max, np.NaN)
    dfAtivoSemanal['sell_start'] = np.where((dfAtivoSemanal.Low < dfAtivoSemanal.shift(1).mark_min) & (dfAtivoSemanal.High > dfAtivoSemanal.shift(1).mark_min),
                                   dfAtivoSemanal.shift(1).mark_min, np.NaN)

    # set stop loss
    dfAtivoSemanal['buy_stop'] = np.where((dfAtivoSemanal.Low < dfAtivoSemanal.shift(1).mark_max) & (dfAtivoSemanal.High > dfAtivoSemanal.shift(1).mark_max),
                                 dfAtivoSemanal.shift(1).Low, np.NaN)
    dfAtivoSemanal['sell_stop'] = np.where((dfAtivoSemanal.Low < dfAtivoSemanal.shift(1).mark_min) & (dfAtivoSemanal.High > dfAtivoSemanal.shift(1).mark_min),
                                  dfAtivoSemanal.shift(1).High, np.NaN)

    dfUltimoNegocio = dfAtivoSemanal.tail(1)

    if dfUltimoNegocio.buy_start[0] > 0:
        sStart = "R${:,.2f}".format(dfUltimoNegocio.buy_start[0])
        sStop  = "R${:,.2f}".format(dfUltimoNegocio.buy_stop[0])
        print(NomedoAtivo, 'Compra', dfUltimoNegocio.index[0].strftime("%d/%m/%Y"), sStart, sStop)
        dfResultado = dfResultado.append({
            'Ativo': NomedoAtivo,
            'Operação': 'Compra',
            'Dia': dfUltimoNegocio.index[0].strftime("%d/%m/%Y"),
            'Start': sStart,
            'Stop': sStop
        }, ignore_index=True)
    elif dfUltimoNegocio.sell_start[0] > 0:
        sStart = "R${:,.2f}".format(dfUltimoNegocio.sell_start[0])
        sStop = "R${:,.2f}".format(dfUltimoNegocio.sell_stop[0])
        print(NomedoAtivo, 'Venda', dfUltimoNegocio.index[0].strftime("%d/%m/%Y"), sStart, sStop)
        ##columns=['Ativo', 'Operação', 'Dia', 'Start', 'Stop'])

        dfResultado = dfResultado.append({
            'Ativo': NomedoAtivo,
            'Operação': 'Venda',
            'Dia': dfUltimoNegocio.index[0].strftime("%d/%m/%Y"),
            'Start': sStart,
            'Stop': sStop
        }, ignore_index=True)

print(dfResultado)
dfResultado.to_csv('Ativos9x.csv')