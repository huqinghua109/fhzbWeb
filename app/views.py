# encoding: UTF-8
import os
import time, random
import pandas as pd
import numpy as np
from collections import OrderedDict

from flask import render_template, request, redirect, url_for,  Flask, url_for, send_from_directory, abort
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class, DEFAULTS,ALL
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

from app import app

from pymongo import MongoClient


# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
POSITION_DB_NAME = 'VnTrader_Position_Db'

SETTING_DB_NAME = 'VnTrader_Setting_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE1_DB_NAME = 'VnTrader_1Min_Db'
MINUTE3_DB_NAME = 'VnTrader_3Min_Db'
MINUTE5_DB_NAME = 'VnTrader_5Min_Db'
MINUTE15_DB_NAME = 'VnTrader_15Min_Db'
MINUTE30_DB_NAME = 'VnTrader_30Min_Db'
STRATEGY_DB_WEB = 'Strategy_Var_Param_WEBDB'
STRATEGY_DETAILLOG = 'Strategy_DetailLog'
STRATEGY_TRADELOG = 'Strategy_TradeLog'

c = MongoClient()
# try:
#     c = MongoClient(port=23429)
#     c['admin'].authenticate('Dean2', 'Dean0129')
# except:
#     print 'no mongoDB!'
db = STRATEGY_DB_WEB
dbTradeLog = STRATEGY_TRADELOG
dbDetailLog = STRATEGY_DETAILLOG

TradeMaxCount = 100
DetailMaxCount = 100

#--------------------------------------------------------------------
def getStrategyTradeData():
    strategyTradeLogs = []  # 分策略成交分组

    for collectionname in c[dbTradeLog].collection_names():
        staTraDict = {}
        staTraDict['strategy'] = collectionname
        staTraDict['trades'] = []
        l = c[dbTradeLog][collectionname].find().sort('_id', -1)
        for i in range(min(TradeMaxCount, l.count())):
            staTraDict['trades'].append([l[i]['datetime'], l[i]['context']])
        strategyTradeLogs.append(staTraDict)

    return strategyTradeLogs

#--------------------------------------------------------------------
def getStrategyDetailLog():
    strategyDetailLogs = []  # 分策略成交细节

    for collectionname in c[dbDetailLog].collection_names():
        straDetailDict = {}
        straDetailDict['strategy'] = collectionname
        straDetailDict['detailLogs'] = []
        l = c[dbDetailLog][collectionname].find().sort('_id', -1)
        for i in range(min(DetailMaxCount, l.count())):
            straDetailDict['detailLogs'].append([l[i]['time'], l[i]['trade'], l[i]['detail']])
        strategyDetailLogs.append(straDetailDict)

    return strategyDetailLogs

#--------------------------------------------------------------------
def getStrategyVarData():
    mytradeVars = []        # 各策略变量

    for collectionname in c[db].collection_names():
        l = c[db][collectionname].find_one()
        trade_d = {}        # 总成交信息缓存
        trade_d['name'] = collectionname 
        trade_d['value'] = {}
        for key,value in l['varsDict'].items():
            if key not in ['inited', 'trading', 'pos', 'localPosDict', 'historyDataVars']:
                trade_d['value'][key] = value

        # 将数据字典（key为stategyname, value为各策略数据）添加到列表
        if trade_d:
            mytradeVars.append(trade_d)

    return mytradeVars

#--------------------------------------------------------------------
def getStrategyHistoryData():
    myhistoryData = []      # 各策略历史数据

    for collectionname in c[db].collection_names():
        l = c[db][collectionname].find_one()
        history_d = {}      # 总历史数据信息缓存
        history_d['name'] = collectionname
        history_d['value'] = {}

        if 'historyDataVars' in l['varsDict']:
            for sym,var in l['varsDict']['historyDataVars'].items():
                for tradevar, pri in var.items():
                    if 'Array' in tradevar:
                        var.pop(tradevar)
                history_d['value'][sym] = var

        # 将数据字典（key为stategyname, value为各策略数据）添加到列表
        if history_d:
            myhistoryData.append(history_d)

    return myhistoryData

