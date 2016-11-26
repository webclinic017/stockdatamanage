# -*- coding: utf-8 -*-
'''
Created on 2016年5月4日

@author: who8736
'''

import logging
import os
import datetime as dt

import pandas as pd

# import datamanage as dm
import datatrans
import sqlrw


# def getLowPEStockList(maxPE=40):
#     """选取指定范围PE的股票
#     maxPE: 最大PE
#     """
# #     engine = getEngine()
#     sql = 'select stockid, pe from stocklist where pe > 0 and pe <= %s' % maxPE
#     df = pd.read_sql(sql, engine)
# #     engine.close()
#     return df


def calGuzhi(stockList=None):
    """生成估值水平评估列表，
    # 包括以下数据： peg, 未来三个PE预测， 过去6个季度TTM利润增长率， 平均增长率， 增长率方差
    Parameters
    --------
    stockList:list 股票列表 e.g:[600519, 600999]

    Return
    --------
    DataFrame
        stockid: 股票代码
        name: 股票名称
        pe: TTM市盈率
        peg: 股票PEG值
        next1YearPE: 下1年预测PE
        next2YearPE: 下2年预测PE
        next3YearPE: 下3年预测PE
        incrate0: 之前第6个季度TTM利润增长率
        incrate1: 之前第5个季度TTM利润增长率
        incrate2: 之前第4个季度TTM利润增长率
        incrate3: 之前第3个季度TTM利润增长率
        incrate4: 之前第2个季度TTM利润增长率
        incrate5: 之前第1个季度TTM利润增长率
        avgrate: 平均增长率
        madrate: 平均离差率， 按平均离差除以平均值计算，反应TTM利润增长率与平均增长率之间的偏离水平
                 # 该值越小，越体现TTM利润的稳定增长
    """

    if stockList is None:
        stockList = sqlrw.getLowPEStockList().stockid.values

#     print stockList.head()
#     print type(stockList)
    # pe数据
    peDf = sqlrw.readCurrentTTMPEs(stockList)
    # 估值数据
    pegDf = sqlrw.readGuzhiFilesToDf(stockList)
    pegDf = pd.merge(peDf, pegDf, on='stockid', how='left')
#     print pegDf.head()

    # TODO: endDate现为指定值， 待修改为自动取当前日期再转换为YYYYQ格式
    # TODO:　假设当前为第2季度，但第1季度上市公司的财务报告未公布，导致缺少数据如何处理
    sectionNum = 6  # 取6个季度
    endDate = 20162
    startDate = datatrans.quarterSub(endDate, sectionNum - 1)
#     quarter  = (int(endDate / 10) * 4 + (endDate % 10)) - sectionNum
    dateList = datatrans.dateList(startDate, endDate)
#     print dateList
    # 过去N个季度TTM利润增长率
    for i in range(sectionNum):
        incDf = sqlrw.readTTMLirunForDate(dateList[i])
        incDf = incDf[['stockid', 'incrate']]
        incDf.columns = ['stockid', 'incrate%d' % i]
#         print incDf.head()
        pegDf = pd.merge(pegDf, incDf, on='stockid', how='left')
#         pegDf = pd.merge(pegDf, incDf, on='stockid')

#     print pegDf.head()
    # 平均利润增长率
    endfield = 'incrate%s' % (sectionNum - 1)
    pegDf['avgrate'] = pegDf.ix[:, 'incrate0':endfield].mean(axis=1)

    # 平均利润增长率（另一种计算方法）
#     pegDf['avgrate'] = 0
#     for i in range(sectionNum):
#         pegDf['avgrate'] += pegDf['incrate%d' % i]
#     pegDf['avgrate'] /= sectionNum

    # 计算每行指定列的平均绝对离差
    lirunmad = pegDf.ix[:, 'incrate0':endfield].mad(axis=1)
    # 计算每行指定列的平均值
