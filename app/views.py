# encoding: UTF-8
import os
import time, random
import pandas as pd
import numpy as np

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
# temptest
@app.route('/temptest', methods=['GET', 'POST'])
def temptest():
    excel_path = "C:\\Users\\dell\\Desktop\\Quant\\fhzbWeb\\report\\CornBasisChart1.xlsx"
    corn_year_basis_df = pd.read_excel(excel_path, sheet_name='cornyearbasis')
    corn_basis_df = pd.read_excel(excel_path, sheet_name='cornbasis')
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    l1 = ['a','v','b','c','d']
    l1 = list(corn_year_basis_df.index)
    l2 = [10,12,13,15,20]
    l3 = [11,14,15,18,22]
    l4 = {'a':1,'b':2,'c':3,'d':4,'e':4}
    l5 = list(corn_year_basis_df.ix[:,'2018basis1'])
    l6 = []
    l7 = []
    for date in corn_year_basis_df.index:
        d = {}
        d['date'] = date
        d['2018basis1'] = corn_year_basis_df.ix[date,'2018basis1']
        d['2018basis5'] = corn_year_basis_df.ix[date,'2018basis5']
        d['2018basis9'] = corn_year_basis_df.ix[date,'2018basis9']
        l6.append(d)
    for i in range(len(corn_basis_df.index)):
        d = {}
        d['date'] = corn_basis_df.index[i].date()
        d['basis1'] = corn_basis_df.iloc[i,0]
        d['basis5'] = corn_basis_df.iloc[i,1]
        d['basis9'] = corn_basis_df.iloc[i,2]
        l7.append(d)
    # print(l5)
    # print(type(l5))
    # print(type(l5[5]))
    # mydf = corn_year_basis_df.to_json()
    # print(mydf)
    # if request.method == 'POST':
    #     print 1111111111111
    # elif request.method == 'GET':
    #     print 22222
    return render_template("temptest.html", corn_year_basis_df=corn_year_basis_df, l1=l1, l2=l2, l3=l3, l4=l5, l6=l6, l7=l7)