#--------------------------------------------------------------------
def getStrategyStatusData():
    myposts = []            # 各策略状态信息
    for collectionname in c[db].collection_names():
        l = c[db][collectionname].find_one()
        info_d = {}         # 总策略状态信息缓存
        d = {}              # 分策略状态信息缓存

        for k,v in l.items():
            if k == 'paramsDict':
                for key,value in v.items():
                    if key not in ['name', 'className']:
                        d[key] = value
            elif k == 'varsDict':
                trad = {}
                for key,value in v.items():
                    if key in ['inited', 'trading', 'pos', 'localPosDict']:
                        d[key] = value
            else:
                if k == 'name':
                    pass
        info_d['name'] = collectionname
        info_d['value'] = d

        # 将数据字典（key为stategyname, value为各策略数据）添加到列表
        if info_d:
            myposts.append(info_d)

    return myposts

############################################################################
############################################################################
# @app.route('/login', methods=['POST','GET'])
# def login():
#     error = None
#     if request.method == 'POST':
#         if request.form['username']=='admin':
#             return redirect(url_for('home.html',username=request.form['username']))
#         else:
#             error = 'Invalid username/password'
#     return render_template("login.html", error=error)

    # return render_template("home.html", username='SomeOne')
AuthList = ['Dean', 'He', 'Mochi', 'Dong', 'Ayang']
@app.route('/')
def home():
    return render_template("home.html")

# @app.route('/login', methods=['POST','GET'])
# def login():
#     error = None
#     if request.method == 'POST':
#         if request.form['username'] in AuthList:
#             return render_template("home.html", username=request.form['username'])
#             # return redirect(url_for('home',username=request.form['username']))
#         else:
#             error = 'Invalid username/password'
#     return render_template("login.html", error=error)
#------------------------------------------------------------------------------
# 分策略成交，按时间顺序显示
@app.route('/StrategyTrade', methods=['POST','GET'])
def trade_strategy():
    error = None
    if request.method == 'POST':
        if request.form['username'] in AuthList:
            strategyTradeLogs = getStrategyTradeData()
            return render_template("Trade_Strategy.html", title = 'strategy trade', strategyTradeLogs = strategyTradeLogs)
        else:
            error = 'Invalid username/password'
    return render_template("login.html", error=error)

#------------------------------------------------------------------------------
# 分策略细节，按时间顺序显示
@app.route('/StrategyDetail', methods=['POST','GET'])
def detail_strategy():
    error = None
    if request.method == 'POST':
        if request.form['username'] in AuthList:
            strategyDetailLogs = getStrategyDetailLog()
            return render_template("Detail_Strategy.html", title = 'strategy detailLogs', strategyDetailLogs = strategyDetailLogs)
        else:
            error = 'Invalid username/password'
    return render_template("login.html", error=error)
#------------------------------------------------------------------------------
# 分策略状态信息
@app.route('/strategyInfo', methods=['POST','GET'])
def strategy_info():
    error = None
    if request.method == 'POST':
        if request.form['username'] in AuthList:
            myposts = getStrategyStatusData()
            return render_template("Status_Strategy.html", title = 'strategy position', myposts = myposts)
        else:
            error = 'Invalid username/password'
    return render_template("login.html", error=error)

#------------------------------------------------------------------------------
# 分策略变量信息
@app.route('/strategyVars', methods=['POST','GET'])
def strategy_vars():
    error = None
    if request.method == 'POST':
        if request.form['username'] in AuthList:
            mytradeVars = getStrategyVarData()
            return render_template("Var_Strategy.html", title = 'strategy vars', mytradeVars = mytradeVars)
        else:
            error = 'Invalid username/password'
    return render_template("login.html", error=error)