#     lirunmean = df.ix[:, 'incrate0':'incrate5'].mean(axis=1).head()
    # 计算每行指定列的平均绝对离差率
    pegDf['madrate'] = lirunmad / pegDf['avgrate']

    # 增加股票名称
    nameDf = sqlrw.readStockListDf()
    pegDf = pd.merge(pegDf, nameDf, on='stockid', how='left')
#     print pegDf

    # 设置输出列与列顺序
    pegDf = pegDf[['stockid', 'name', 'pe', 'peg',
                   'next1YearPE',  'next2YearPE',  'next3YearPE',
                   'incrate0', 'incrate1', 'incrate2',
                   'incrate3', 'incrate4', 'incrate5',
                   'avgrate', 'madrate'
                   ]]
    return pegDf


def youzhiSelect(pegDf):
    """ 从估值分析中筛选出各项指标都合格的
    # 筛选条件：1、 peg不为空，且大于0，小于1
             2、平均增长率大于0
             3、平均绝对离差率小于一定范围（待确定）
    Parameters
    --------
    pegDf:DataFrame 股票估值分析列表， 结构同calGuzhi()函数输出格式

    Return
    --------
    DataFrame: 筛选后的估值分析表格
    """
    print pegDf.head()
    pegDf = pegDf[pegDf.peg.notnull()]
    pegDf = pegDf[(pegDf.peg > 0) & (pegDf.peg < 1) & (pegDf.avgrate > 0)]
    pegDf = pegDf[pegDf.madrate < 2]
#     pegDf = pegDf[['stockid', 'pe', 'peg',
#                    'next1YearPE',  'next2YearPE',  'next3YearPE',
#                    'incrate0', 'incrate1', 'incrate2',
#                    'incrate3', 'incrate4', 'incrate5',
#                    'avgrate'
#                    ]]
    print pegDf.head()
    print len(pegDf)
    return pegDf


def dfToCsvFile(df, filename):
    #     filename = u'.\\youzhi.csv'
    return df.to_csv(filename)


def testChigu():
    #     youzhiSelect()
    inFilename = '.\data\chigustockid.txt'
    outFilename = '.\data\chiguguzhi.csv'
#     testStockList = ['600519', '600999', '000651', '000333']
    testStockList = sqlrw.readStockListFromFile(inFilename)
    print testStockList
    df = calGuzhi(testStockList)
#     df = calGuzhi()
    print df.head()
    dfToCsvFile(df, outFilename)


def testShaixuan():
    df = calGuzhi()
    df = youzhiSelect(df)
    print df.head()
    outFilename = '.\data\youzhi.csv'
    dfToCsvFile(df, outFilename)
    outFilename = '.\data\youzhiid.txt'
    sqlrw.writeStockIDListToFile(df['stockid'], outFilename)

if __name__ == '__main__':
    logfilename = os.path.join(os.path.abspath(os.curdir),
                               'stockanalyse.log')
    formatStr = ('%(asctime)s %(filename)s[line:%(lineno)d] '
                 '%(levelname)s %(message)s')
    logging.basicConfig(level=logging.DEBUG,
                        format=formatStr,
                        filename=logfilename,
                        filemode='a')

    ##########################################################################
    # 定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象#
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    ##########################################################################

    timec = dt.datetime.now()
#    testStockID = u'601398'
    testStockID = u'000153'
    startDate = u'2016-04-30'
    endDate = u'2016-04-29'
    logging.info('===================start=====================')

    # 测试持股估值
    testChigu()

    # 测试筛选估值
    testShaixuan()

    # 测试TTMPE直方图、概率分布
#     ttmdf = sqlrw.readTTMPE(testStockID)
#     ttmdf = ttmdf[-200:]
#     ttmdf.plot()
#     print ttmdf.head()
#     print ttmdf.tail()
#
#     a = ttmdf.plot(kind='kde')
#     print 'type a :', type(a)
#
#     b = ttmdf.hist(bins=20)
#     print 'type b :', type(b)

#    c = ttmdf.hist().get_figure()
#    print 'type c :', type(c)

    timed = dt.datetime.now()
    logging.info('datamanage test took %s' % (timed - timec))
    logging.info('===================end=====================')
