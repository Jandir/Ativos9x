## Script Ativos9x v1.01
##
## Autor: twitter.com/jandirp
##
## Script para pesquisa de ativos listados em bolsa B3 com possível situação de compra/ou venda
## Baseado em setup 9.1 Larry Williams ensinado no Brasil por Palex (t.me/palexgram)
##
## Script gera um CSV com ativos em situação 9.1 para analise em plataforma de negociação ou gráfico de análise técnica

import pandas_datareader as pdr
import pandas as pd

from datetime import datetime, timedelta
import numpy as np


# Lista de ativos a serem rastreados na B3
# Essa lista foi gerada a partir do próprio site da B3
# Pode-se criar sua própria lista usando a primeira coluna com o nome do ativo desejado.
dfSymbols = pd.read_csv('AtivosB3.csv', sep=';')

# DataFram para lista dos ativos detectados como 9.1 no último pregão
dfResultado = pd.DataFrame(columns=['Ativo', 'Operação', 'Dia', 'Start', 'Stop'])

print('Possíveis 9.1 de Compra/Venda')

for NomedoAtivo in dfSymbols.Asset:
    try:
        # Periodo selecionado aqui é dos últimos 30 dias a partir de hoje.
        # 30 dias se viu como um período mínimo viável para se fazer as médias de apoio ao setup
        # Não será contado o dia de "HOJE" para não pegar pregão em andamento, sempre o hoje-1
        dfAtivoSemanal = pdr.get_data_yahoo(NomedoAtivo + '.SA',
                                            start=(datetime.now() - timedelta(30)).strftime('%Y, %m, %d'),
                                            end=(datetime.now() - timedelta(1)).strftime('%Y, %m, %d')
                                            )
    except:
        # print(Ativo, "Sem informações para esse ativo...")
        continue

    dfAtivoSemanal = dfAtivoSemanal.dropna()

    # Calculo de Média Móvel Curta Exponencial
    # Pandas permite o calculo da média exponencial (EWM) direto no dataframe sem necessidade de funções a parte
    nPeriodos = 9  # Média Curta
    dfAtivoSemanal['MME9'] = dfAtivoSemanal.Close.ewm(span=nPeriodos).mean().dropna()

    # Calculo de Média Móvel Longa Exponencial
    nPeriodos = 21  # Média Longa
    dfAtivoSemanal['MME21'] = dfAtivoSemanal.Close.ewm(span=nPeriodos).mean().dropna()

    ## Slop of MME
    # dfTendencia > 0 diz que a MME9 está para cima ou tendência de alta
    # dfTendencia < 0 dia que a MME9 está para baixo ou tendência de baixa
    dfTendencia = dfAtivoSemanal.MME9 - dfAtivoSemanal.shift(1).MME9

    # Se o candle atravessa a MME9 então é candidato a ser um sinal 9.1 Se atravessa
    #   (fecha acima da MME9) e
    # dfTendencia > 0 então é um 9.1 de compra com disparo da ordem na máxima do candle corrente mais 1 centavo ou tick
    # Esse mais 1 centavo é recomendação do Palex para melhorar a taxa de acerto
    dfAtivoSemanal['mark_max'] = np.where(
        (dfAtivoSemanal.MME9 < dfAtivoSemanal.Close) &
        (dfAtivoSemanal.MME9 > dfAtivoSemanal.Open) &
        (dfTendencia > 0),
        dfAtivoSemanal.High + 0.01,
        0
    )
    # Se atravessa (fecha abaixo da MME9) e dfTendencia < 0 então é um 9.1 de venda com disparo da ordem de venda na
    # mínima mais 1 centavo ou tick do candle corrente
    # Esse mais 1 centavo é recomendação do Palex para melhorar a taxa de acerto
    dfAtivoSemanal['mark_min'] = np.where(
        (dfAtivoSemanal.MME9 > dfAtivoSemanal.Open) &
        (dfAtivoSemanal.MME9 < dfAtivoSemanal.Close) &
        (dfTendencia < 0),
        dfAtivoSemanal.Low - 0.01,
        0
    )

    # Compra ou Venda?
    # MME9 maior que a do Candle anterior e
    #   Candle de alta com fechamento maior que a MME9 e
    #   mínima menor que a MME9 então
    #       COMPRA 1 centavo a mais que a máxima do candle corrente ou do último pregão
    # MME9 menor que a do Candle anterior e
    #   Candle de baixa com fechamento menor que a MME9 e
    #   máxima maior que a MME9 então
    #       VENDA 1 centavo a menos que a mínima do candle corrente ou do último pregão

    # Pegar preços de entrada
    dfAtivoSemanal['buy_start'] = dfAtivoSemanal.mark_max
    dfAtivoSemanal['sell_start'] = dfAtivoSemanal.mark_min

    # Pegar preços de saida
    dfAtivoSemanal['buy_stop'] = np.where(
        (dfAtivoSemanal.mark_max > 0),
        dfAtivoSemanal.Low,
        0
    )
    dfAtivoSemanal['sell_stop'] = np.where(
        (dfAtivoSemanal.mark_min > 0),
        dfAtivoSemanal.High,
        0
    )

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