#------------------------------------------------------------------------------
# 分策略历史数据
@app.route('/strategyHistoryData', methods=['POST','GET'])
def strategy_history():
    error = None
    if request.method == 'POST':
        if request.form['username'] in AuthList:
            myhistoryData = getStrategyHistoryData()
            return render_template("historyData_Strategy.html", title = 'strategy histortData', myhistoryData = myhistoryData)
        else:
            error = 'Invalid username/password'
    return render_template("login.html", error=error)

#------------------------------------------------------------------------------
# 玉米潮干粮价格折算
@app.route('/cornPrice', methods=['GET', 'POST'])
def cornCal():
    return render_template("cornCal.html",
        title = 'Corn Price Calculator')

#------------------------------------------------------------------------------
# 玉米现货价格录入
@app.route('/cornPriceInsert', methods=['GET', 'POST'])
def cornPriceInsert():
    if request.method == 'POST':
        if request.form['date1']:
            return u'insert successfully,近期点评：%s' % request.form['pinglun']
        else:
            return 'insert failed!'
    return render_template("cornPriceInsert.html",
        title = 'Corn Price Insert')

#------------------------------------------------------------------------------
# 玉米分析报告
@app.route('/cornAnalysisReport')
def cornAnalysisReport():
    
    return render_template("cornAnalysisReport.html",
        mydata = [random.randrange(100,900) for i in range(12)],
        title = 'Corn Analysis Report')
#------------------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
#------------------------------------------------------------------------------
obj = UploadSet('obj', ALL)
configure_uploads(app, obj)
patch_request_class(app)  # set maximum file size, default is 16MB


class UploadForm(FlaskForm):
    obj = FileField(validators=[FileAllowed(obj, u'English Only!'), FileRequired(u'Choose a file!')])
    submit = SubmitField(u'Upload')

@app.route('/manage')
def manage_file():
    files_list = os.listdir(app.config['UPLOADED_OBJ_DEST'])
    return render_template('manageReport.html', files_list=files_list)


@app.route('/open/<filename>')
def open_file(filename):
    file_url = obj.url(filename)
    return render_template('browser.html', file_url=file_url)

dirpath = os.path.join(os.path.dirname(app.root_path),'report')
@app.route('/download/<filename>')
def download_file(filename):
    if request.method=="GET":
        # if os.path.isfile(os.path.join('static', filename)):
        return send_from_directory(dirpath,filename,as_attachment=True)
        abort(404)

@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = obj.path(filename)
    os.remove(file_path)
    return redirect(url_for('manage_file'))

#------------------------------------------------------------------------------
# 谷物报告
@app.route('/grainReport', methods=['GET', 'POST'])
def grainReport():
    form = UploadForm()
    if form.validate_on_submit():
        for filename in request.files.getlist('obj'):
            # name = 'grain' + time.strftime("%Y%m%d_%H%M%S", time.localtime())
            name = 'grain_' + time.strftime("%Y%m%d%H%M%S", time.localtime()) + '_' + filename.filename
            obj.save(filename, name=name)
        success = True
    else:
        success = False

    files_list = []
    for file in os.listdir(app.config['UPLOADED_OBJ_DEST']):
        if 'grain' in file:
            files_list.append(file)
    return render_template('grainReport.html', form=form, success=success, files_list=files_list)

#------------------------------------------------------------------------------
# 油脂油料报告
@app.route('/oilSeedReport', methods=['GET', 'POST'])
def oilSeedReport():
    form = UploadForm()
    if form.validate_on_submit():
        for filename in request.files.getlist('obj'):
            name = 'oilseed_' + time.strftime("%Y%m%d%H%M%S", time.localtime()) + '_' + filename.filename
            obj.save(filename, name=name)
        success = True
    else:
        success = False

    files_list = []
    for file in os.listdir(app.config['UPLOADED_OBJ_DEST']):
        if 'oilseed' in file:
            files_list.append(file)
    return render_template('oilSeedReport.html', form=form, success=success, files_list=files_list)

