## Script Ativos9x v1.09 MultiTreading
##
## Autor: twitter.com/jandirp
##
## Script para pesquisa de ativos listados em bolsa B3 com possível situação de compra/ou venda
## Baseado em setup 9.1 Larry Williams ensinado no Brasil por Palex (t.me/palexgram)
##
## Versão com MultTreading

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas_datareader as pdr
import pandas as pd 
import time
import concurrent.futures

from datetime import datetime, timedelta
import numpy as np 

def AnaliseAtivo(sAtivo):
    try:
        # Periodo selecionado aqui é dos últimos 30 dias a partir de hoje.
        # 30 dias se viu como um período mínimo viável para se fazer as médias de apoio ao setup
        # Não será contado o dia de "HOJE" para não pegar pregão em andamento, sempre o hoje-1
        # dfAtivo30Dias = pdr.get_data_yahoo(Ativo + '.SA',

        dfAtivo30Dias = pdr.DataReader(sAtivo + '.SA', 'yahoo',
            start=(datetime.now() - timedelta(30)).strftime('%Y, %m, %d'),
            end=(datetime.now() - timedelta(1)).strftime('%Y, %m, %d')
        )
    except:
        # print(Ativo, "Sem informações para esse ativo...")
        return

    dfAtivo30Dias = dfAtivo30Dias.dropna()

    # Calculo de Média Móvel Curta Exponencial
    # Pandas permite o calculo da média exponencial (EWM) direto no dataframe sem necessidade de funções a parte
    # Atualmente o script usa apenas a MME9, as outras serão usadas em implementações futuras.
    # lPeriodos = (9, 21, 51, 200)
    lPeriodos = (9, 21)
    for nPeriodos in lPeriodos:
        dfAtivo30Dias['MME' + str(nPeriodos)] = dfAtivo30Dias.Close.ewm(span=nPeriodos).mean().dropna()

    ## Slop of MME
    # dfTendencia > 0 diz que a MME9 está para cima ou tendência de alta
    # dfTendencia < 0 dia que a MME9 está para baixo ou tendência de baixa
    # O calculo original preve apenas a ocorrencia MME9 do elemento anterior para detectar
    # a tendência do preço.
    # para melhorar a qualidade de detecção do setup deve-se colocar mais elementos para se definir 
    # com mais precisão a tendência de alta ou de baixa.
    dfTendencia = dfAtivo30Dias.MME9 - dfAtivo30Dias.shift(1).MME9

    # Se o candle atravessa a MME9 então é candidato a ser um sinal 9.1 Se atravessa
    #   (fecha acima da MME9) e
    # dfTendencia > 0 então é um 9.1 de compra com disparo da ordem na máxima do candle corrente mais 1 centavo ou tick
    # Esse mais 1 centavo é recomendação do Palex para melhorar a taxa de acerto
    dfAtivo30Dias['mark_max'] = np.where(
        (dfAtivo30Dias.MME9 < dfAtivo30Dias.Close) &
        (dfAtivo30Dias.MME9 > dfAtivo30Dias.Open) &
        (dfTendencia > 0),
        dfAtivo30Dias.High + 0.01,
        0
    )
    # Se atravessa (fecha abaixo da MME9) e dfTendencia < 0 então é um 9.1 de venda com disparo da ordem de venda na
    # mínima mais 1 centavo ou tick do candle corrente
    # Esse mais 1 centavo é recomendação do Palex para melhorar a taxa de acerto
    dfAtivo30Dias['mark_min'] = np.where(
        (dfAtivo30Dias.MME9 > dfAtivo30Dias.Open) &
        (dfAtivo30Dias.MME9 < dfAtivo30Dias.Close) &
        (dfTendencia < 0),
        dfAtivo30Dias.Low - 0.01,
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
    dfAtivo30Dias['buy_start'] = dfAtivo30Dias.mark_max
    dfAtivo30Dias['sell_start'] = dfAtivo30Dias.mark_min

    # Pegar preços de saida
    dfAtivo30Dias['buy_stop'] = np.where(
        (dfAtivo30Dias.mark_max > 0),
        dfAtivo30Dias.Low,
        0
    )
    dfAtivo30Dias['sell_stop'] = np.where(
        (dfAtivo30Dias.mark_min > 0),
        dfAtivo30Dias.High,
        0
    )

    dfUltimoNegocio = dfAtivo30Dias.tail(1)

    if dfUltimoNegocio.buy_start[0] > 0:
        sStart = "R${:,.2f}".format(dfUltimoNegocio.buy_start[0])
        sStop  = "R${:,.2f}".format(dfUltimoNegocio.buy_stop[0])
        print(sAtivo, 'Compra', dfUltimoNegocio.index[0].strftime("%d/%m/%Y"), sStart, sStop)
    elif dfUltimoNegocio.sell_start[0] > 0:
        sStart = "R${:,.2f}".format(dfUltimoNegocio.sell_start[0])
        sStop = "R${:,.2f}".format(dfUltimoNegocio.sell_stop[0])
        print(sAtivo, 'Venda', dfUltimoNegocio.index[0].strftime("%d/%m/%Y"), sStart, sStop)

def main():
    tInicio = time.perf_counter()

    # Lista de ativos a serem rastreados na B3
    # Essa lista foi gerada a partir do próprio site da B3
    # Pode-se criar sua própria lista usando a primeira coluna com o nome do ativo desejado.
    dfSymbols = pd.read_csv('AtivosB3.csv', sep=';')

    # DataFram para lista dos ativos detectados como 9.1 no último pregão
    dfResultado = pd.DataFrame(columns=['Ativo', 'Operação', 'Dia', 'Start', 'Stop'])

    print('Possíveis 9.1 de Compra/Venda')

    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(AnaliseAtivo, dfSymbols.Asset)

    tFinal = time.perf_counter()

    print(f'Finalização em {tFinal-tInicio} segundos')

if __name__ == '__main__':
    main()