#------------------------------------------------------------------------------
# 黑色产业报告
@app.route('/rbjiReport', methods=['GET', 'POST'])
def rbjiReport():
    form = UploadForm()
    if form.validate_on_submit():
        for filename in request.files.getlist('obj'):
            name = 'rbji_' + time.strftime("%Y%m%d%H%M%S", time.localtime()) + '_' + filename.filename
            obj.save(filename, name=name)
        success = True
    else:
        success = False

    files_list = []
    for file in os.listdir(app.config['UPLOADED_OBJ_DEST']):
        if 'rbji' in file:
            files_list.append(file)
    return render_template('rbjiReport.html', form=form, success=success, files_list=files_list)

#------------------------------------------------------------------------------
# 化工品报告
@app.route('/chemicalsReport', methods=['GET', 'POST'])
def chemicalsReport():
    form = UploadForm()
    if form.validate_on_submit():
        for filename in request.files.getlist('obj'):
            name = 'chemical_' + time.strftime("%Y%m%d%H%M%S", time.localtime()) + '_' + filename.filename
            obj.save(filename, name=name)
        success = True
    else:
        success = False

    files_list = []
    for file in os.listdir(app.config['UPLOADED_OBJ_DEST']):
        if 'chemical_' in file:
            files_list.append(file)
    return render_template('chemicalsReport.html', form=form, success=success, files_list=files_list)

#------------------------------------------------------------------------------
@app.route('/otherReport', methods=['GET', 'POST'])
def otherReport():
    form = UploadForm()
    if form.validate_on_submit():
        for filename in request.files.getlist('obj'):
            name = 'other_' + time.strftime("%Y%m%d%H%M%S", time.localtime()) + '_' + filename.filename
            obj.save(filename, name=name)
        success = True
    else:
        success = False

    files_list = []
    for file in os.listdir(app.config['UPLOADED_OBJ_DEST']):
        if 'other' in file:
            files_list.append(file)
    return render_template('chemicalsReport.html', form=form, success=success, files_list=files_list)
#------------------------------------------------------------------------------
# aboutus
@app.route('/aboutus')
def aboutus():
    return render_template("aboutus.html",
        title = 'aboutus')
#------------------------------------------------------------------------------
# basis chart
@app.route('/cornbasischart', methods=['GET', 'POST'])
def cornbasischart():
    # excel_path = "C:\\Users\\dell\\Desktop\\Quant\\fhzbWeb\\report\\CornBasisChart1.xlsx"
    corn_year_basis1_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='cornyearbasis1')
    corn_year_basis5_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='cornyearbasis5')
    corn_year_basis9_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='cornyearbasis9')
    corn_basis_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='cornbasis')
    # corn_year_basis_df = corn_year_basis_df.fillna(0)

    corn_year_basis1_l = []
    for date in corn_year_basis1_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2019basis1'] = corn_year_basis1_df.ix[date,'2019basis1']
        d['2018basis1'] = corn_year_basis1_df.ix[date,'2018basis1']
        d['2017basis1'] = corn_year_basis1_df.ix[date,'2017basis1']
        d['2016basis1'] = corn_year_basis1_df.ix[date,'2016basis1']
        d['2015basis1'] = corn_year_basis1_df.ix[date,'2015basis1']
        # d['2014basis1'] = corn_year_basis1_df.ix[date,'2014basis1']
        corn_year_basis1_l.append(d)

    corn_year_basis5_l = []
    for date in corn_year_basis5_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2019basis5'] = corn_year_basis5_df.ix[date,'2019basis5']
        d['2018basis5'] = corn_year_basis5_df.ix[date,'2018basis5']
        d['2017basis5'] = corn_year_basis5_df.ix[date,'2017basis5']
        d['2016basis5'] = corn_year_basis5_df.ix[date,'2016basis5']
        d['2015basis5'] = corn_year_basis5_df.ix[date,'2015basis5']
        # d['2014basis5'] = corn_year_basis5_df.ix[date,'2014basis5']
        corn_year_basis5_l.append(d)

    corn_year_basis9_l = []
    for date in corn_year_basis9_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2019basis9'] = corn_year_basis9_df.ix[date,'2019basis9']
        d['2018basis9'] = corn_year_basis9_df.ix[date,'2018basis9']
        d['2017basis9'] = corn_year_basis9_df.ix[date,'2017basis9']
        d['2016basis9'] = corn_year_basis9_df.ix[date,'2016basis9']
        d['2015basis9'] = corn_year_basis9_df.ix[date,'2015basis9']
        corn_year_basis9_l.append(d)

    corn_basis_l = []
    for i in range(len(corn_basis_df.index)):
        d = OrderedDict()
        d['date'] = corn_basis_df.index[i].date()
        d['basis1'] = corn_basis_df.iloc[i,0]
        d['basis5'] = corn_basis_df.iloc[i,1]
        d['basis9'] = corn_basis_df.iloc[i,2]
        corn_basis_l.append(d)

    return render_template("cornbasischart.html", corn_year_basis1_l=corn_year_basis1_l, corn_year_basis5_l=corn_year_basis5_l, corn_year_basis9_l=corn_year_basis9_l, corn_basis_l=corn_basis_l)

#------------------------------------------------------------------------------
# corn spread month & cs
@app.route('/cornspreadchart', methods=['GET', 'POST'])
def cornspreadchart():
    # excel_path = "C:\\Users\\dell\\Desktop\\Quant\\fhzbWeb\\report\\CornBasisChart1.xlsx"
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    corn_cs_spread1_year = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='corncsspread1year')
    corn_cs_spread5_year = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='corncsspread5year')
    corn_cs_spread9_year = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='corncsspread9year')
    corn_cs_spread_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='corncsspread')

    corn_91_spread_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='c9_1_year')
    corn_15_spread_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='c1_5_year')
    corn_59_spread_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='c5_9_year')

    corn_cs_spread1_year_l = []
    for date in corn_cs_spread1_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2016c_cs1'] = corn_cs_spread1_year.ix[date,'2016c-cs1']
        d['2017c_cs1'] = corn_cs_spread1_year.ix[date,'2017c-cs1']
        d['2018c_cs1'] = corn_cs_spread1_year.ix[date,'2018c-cs1']
        d['2019c_cs1'] = corn_cs_spread1_year.ix[date,'2019c-cs1']
        corn_cs_spread1_year_l.append(d)

    corn_cs_spread5_year_l = []
    for date in corn_cs_spread5_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2015c_cs5'] = corn_cs_spread5_year.ix[date,'2015c-cs5']
        d['2016c_cs5'] = corn_cs_spread5_year.ix[date,'2016c-cs5']
        d['2017c_cs5'] = corn_cs_spread5_year.ix[date,'2017c-cs5']
        d['2018c_cs5'] = corn_cs_spread5_year.ix[date,'2018c-cs5']
        d['2019c_cs5'] = corn_cs_spread5_year.ix[date,'2019c-cs5']
        corn_cs_spread5_year_l.append(d)

    corn_cs_spread9_year_l = []
    for date in corn_cs_spread9_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2015c_cs9'] = corn_cs_spread9_year.ix[date,'2015c-cs9']
        d['2016c_cs9'] = corn_cs_spread9_year.ix[date,'2016c-cs9']
        d['2017c_cs9'] = corn_cs_spread9_year.ix[date,'2017c-cs9']
        d['2018c_cs9'] = corn_cs_spread9_year.ix[date,'2018c-cs9']
        d['2019c_cs9'] = corn_cs_spread9_year.ix[date,'2019c-cs9']
        corn_cs_spread9_year_l.append(d)

    corn_91_year_l = []
    for date in corn_91_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        d['1809_1901'] = corn_91_spread_df.ix[date,'20189_1']
        d['1709_1801'] = corn_91_spread_df.ix[date,'20179_1']
        d['1609_1701'] = corn_91_spread_df.ix[date,'20169_1']
        d['1509_1601'] = corn_91_spread_df.ix[date,'20159_1']
        d['1409_1501'] = corn_91_spread_df.ix[date,'20149_1']
        corn_91_year_l.append(d)

    corn_15_year_l = []
    for date in corn_15_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        d['1901_1905'] = corn_15_spread_df.ix[date,'20191_5']
        d['1801_1805'] = corn_15_spread_df.ix[date,'20181_5']
        d['1701_1705'] = corn_15_spread_df.ix[date,'20171_5']
        d['1601_1605'] = corn_15_spread_df.ix[date,'20161_5']
        d['1501_1505'] = corn_15_spread_df.ix[date,'20151_5']
        corn_15_year_l.append(d)

    corn_59_year_l = []
    for date in corn_59_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        d['1905_1909'] = corn_59_spread_df.ix[date,'20195_9']
        d['1805_1809'] = corn_59_spread_df.ix[date,'20185_9']
        d['1705_1709'] = corn_59_spread_df.ix[date,'20175_9']
        d['1605_1609'] = corn_59_spread_df.ix[date,'20165_9']
        d['1505_1509'] = corn_59_spread_df.ix[date,'20155_9']
        corn_59_year_l.append(d)

    corn_cs_spread_df_l = []
    for i in range(len(corn_cs_spread_df.index)):
        d = OrderedDict()
        d['date'] = corn_cs_spread_df.index[i].date()
        d['corncs1'] = corn_cs_spread_df.iloc[i,0]
        d['corncs5'] = corn_cs_spread_df.iloc[i,1]
        d['corncs9'] = corn_cs_spread_df.iloc[i,2]
        corn_cs_spread_df_l.append(d)
    # print(corn_cs_spread_df_l)
    return render_template("cornspreadchart.html", corn_cs_spread1_year_l=corn_cs_spread1_year_l, corn_cs_spread5_year_l=corn_cs_spread5_year_l, corn_cs_spread9_year_l=corn_cs_spread9_year_l, corn_cs_spread_df_l=corn_cs_spread_df_l, corn_91_year_l=corn_91_year_l, corn_15_year_l=corn_15_year_l, corn_59_year_l=corn_59_year_l)
#------------------------------------------------------------------------------
# North Port Carryout & Price
@app.route('/portcarryout', methods=['GET', 'POST'])
def portcarryout():
    df = pd.read_excel(app.config['EXCEL_CORNDATA'], sheet_name='NSPort')
    df = df[1:-1]
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    l1 = []
    l2 = []
    l3 = []
    l4 = []
    for date in df.index:
        d1 = OrderedDict()
        d1['date'] = date
        d1['NorthCarryout'] = df.ix[date,'Unnamed: 20']
        d1['NorthCarryoutChange'] = df.ix[date,'Unnamed: 21']
        d1['JinzhouPrice'] = df.ix[date,'Unnamed: 4']
        l1.append(d1)

        d2 = OrderedDict()
        d2['date'] = date
        d2['GDCarryout'] = df.ix[date,'Unnamed: 25']
        d2['GDCarryoutChange'] = df.ix[date,'Unnamed: 26']
        d2['GDPrice'] = df.ix[date,'Unnamed: 27']
        l2.append(d2)

        d3 = OrderedDict()
        d3['date'] = date
        d3['CarryoutSpread'] = d2['GDCarryout']/d1['NorthCarryout']
        d3['profit'] = df.ix[date,'Unnamed: 30']
        l3.append(d3)

        d4 = OrderedDict()
        d4['date'] = date
        d4['GDPrice'] = df.ix[date,'Unnamed: 27']
        d4['InportCorn'] = df.ix[date,'Unnamed: 31']
        d4['Sorghum'] = df.ix[date,'Unnamed: 32']
        d4['Barley'] = df.ix[date,'Unnamed: 33']
        d4['GDInportSpread'] = d4['GDPrice']-d4['InportCorn']
        l4.append(d4)

    gatherN_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='gatherN_year_df')
    gatherS_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='gatherS_year_df')
    outN_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='outN_year_df')
    outS_df = pd.read_excel(app.config['EXCEL_BASIS'], sheet_name='outS_year_df')
    l5 = []
    for date in gatherN_df.index:
        d5 = OrderedDict()
        d5['date'] = date
        d5['gatherN_2016_2017'] = gatherN_df.ix[date,'2016/2017']
        d5['gatherN_2017_2018'] = gatherN_df.ix[date,'2017/2018']
        d5['gatherN_2018_2019'] = gatherN_df.ix[date,'2018/2019']
        d5['gatherS_2016_2017'] = gatherS_df.ix[date,'2016/2017']
        d5['gatherS_2017_2018'] = gatherS_df.ix[date,'2017/2018']
        d5['gatherS_2018_2019'] = gatherS_df.ix[date,'2018/2019']
        d5['outN_2016_2017'] = outN_df.ix[date,'2016/2017']
        d5['outN_2017_2018'] = outN_df.ix[date,'2017/2018']
        d5['outN_2018_2019'] = outN_df.ix[date,'2018/2019']
        d5['outS_2016_2017'] = outS_df.ix[date,'2016/2017']
        d5['outS_2017_2018'] = outS_df.ix[date,'2017/2018']
        d5['outS_2018_2019'] = outS_df.ix[date,'2018/2019']
        l5.append(d5)

    return render_template("portcarryout.html", l1=l1, l2=l2, l3=l3, l4=l4, l5=l5)
#------------------------------------------------------------------------------
# deepprocessing
@app.route('/deepprocessing')
def deepProcessing():
    df = pd.read_excel(app.config['EXCEL_CORNDATA'], sheet_name='DeepProcessing')
    deepprocessing_df = df.iloc[1:,:16]
    deepprocessing_df.columns = ['68cs_qg_kgl', '68cs_db_kgl', '68cs_sd_kgl', '68cs_hb_kgl', 'cs_hlj_lr', 'cs_jl_lr', 'cs_ln_lr', 'cs_hb_lr', 'cs_sd_lr', '35jj_qg_kgl', '35jj_db_kgl', '35jj_hn_kgl', 'jj_jl_lr', 'jj_hlj_lr', 'jj_hb_lr', 'jj_hn_lr']
    # print(deepprocessing_df.columns)
    l1 = []
    for date in deepprocessing_df.index:
        # print(date)
        d1 = OrderedDict()
        d1['date'] = date
        # d1['68cs_qg_kgl'] = deepprocessing_df.ix[date,'68cs_qg_kgl']
        d1['68cs_db_kgl'] = deepprocessing_df.ix[date,'68cs_db_kgl']
        d1['68cs_sd_kgl'] = deepprocessing_df.ix[date,'68cs_sd_kgl']
        # d1['68cs_hb_kgl'] = deepprocessing_df.ix[date,'68cs_hb_kgl']
        d1['cs_hlj_lr'] = deepprocessing_df.ix[date,'cs_hlj_lr']
        d1['cs_jl_lr'] = deepprocessing_df.ix[date,'cs_jl_lr']
        # d1['cs_ln_lr'] = deepprocessing_df.ix[date,'cs_ln_lr']
        # d1['cs_hb_lr'] = deepprocessing_df.ix[date,'cs_hb_lr']
        d1['cs_sd_lr'] = deepprocessing_df.ix[date,'cs_sd_lr']
        # d1['35jj_qg_kgl'] = deepprocessing_df.ix[date,'35jj_qg_kgl']
        d1['35jj_db_kgl'] = deepprocessing_df.ix[date,'35jj_db_kgl']
        d1['35jj_hn_kgl'] = deepprocessing_df.ix[date,'35jj_hn_kgl']
        d1['jj_jl_lr'] = deepprocessing_df.ix[date,'jj_jl_lr']
        d1['jj_hlj_lr'] = deepprocessing_df.ix[date,'jj_hlj_lr']
        # d1['jj_hb_lr'] = deepprocessing_df.ix[date,'jj_hb_lr']
        d1['jj_hn_lr'] = deepprocessing_df.ix[date,'jj_hn_lr']
        l1.append(d1)
    # print(l1)
    return render_template("deepprocessing.html", l1=l1)
    # return deepprocessing_df.to_html()
#------------------------------------------------------------------------------
# priceSummarize
@app.route('/priceSummarize')
def priceSummarize():
    df = pd.read_excel(app.config['EXCEL_CORNDATA'], sheet_name='summarize', header=None)
    region_df = df.ix[:7, :8]
    region_df.iloc[0,0] = region_df.iloc[0,0].date()

    deepcarryout_df = df.ix[:16, 10:14]
    deepcarryout_df.iloc[0,3] = deepcarryout_df.iloc[0,3].date()
    deepcarryout_df.iloc[0,4] = deepcarryout_df.iloc[0,4].date()
    for i in range(deepcarryout_df.shape[0]-1):
        deepcarryout_df.iloc[i+1,2] = '%.2f%%' % (deepcarryout_df.iloc[i+1,2]*100)

    feedcarryout_df = df.ix[:12, 15:20]
    feedcarryout_df.iloc[0,3] = feedcarryout_df.iloc[0,3].date()
    feedcarryout_df.iloc[0,4] = feedcarryout_df.iloc[0,4].date()
    for i in range(feedcarryout_df.shape[0]-1):
        feedcarryout_df.iloc[i+1,2] = '%.2f%%' % (feedcarryout_df.iloc[i+1,2]*100)
    # region_df = region_df.to_html(header=None, index=None, na_rep='', col_space=20, bold_rows=True)
    # carryout_df = carryout_df.to_html(header=None, index=None, na_rep='', col_space=20, bold_rows=True)
    # region_df = region_df.to_json()
    return render_template("priceSummarize.html", region_df=region_df, deepcarryout_df=deepcarryout_df, feedcarryout_df=feedcarryout_df)
    # return carryout_df
#------------------------------------------------------------------------------
# temptest
@app.route('/temptest', methods=['GET', 'POST'])
def temptest():
    excel_path = "E:\\Desktop\\fhzbWeb\\report\\CornData.xlsx"
    df = pd.read_excel(excel_path, sheet_name='NSPort')
    df = df[1:-1]
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    l1 = []
    l2 = []
    l3 = []
    for date in df.index:
        d = OrderedDict()
        d['date'] = date
        d['NorthCarryout'] = df.ix[date,'Unnamed: 20']
        d['NorthCarryoutChange'] = df.ix[date,'Unnamed: 21']
        d['JinzhouPrice'] = df.ix[date,'Unnamed: 4']
        l1.append(d)
    # for i in range(len(corn_basis_df.index)):
    #     d = OrderedDict()
    #     d['date'] = corn_basis_df.index[i].date()
    #     d['basis1'] = corn_basis_df.iloc[i,0]
    #     d['basis5'] = corn_basis_df.iloc[i,1]
    #     d['basis9'] = corn_basis_df.iloc[i,2]
    #     l7.append(d)
    # print(l5)
    # print(type(l5))
    # print(type(l5[5]))
    # mydf = s.to_json()
    # print(mydf)
    # if request.method == 'POST':
    #     print 1111111111111
    # elif request.method == 'GET':
    #     print 22222
    return render_template("temptest.html", l1=l1, l2=l2, l3=l3)

