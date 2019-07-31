# encoding: UTF-8
import os
import random
import datetime as dtt
import pandas as pd
import numpy as np
from collections import OrderedDict

from flask import render_template, request, redirect, url_for,  Flask, url_for, send_from_directory, abort
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class, DEFAULTS,ALL
from flask_wtf import FlaskForm
from flask_login import UserMixin, LoginManager, login_required, login_user
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

from app import app

from pymongo import MongoClient

from bs4 import BeautifulSoup
import urllib.request


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

c = None
# c = MongoClient()
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
# 登录与登出功能实现
# 如果需要页面是授权用户才可见，在相应视图函数前加上 @login_required 装饰器进行声明即可，@login_required 装饰器对于未登录用户访问，默认处理是重定向到 LoginManager.login_view 所指定的视图
class User(UserMixin):
    pass


users = [
    {'id':'dean', 'username':'dean', 'password':'123456'},
    {'id':'guest', 'username':'guest', 'password':'123456'}
]    

def query_user(user_id):
    for user in users:
        if user_id == user['id']:
            return user

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = 'Access denied.'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if query_user(user_id) is not None:
        curr_user = User()
        curr_user.id = user_id

        return curr_user
# 登入功能实现
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('userid')
        user = query_user(user_id)
        if user is not None and request.form['password'] == user['password']:

            curr_user = User()
            curr_user.id = user_id

            # 通过Flask-Login的login_user方法登录用户
            login_user(curr_user)

            next = request.args.get('next')
            return redirect(next)

        else:
            error = '用户名或密码错误!'
            return render_template('login.html', error=error)

    # GET 请求
    return render_template('login.html')

# 登出功能实现
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out successfully!'
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

#--------------------------------------------------------------------
def getDroughtUrl():
    datestr = (dtt.datetime.now()-dtt.timedelta(1)).strftime("%Y%m%d")
    date5str = (dtt.datetime.now()-dtt.timedelta(6)).strftime("%Y%m%d")
    date10str = (dtt.datetime.now()-dtt.timedelta(11)).strftime("%Y%m%d")
    date365str = (dtt.datetime.now()-dtt.timedelta(366)).strftime("%Y%m%d")
    date730str = (dtt.datetime.now()-dtt.timedelta(731)).strftime("%Y%m%d")
    # date1095str = (dtt.datetime.now()-dtt.timedelta(1096)).strftime("%Y%m%d")
    urlToday = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+datestr+"_00000000.png"
    url5 = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+date5str+"_00000000.png"
    url10 = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+date10str+"_00000000.png"
    url365 = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+date365str+"_00000000.png"
    url730 = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+date730str+"_00000000.png"
    nongyeDroughturl = getNongyeDroughtUrl()
    return [urlToday, url5, url10, url365, url730, nongyeDroughturl]
#--------------------------------------------------------------------
def getRainfallUrl():
    datestr = dtt.datetime.now().strftime("%Y%m%d")[2:]
    date5str = (dtt.datetime.now()-dtt.timedelta(5)).strftime("%Y%m%d")[2:]
    date10str = (dtt.datetime.now()-dtt.timedelta(10)).strftime("%Y%m%d")[2:]
    date365str = (dtt.datetime.now()-dtt.timedelta(365)).strftime("%Y%m%d")[2:]
    date730str = (dtt.datetime.now()-dtt.timedelta(730)).strftime("%Y%m%d")[2:]
    date1095str = (dtt.datetime.now()-dtt.timedelta(1095)).strftime("%Y%m%d")[2:]
    urlToday = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+datestr+".gif"
    url5 = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+date5str+".gif"
    url10 = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+date10str+".gif"
    url365 = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+date365str+".gif"
    url730 = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+date730str+".gif"
    url1095 = "https://cmdp.ncc-cma.net/Monitoring/DailyMonitoring/ra20_/ra20_"+date1095str+".gif"
    return [urlToday, url5, url10, url365, url730, url1095]
#--------------------------------------------------------------------
def getNongyeDroughtUrl():
    nmcurl = "http://www.nmc.cn/publish/agro/disastersmonitoring/Agricultural_Drought_Monitoring.htm"
    response = urllib.request.urlopen(nmcurl)
    soup = BeautifulSoup(response, "html.parser")
    nongyeDroughturl = soup.find('img', id='imgpath').get('src')
    return nongyeDroughturl
#--------------------------------------------------------------------
def getPrecipitationUrl():
    baseUrl = "http://www.nmc.cn/publish/precipitation/1-day.html"
    response = urllib.request.urlopen(baseUrl)
    soup = BeautifulSoup(response, "html.parser")

    # res = soup.find('ul', id='mycarousel').get("data-original")
    res = soup.find('ul', id='mycarousel')
    # res = soup.find_all('li')
    # select = soup.select("#mycarousel")
    # print(len(res.find_all('img')))
    precipitationUrl_l = []
    for i in range(7):
        preurl = res.find_all('img')[i].get("data-original")
        precipitationUrl_l.append(preurl)
    return precipitationUrl_l
#--------------------------------------------------------------------
def getTemperatureUrl():
    baseUrl = "http://www.nmc.cn/publish/temperature/hight/24hour.html"
    response = urllib.request.urlopen(baseUrl)
    soup = BeautifulSoup(response, "html.parser")

    res = soup.find('ul', id='mycarousel')
    temperatureUrl_l = []
    for i in range(7):
        temurl = res.find_all('img')[i].get("data-original")
        temperatureUrl_l.append(temurl)
    return temperatureUrl_l

#--------------------------------------------------------------------
#--------------------------------------------------------------------
#--------------------------------------------------------------------
############################################################################
@app.route('/home111')
def starthome():
    return "今日天气好晴朗,处处好风光 好风光，蝴蝶儿忙 蜜蜂也忙，小鸟儿忙着 白云也忙。"
############################################################################
@app.route('/')
def home():
    b9= getCornYearBasis09()
    
    datestr = (dtt.datetime.now()-dtt.timedelta(1)).strftime("%Y%m%d")
    droughturl = "https://cmdp.ncc-cma.net/download/Drought/MCI/CMDP_DSTR_ACHN_L88_DATA_ELEMENT_PDAY_YMD_107578_"+datestr+"_00000000.png"

    nongyeDroughturl = getNongyeDroughtUrl()

    return render_template("home.html", corn_year_basis9_l=b9, droughturl=droughturl, nongyeDroughturl=nongyeDroughturl)
    # return render_template("home.html")

#------------------------------------------------------------------------------
# 天气情况
@app.route('/tianqiqingkuang')
def tianqiqingkuang():
    rainFallUrl_l = getRainfallUrl()
    droughtUrl_l = getDroughtUrl()
    return render_template("tianqiqingkuang.html", rainFallUrl_l=rainFallUrl_l, droughtUrl_l=droughtUrl_l, title="天气情况")
#------------------------------------------------------------------------------
# 降水与气温7天预报
@app.route('/tianqiyubao7')
def tianqiyubao7():
    precipitationUrl_l = getPrecipitationUrl()
    temperatureUrl_l = getTemperatureUrl()
    return render_template("tianqiyubao7.html", precipitationUrl_l=precipitationUrl_l, temperatureUrl_l=temperatureUrl_l, title="天气预报-7天")
#------------------------------------------------------------------------------
# 分策略成交，按时间顺序显示
@app.route('/StrategyTrade', methods=['POST','GET'])
@login_required
def trade_strategy():
    strategyTradeLogs = getStrategyTradeData()
    return render_template("Trade_Strategy.html", title = 'strategy trade', strategyTradeLogs = strategyTradeLogs)

#------------------------------------------------------------------------------
# 分策略细节，按时间顺序显示
@app.route('/StrategyDetail', methods=['POST','GET'])
@login_required
def detail_strategy():
    strategyDetailLogs = getStrategyDetailLog()
    return render_template("Detail_Strategy.html", title = 'strategy detailLogs', strategyDetailLogs = strategyDetailLogs)
#------------------------------------------------------------------------------
# 分策略状态信息
@app.route('/strategyInfo', methods=['POST','GET'])
@login_required
def strategy_info():
    myposts = getStrategyStatusData()
    return render_template("Status_Strategy.html", title = 'strategy position', myposts = myposts)

#------------------------------------------------------------------------------
# 分策略变量信息
@app.route('/strategyVars', methods=['POST','GET'])
@login_required
def strategy_vars():
    mytradeVars = getStrategyVarData()
    return render_template("Var_Strategy.html", title = 'strategy vars', mytradeVars = mytradeVars)

#------------------------------------------------------------------------------
# 分策略历史数据
@app.route('/strategyHistoryData', methods=['POST','GET'])
@login_required
def strategy_history():
    myhistoryData = getStrategyHistoryData()
    return render_template("historyData_Strategy.html", title = 'strategy histortData', myhistoryData = myhistoryData)

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
obj = UploadSet('obj', ALL)
configure_uploads(app, obj)
patch_request_class(app)  # set maximum file size, default is 16MB


class UploadForm(FlaskForm):
    obj = FileField(validators=[FileAllowed(obj, u'English Only!'), FileRequired(u'Choose a file!')])
    submit = SubmitField(u'Upload')

@app.route('/manage')
@login_required
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
        # abort(404)

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
def getCornYearBasis01():
    corn_year_basis1_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis1')

    corn_year_basis1_l = []
    for date in corn_year_basis1_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis1'] = corn_year_basis1_df.loc[date,'2020basis1']
        d['2019basis1'] = corn_year_basis1_df.loc[date,'2019basis1']
        d['2018basis1'] = corn_year_basis1_df.loc[date,'2018basis1']
        d['2017basis1'] = corn_year_basis1_df.loc[date,'2017basis1']
        d['2016basis1'] = corn_year_basis1_df.loc[date,'2016basis1']
        d['2015basis1'] = corn_year_basis1_df.loc[date,'2015basis1']
        d['2014basis1'] = corn_year_basis1_df.loc[date,'2014basis1']
        corn_year_basis1_l.append(d)

    return corn_year_basis1_l
#------------------------------------------------------------------------------
def getCornYearBasis05():
    corn_year_basis5_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis5')

    corn_year_basis5_l = []
    for date in corn_year_basis5_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis5'] = corn_year_basis5_df.loc[date,'2020basis5']
        d['2019basis5'] = corn_year_basis5_df.loc[date,'2019basis5']
        d['2018basis5'] = corn_year_basis5_df.loc[date,'2018basis5']
        d['2017basis5'] = corn_year_basis5_df.loc[date,'2017basis5']
        d['2016basis5'] = corn_year_basis5_df.loc[date,'2016basis5']
        d['2015basis5'] = corn_year_basis5_df.loc[date,'2015basis5']
        d['2014basis5'] = corn_year_basis5_df.loc[date,'2014basis5']
        corn_year_basis5_l.append(d)

    return corn_year_basis5_l
#------------------------------------------------------------------------------
def getCornYearBasis09():
    corn_year_basis9_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis9')

    corn_year_basis9_l = []
    for date in corn_year_basis9_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis9'] = corn_year_basis9_df.loc[date,'2020basis9']
        d['2019basis9'] = corn_year_basis9_df.loc[date,'2019basis9']
        d['2018basis9'] = corn_year_basis9_df.loc[date,'2018basis9']
        d['2017basis9'] = corn_year_basis9_df.loc[date,'2017basis9']
        d['2016basis9'] = corn_year_basis9_df.loc[date,'2016basis9']
        d['2015basis9'] = corn_year_basis9_df.loc[date,'2015basis9']
        d['2014basis9'] = corn_year_basis9_df.loc[date,'2014basis9']
        corn_year_basis9_l.append(d)

    return corn_year_basis9_l
#------------------------------------------------------------------------------
def getCornBasis():
    # excel_path = "C:\\Users\\dell\\Desktop\\Quant\\fhzbWeb\\report\\CornBasisChart1.xlsx"
    corn_year_basis1_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis1')
    corn_year_basis5_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis5')
    corn_year_basis9_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornyearbasis9')
    corn_basis_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cornbasis', index_col =0)
    # corn_year_basis_df = corn_year_basis_df.fillna(0)

    corn_year_basis1_l = []
    for date in corn_year_basis1_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis1'] = corn_year_basis1_df.loc[date,'2020basis1']
        d['2019basis1'] = corn_year_basis1_df.loc[date,'2019basis1']
        d['2018basis1'] = corn_year_basis1_df.loc[date,'2018basis1']
        d['2017basis1'] = corn_year_basis1_df.loc[date,'2017basis1']
        d['2016basis1'] = corn_year_basis1_df.loc[date,'2016basis1']
        d['2015basis1'] = corn_year_basis1_df.loc[date,'2015basis1']
        d['2014basis1'] = corn_year_basis1_df.loc[date,'2014basis1']
        corn_year_basis1_l.append(d)

    corn_year_basis5_l = []
    for date in corn_year_basis5_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis5'] = corn_year_basis5_df.loc[date,'2020basis5']
        d['2019basis5'] = corn_year_basis5_df.loc[date,'2019basis5']
        d['2018basis5'] = corn_year_basis5_df.loc[date,'2018basis5']
        d['2017basis5'] = corn_year_basis5_df.loc[date,'2017basis5']
        d['2016basis5'] = corn_year_basis5_df.loc[date,'2016basis5']
        d['2015basis5'] = corn_year_basis5_df.loc[date,'2015basis5']
        d['2014basis5'] = corn_year_basis5_df.loc[date,'2014basis5']
        corn_year_basis5_l.append(d)

    corn_year_basis9_l = []
    for date in corn_year_basis9_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2020basis9'] = corn_year_basis9_df.loc[date,'2020basis9']
        d['2019basis9'] = corn_year_basis9_df.loc[date,'2019basis9']
        d['2018basis9'] = corn_year_basis9_df.loc[date,'2018basis9']
        d['2017basis9'] = corn_year_basis9_df.loc[date,'2017basis9']
        d['2016basis9'] = corn_year_basis9_df.loc[date,'2016basis9']
        d['2015basis9'] = corn_year_basis9_df.loc[date,'2015basis9']
        d['2014basis9'] = corn_year_basis9_df.loc[date,'2014basis9']
        corn_year_basis9_l.append(d)

    corn_basis_l = []
    for i in range(len(corn_basis_df.index)):
        d = OrderedDict()
        d['date'] = corn_basis_df.index[i].date()
        d['basis1'] = corn_basis_df.iloc[i,0]
        d['basis5'] = corn_basis_df.iloc[i,1]
        d['basis9'] = corn_basis_df.iloc[i,2]
        corn_basis_l.append(d)

    return corn_year_basis1_l, corn_year_basis5_l, corn_year_basis9_l, corn_basis_l
#------------------------------------------------------------------------------
# basis chart
@app.route('/cornbasischart', methods=['GET', 'POST'])
# @login_required
def cornbasischart():
    corn_year_basis1_l, corn_year_basis5_l, corn_year_basis9_l, corn_basis_l = getCornBasis()

    return render_template("cornbasischart.html", corn_year_basis1_l=corn_year_basis1_l, corn_year_basis5_l=corn_year_basis5_l, corn_year_basis9_l=corn_year_basis9_l, corn_basis_l=corn_basis_l)

#------------------------------------------------------------------------------
# corn spread month & cs
@app.route('/cornspreadchart', methods=['GET', 'POST'])
# @login_required
def cornspreadchart():
    # excel_path = "C:\\Users\\dell\\Desktop\\Quant\\fhzbWeb\\report\\CornBasisChart1.xlsx"
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    corn_cs_spread1_year = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='corncsspread1year')
    corn_cs_spread5_year = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='corncsspread5year')
    corn_cs_spread9_year = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='corncsspread9year')
    corn_cs_spread_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='corncsspread', index_col =0)

    corn_91_spread_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='c9_1_year')
    corn_15_spread_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='c1_5_year')
    corn_59_spread_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='c5_9_year')

    corn_cs_spread1_year_l = []
    for date in corn_cs_spread1_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2016c_cs1'] = corn_cs_spread1_year.loc[date,'2016c-cs1']
        d['2017c_cs1'] = corn_cs_spread1_year.loc[date,'2017c-cs1']
        d['2018c_cs1'] = corn_cs_spread1_year.loc[date,'2018c-cs1']
        d['2019c_cs1'] = corn_cs_spread1_year.loc[date,'2019c-cs1']
        d['2020c_cs1'] = corn_cs_spread1_year.loc[date,'2020c-cs1']
        corn_cs_spread1_year_l.append(d)

    corn_cs_spread5_year_l = []
    for date in corn_cs_spread5_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2015c_cs5'] = corn_cs_spread5_year.loc[date,'2015c-cs5']
        d['2016c_cs5'] = corn_cs_spread5_year.loc[date,'2016c-cs5']
        d['2017c_cs5'] = corn_cs_spread5_year.loc[date,'2017c-cs5']
        d['2018c_cs5'] = corn_cs_spread5_year.loc[date,'2018c-cs5']
        d['2019c_cs5'] = corn_cs_spread5_year.loc[date,'2019c-cs5']
        d['2020c_cs5'] = corn_cs_spread5_year.loc[date,'2020c-cs5']
        corn_cs_spread5_year_l.append(d)

    corn_cs_spread9_year_l = []
    for date in corn_cs_spread9_year.index:
        d = OrderedDict()
        d['date'] = date
        d['2015c_cs9'] = corn_cs_spread9_year.loc[date,'2015c-cs9']
        d['2016c_cs9'] = corn_cs_spread9_year.loc[date,'2016c-cs9']
        d['2017c_cs9'] = corn_cs_spread9_year.loc[date,'2017c-cs9']
        d['2018c_cs9'] = corn_cs_spread9_year.loc[date,'2018c-cs9']
        d['2019c_cs9'] = corn_cs_spread9_year.loc[date,'2019c-cs9']
        d['2020c_cs9'] = corn_cs_spread9_year.loc[date,'2020c-cs9']
        corn_cs_spread9_year_l.append(d)

    corn_91_year_l = []
    for date in corn_91_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        # d['2009_2101'] = corn_91_spread_df.loc[date,'20209_1']
        d['1909_2001'] = corn_91_spread_df.loc[date,'20199_1']
        d['1809_1901'] = corn_91_spread_df.loc[date,'20189_1']
        d['1709_1801'] = corn_91_spread_df.loc[date,'20179_1']
        d['1609_1701'] = corn_91_spread_df.loc[date,'20169_1']
        d['1509_1601'] = corn_91_spread_df.loc[date,'20159_1']
        d['1409_1501'] = corn_91_spread_df.loc[date,'20149_1']
        corn_91_year_l.append(d)

    corn_15_year_l = []
    for date in corn_15_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        # d['2101_2105'] = corn_15_spread_df.loc[date,'20211_5']
        d['2001_2005'] = corn_15_spread_df.loc[date,'20201_5']
        d['1901_1905'] = corn_15_spread_df.loc[date,'20191_5']
        d['1801_1805'] = corn_15_spread_df.loc[date,'20181_5']
        d['1701_1705'] = corn_15_spread_df.loc[date,'20171_5']
        d['1601_1605'] = corn_15_spread_df.loc[date,'20161_5']
        d['1501_1505'] = corn_15_spread_df.loc[date,'20151_5']
        corn_15_year_l.append(d)

    corn_59_year_l = []
    for date in corn_59_spread_df.index:
        d = OrderedDict()
        d['date'] = date
        d['2005_2009'] = corn_59_spread_df.loc[date,'20205_9']
        d['1905_1909'] = corn_59_spread_df.loc[date,'20195_9']
        d['1805_1809'] = corn_59_spread_df.loc[date,'20185_9']
        d['1705_1709'] = corn_59_spread_df.loc[date,'20175_9']
        d['1605_1609'] = corn_59_spread_df.loc[date,'20165_9']
        d['1505_1509'] = corn_59_spread_df.loc[date,'20155_9']
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
    north_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='northPort', index_col=0)
    GD_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='GDPort', index_col=0)
    l1 = []
    l2 = []
    l3 = []
    l4 = []
    for date in north_df.index:
        d1 = OrderedDict()
        d1['date'] = date
        d1['NorthCarryout'] = round(north_df.loc[date,'northCarryOutSum'],2)
        d1['NorthCarryoutChange'] = round(north_df.loc[date,'weekchange'],2)
        d1['JinzhouPrice'] = north_df.loc[date,'jinzhou']
        l1.append(d1)
    for date in GD_df.index:
        d2 = OrderedDict()
        d2['date'] = date
        d2['GDCarryout'] = round(GD_df.loc[date,'GDCarryOutSum'],2)
        d2['GDnmCarryout'] = round(GD_df.loc[date,'gdnmcarry'],2)
        d2['GDjkCarryout'] = round(GD_df.loc[date,'gdjkcarry'],2)
        d2['GDCarryoutChange'] = round(GD_df.loc[date,'weekchange'],2)
        d2['GDPrice'] = GD_df.loc[date,'guangdong']
        l2.append(d2)

        d3 = OrderedDict()
        d3['date'] = date
        d3['CarryoutSpread'] = round(GD_df.loc[date,'GDCarryOutSum']/GD_df.loc[date,'northCarryOutSum'],2)
        d3['profit'] = GD_df.loc[date,'ntosProfit']
        l3.append(d3)

        if date > dtt.datetime(2017,1,1):
            d4 = OrderedDict()
            d4['date'] = date
            d4['GDPrice'] = GD_df.loc[date,'guangdong']
            d4['InportCorn'] = GD_df.loc[date,'importcorn']
            d4['Sorghum'] = GD_df.loc[date,'importUSAsorghum']
            d4['Barley'] = GD_df.loc[date,'importbarley']
            d4['GDInportSpread'] = GD_df.loc[date,'guangdong'] - GD_df.loc[date,'importcorn']
            l4.append(d4)

    return render_template("portcarryout.html", l1=l1, l2=l2, l3=l3, l4=l4)
#------------------------------------------------------------------------------
# gather and out
@app.route('/gatherandout', methods=['GET', 'POST'])
def gatherandout():
    gatherN_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='gatherN_year', index_col=0)
    gatherN_df = gatherN_df.round(decimals=2)
    gatherNcumsum_df = gatherN_df.cumsum(0)
    gatherNcumsum_df = gatherNcumsum_df.round(decimals=2)

    gatherS_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='gatherGD_year', index_col=0)
    gatherS_df = gatherS_df.round(decimals=2)
    gatherScumsum_df = gatherS_df.cumsum(0)
    gatherScumsum_df = gatherScumsum_df.round(decimals=2)

    outN_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='outN_year', index_col=0)
    outN_df = outN_df.round(decimals=2)
    outNcumsum_df = outN_df.cumsum(0)
    outNcumsum_df = outNcumsum_df.round(decimals=2)

    outS_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='outGD_year', index_col=0)
    outS_df = outS_df.round(decimals=2)
    outScumsum_df = outS_df.cumsum(0)
    outScumsum_df = outScumsum_df.round(decimals=2)

    l5 = []
    for date in gatherN_df.index:
        d5 = OrderedDict()
        d5['date'] = date
        d5['gatherN_2016_2017'] = gatherN_df.loc[date,'2016/2017']
        d5['gatherN_2017_2018'] = gatherN_df.loc[date,'2017/2018']
        d5['gatherN_2018_2019'] = gatherN_df.loc[date,'2018/2019']
        d5['gatherS_2016_2017'] = gatherS_df.loc[date,'2016/2017']
        d5['gatherS_2017_2018'] = gatherS_df.loc[date,'2017/2018']
        d5['gatherS_2018_2019'] = gatherS_df.loc[date,'2018/2019']
        d5['outN_2016_2017'] = outN_df.loc[date,'2016/2017']
        d5['outN_2017_2018'] = outN_df.loc[date,'2017/2018']
        d5['outN_2018_2019'] = outN_df.loc[date,'2018/2019']
        d5['outS_2016_2017'] = outS_df.loc[date,'2016/2017']
        d5['outS_2017_2018'] = outS_df.loc[date,'2017/2018']
        d5['outS_2018_2019'] = outS_df.loc[date,'2018/2019']
        l5.append(d5)
    l1 = []
    for date in gatherNcumsum_df.index:
        d1 = OrderedDict()
        d1['date'] = date
        d1['gatherN_2016_2017'] = gatherNcumsum_df.loc[date,'2016/2017']
        d1['gatherN_2017_2018'] = gatherNcumsum_df.loc[date,'2017/2018']
        d1['gatherN_2018_2019'] = gatherNcumsum_df.loc[date,'2018/2019']
        d1['gatherS_2016_2017'] = gatherScumsum_df.loc[date,'2016/2017']
        d1['gatherS_2017_2018'] = gatherScumsum_df.loc[date,'2017/2018']
        d1['gatherS_2018_2019'] = gatherScumsum_df.loc[date,'2018/2019']
        d1['outN_2016_2017'] = outNcumsum_df.loc[date,'2016/2017']
        d1['outN_2017_2018'] = outNcumsum_df.loc[date,'2017/2018']
        d1['outN_2018_2019'] = outNcumsum_df.loc[date,'2018/2019']
        d1['outS_2016_2017'] = outScumsum_df.loc[date,'2016/2017']
        d1['outS_2017_2018'] = outScumsum_df.loc[date,'2017/2018']
        d1['outS_2018_2019'] = outScumsum_df.loc[date,'2018/2019']
        l1.append(d1)

    gatherBBW_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='gatherBBW_year', index_col=0)
    gatherBBW_df = gatherBBW_df.round(decimals=2)
    gatherBBWcumsum_df = gatherBBW_df.cumsum(0)
    gatherBBWcumsum_df = gatherBBWcumsum_df.round(decimals=2)

    gatherZZ_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='gatherZZ_year', index_col=0)
    gatherZZ_df = gatherZZ_df.round(decimals=2)
    gatherZZcumsum_df = gatherZZ_df.cumsum(0)
    gatherZZcumsum_df = gatherZZcumsum_df.round(decimals=2)

    outBBW_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='outBBW_year', index_col=0)
    outBBW_df = outBBW_df.round(decimals=2)
    outBBWcumsum_df = outBBW_df.cumsum(0)
    outBBWcumsum_df = outBBWcumsum_df.round(decimals=2)

    outZZ_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='outZZ_year', index_col=0)
    outZZ_df = outZZ_df.round(decimals=2)
    outZZcumsum_df = outZZ_df.cumsum(0)
    outZZcumsum_df = outZZcumsum_df.round(decimals=2)

    l6 = []
    for date in gatherBBW_df.index:
        d6 = OrderedDict()
        d6['date'] = date
        d6['gatherBBW_2016_2017'] = gatherBBW_df.loc[date,'2016/2017']
        d6['gatherBBW_2017_2018'] = gatherBBW_df.loc[date,'2017/2018']
        d6['gatherBBW_2018_2019'] = gatherBBW_df.loc[date,'2018/2019']
        d6['gatherZZ_2016_2017'] = gatherZZ_df.loc[date,'2016/2017']
        d6['gatherZZ_2017_2018'] = gatherZZ_df.loc[date,'2017/2018']
        d6['gatherZZ_2018_2019'] = gatherZZ_df.loc[date,'2018/2019']
        d6['outBBW_2016_2017'] = outBBW_df.loc[date,'2016/2017']
        d6['outBBW_2017_2018'] = outBBW_df.loc[date,'2017/2018']
        d6['outBBW_2018_2019'] = outBBW_df.loc[date,'2018/2019']
        d6['outZZ_2016_2017'] = outZZ_df.loc[date,'2016/2017']
        d6['outZZ_2017_2018'] = outZZ_df.loc[date,'2017/2018']
        d6['outZZ_2018_2019'] = outZZ_df.loc[date,'2018/2019']
        l6.append(d6)
    l2 = []
    for date in gatherBBW_df.index:
        d2 = OrderedDict()
        d2['date'] = date
        # d2['gatherBBW_2016_2017'] = gatherBBWcumsum_df.loc[date,'2016/2017']
        # d2['gatherBBW_2017_2018'] = gatherBBWcumsum_df.loc[date,'2017/2018']
        d2['gatherBBW_2018_2019'] = gatherBBWcumsum_df.loc[date,'2018/2019']
        # d2['gatherZZ_2016_2017'] = gatherZZcumsum_df.loc[date,'2016/2017']
        d2['gatherZZ_2017_2018'] = gatherZZcumsum_df.loc[date,'2017/2018']
        d2['gatherZZ_2018_2019'] = gatherZZcumsum_df.loc[date,'2018/2019']
        # d2['outBBW_2016_2017'] = outBBWcumsum_df.loc[date,'2016/2017']
        # d2['outBBW_2017_2018'] = outBBWcumsum_df.loc[date,'2017/2018']
        d2['outBBW_2018_2019'] = outBBWcumsum_df.loc[date,'2018/2019']
        # d2['outZZ_2016_2017'] = outZZcumsum_df.loc[date,'2016/2017']
        d2['outZZ_2017_2018'] = outZZcumsum_df.loc[date,'2017/2018']
        d2['outZZ_2018_2019'] = outZZcumsum_df.loc[date,'2018/2019']
        l2.append(d2)

    return render_template("gatherandout.html",l1=l1, l2=l2, l5=l5, l6=l6)
#------------------------------------------------------------------------------
# import and export
@app.route('/importandexport')
def importandexport():
    import_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='importcumsum')
    import_df = import_df.astype('float', errors="ignore")
    # import_df = import_df.fillna(0)
    # import_df = import_df.round(decimals=2)

    l1 = []
    for month in import_df.index:
        d1 = OrderedDict()
        d1['month'] = month
        # print(type(import_df.loc[month,'2018cassava']))
        d1['2014corn'] = import_df.loc[month,'2014corn']
        d1['2015corn'] = import_df.loc[month,'2015corn']
        d1['2016corn'] = import_df.loc[month,'2016corn']
        d1['2017corn'] = import_df.loc[month,'2017corn']
        d1['2018corn'] = import_df.loc[month,'2018corn']

        d1['2014barley'] = import_df.loc[month,'2014barley']
        d1['2015barley'] = import_df.loc[month,'2015barley']
        d1['2016barley'] = import_df.loc[month,'2016barley']
        d1['2017barley'] = import_df.loc[month,'2017barley']
        d1['2018barley'] = import_df.loc[month,'2018barley']

        d1['2014sorghum'] = import_df.loc[month,'2014sorghum']
        d1['2015sorghum'] = import_df.loc[month,'2015sorghum']
        d1['2016sorghum'] = import_df.loc[month,'2016sorghum']
        d1['2017sorghum'] = import_df.loc[month,'2017sorghum']
        d1['2018sorghum'] = import_df.loc[month,'2018sorghum']

        d1['2014cassava'] = import_df.loc[month,'2014cassava']
        d1['2015cassava'] = import_df.loc[month,'2015cassava']
        d1['2016cassava'] = import_df.loc[month,'2016cassava']
        d1['2017cassava'] = import_df.loc[month,'2017cassava']
        d1['2018cassava'] = import_df.loc[month,'2018cassava']
        l1.append(d1)
    # print(l1)
    return render_template("importandexport.html",l1=l1, title="玉米及替代品进口")
#------------------------------------------------------------------------------
# deepprocessing
@app.route('/deepprocessing')
def deepProcessing():
    df = pd.read_excel(app.config['EXCEL_DEEPPROCESS'], sheet_name='DeepProcessing')
    deepprocessing_df = df.iloc[1:,:16]
    deepprocessing_df.columns = ['68cs_qg_kgl', '68cs_db_kgl', '68cs_sd_kgl', '68cs_hb_kgl', 'cs_hlj_lr', 'cs_jl_lr', 'cs_ln_lr', 'cs_hb_lr', 'cs_sd_lr', '35jj_qg_kgl', '35jj_db_kgl', '35jj_hn_kgl', 'jj_jl_lr', 'jj_hlj_lr', 'jj_hb_lr', 'jj_hn_lr']
    # print(deepprocessing_df.columns)
    l1 = []
    for date in deepprocessing_df.index:
        # print(date)
        d1 = OrderedDict()
        d1['date'] = date
        # d1['68cs_qg_kgl'] = deepprocessing_df.loc[date,'68cs_qg_kgl']
        d1['68cs_db_kgl'] = deepprocessing_df.loc[date,'68cs_db_kgl']
        d1['68cs_sd_kgl'] = deepprocessing_df.loc[date,'68cs_sd_kgl']
        # d1['68cs_hb_kgl'] = deepprocessing_df.loc[date,'68cs_hb_kgl']
        d1['cs_hlj_lr'] = deepprocessing_df.loc[date,'cs_hlj_lr']
        d1['cs_jl_lr'] = deepprocessing_df.loc[date,'cs_jl_lr']
        # d1['cs_ln_lr'] = deepprocessing_df.loc[date,'cs_ln_lr']
        # d1['cs_hb_lr'] = deepprocessing_df.loc[date,'cs_hb_lr']
        d1['cs_sd_lr'] = deepprocessing_df.loc[date,'cs_sd_lr']
        # d1['35jj_qg_kgl'] = deepprocessing_df.loc[date,'35jj_qg_kgl']
        d1['35jj_db_kgl'] = deepprocessing_df.loc[date,'35jj_db_kgl']
        d1['35jj_hn_kgl'] = deepprocessing_df.loc[date,'35jj_hn_kgl']
        d1['jj_jl_lr'] = deepprocessing_df.loc[date,'jj_jl_lr']
        d1['jj_hlj_lr'] = deepprocessing_df.loc[date,'jj_hlj_lr']
        # d1['jj_hb_lr'] = deepprocessing_df.loc[date,'jj_hb_lr']
        d1['jj_hn_lr'] = deepprocessing_df.loc[date,'jj_hn_lr']
        l1.append(d1)
    # print(l1)
    return render_template("deepprocessing.html", l1=l1)
    # return deepprocessing_df.to_html()
#------------------------------------------------------------------------------
# priceSummarize
@app.route('/priceSummarize')
def priceSummarize():
    df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='visual', index_col=0)
    region_df = df.iloc[13:21, :8]
    region_df.iloc[0,0] = region_df.iloc[0,0].date()

    # deepcarryout_df = df.iloc[:17, 9:14]
    # deepcarryout_df.iloc[0,3] = deepcarryout_df.iloc[0,3].date()
    # deepcarryout_df.iloc[0,4] = deepcarryout_df.iloc[0,4].date()
    # for i in range(deepcarryout_df.shape[0]-1):
    #     deepcarryout_df.iloc[i+1,2] = '%.2f%%' % (deepcarryout_df.iloc[i+1,2]*100)

    summarize_df = df.iloc[30:59, :9]
    summarize_df.iloc[0,0] = summarize_df.iloc[0,0].date()
    # summarize_df.iloc[14:21,[6,8]].round(2)
    summarize_df.iloc[22,8] = '%.2f%%' % (summarize_df.iloc[22,8]*100)
    summarize_df.iloc[23,8] = '%.2f%%' % (summarize_df.iloc[23,8]*100)
    for i in range(14,21,1):
        for j in range(5,9,1):
            summarize_df.iloc[i,j] = round((summarize_df.iloc[i,j]),1)
    summarize_df.iloc[22,6] = round((summarize_df.iloc[22,6]),1)
    summarize_df.iloc[22,7] = round((summarize_df.iloc[22,7]),1)
    summarize_df.iloc[23,6] = round((summarize_df.iloc[23,6]),1)
    summarize_df.iloc[23,7] = round((summarize_df.iloc[23,7]),1)

    feedcarryout_df = df.iloc[:12, :6]
    # feedcarryout_df.iloc[0,3] = feedcarryout_df.iloc[0,3].date()
    # feedcarryout_df.iloc[0,4] = feedcarryout_df.iloc[0,4].date()
    # for i in range(feedcarryout_df.shape[0]-1):
    #     feedcarryout_df.iloc[i+1,2] = '%.2f%%' % (feedcarryout_df.iloc[i+1,2]*100)
    # region_df = region_df.to_html(header=None, index=None, na_rep='', col_space=20, bold_rows=True)
    # carryout_df = carryout_df.to_html(header=None, index=None, na_rep='', col_space=20, bold_rows=True)
    factory115_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='factory115', index_col=0)
    factory115_df = factory115_df.round(decimals=2)
    factory115_l = []
    for i in range(factory115_df.shape[0]):
        d1 = OrderedDict()
        d1['date'] = factory115_df.index[i]
        d1['zongkucun'] = factory115_df.iloc[i,0]
        d1['changnei'] = factory115_df.iloc[i,1]
        d1['waiku'] = factory115_df.iloc[i,2]
        d1['weizhixing'] = factory115_df.iloc[i,3]
        d1['weiyunhui'] = factory115_df.iloc[i,4]
        d1['weekchange'] = round(factory115_df.iloc[i,6],1)
        d1['jinzhou'] = factory115_df.iloc[i,5]
        factory115_l.append(d1)
    return render_template("priceSummarize.html", region_df=region_df, feedcarryout_df=feedcarryout_df, summarize_df=summarize_df, factory115_l=factory115_l, title="信息概览")
    # return carryout_df
#------------------------------------------------------------------------------
# jinzhou prie seasonal
@app.route('/priceseasonal')
def priceseasonal():
    priceseasonal_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='jinzhouprice_year', index_col=1)
    priceseasonal_l = []
    for date in priceseasonal_df.index:
        d1 = OrderedDict()
        d1['date'] = date
        d1['09/10'] = priceseasonal_df.loc[date,"2009/2010"]
        d1['10/11'] = priceseasonal_df.loc[date,"2010/2011"]
        d1['11/12'] = priceseasonal_df.loc[date,"2011/2012"]
        d1['12/13'] = priceseasonal_df.loc[date,"2012/2013"]
        d1['13/14'] = priceseasonal_df.loc[date,"2013/2014"]
        d1['14/15'] = priceseasonal_df.loc[date,"2014/2015"]
        d1['15/16'] = priceseasonal_df.loc[date,"2015/2016"]
        d1['16/17'] = priceseasonal_df.loc[date,"2016/2017"]
        d1['17/18'] = priceseasonal_df.loc[date,"2017/2018"]
        d1['18/19'] = priceseasonal_df.loc[date,"2018/2019"]
        priceseasonal_l.append(d1)

    return render_template("priceseasonal.html", priceseasonal_l=priceseasonal_l)
#------------------------------------------------------------------------------
# CFTC open insterest
@app.route('/cftcopi')
def cftcopi():
    cftc_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='cftc_data', index_col=0)
    cftc_df = cftc_df.astype('float', errors="ignore")
    cftc_l = []
    for date in cftc_df.index:
        d1 = OrderedDict()
        d1['date'] = date
        d1['corn_opi'] = cftc_df.loc[date,"corn_opi"]
        d1['corn_netlong_ratio'] = cftc_df.loc[date,"corn_netlong_ratio"]
        d1['corn_netlong'] = cftc_df.loc[date,"corn_netlong"]
        d1['cornprice'] = cftc_df.loc[date,"cornprice"]
        d1['wsr_opi'] = cftc_df.loc[date,"wsr_opi"]
        d1['wsr_netlong_ratio'] = cftc_df.loc[date,"wsr_netlong_ratio"]
        d1['wsr_netlong'] = cftc_df.loc[date,"wsr_netlong"]
        d1['wsrprice'] = cftc_df.loc[date,"wsrprice"]
        d1['whr_opi'] = cftc_df.loc[date,"whr_opi"]
        d1['whr_netlong_ratio'] = cftc_df.loc[date,"whr_netlong_ratio"]
        d1['whr_netlong'] = cftc_df.loc[date,"whr_netlong"]
        d1['soy_opi'] = cftc_df.loc[date,"soy_opi"]
        d1['soy_netlong_ratio'] = cftc_df.loc[date,"soy_netlong_ratio"]
        d1['soy_netlong'] = cftc_df.loc[date,"soy_netlong"]
        d1['soyprice'] = cftc_df.loc[date,"soyprice"]

        cftc_l.append(d1)

    return render_template("cftcopi.html", cftc_l=cftc_l)
#------------------------------------------------------------------------------
# corntempres
@app.route('/corntempres')
def corntempres():
    # summarize
    df = pd.read_excel(app.config['EXCEL_TEMPRES'], sheet_name='summarize', header=None)
    tempRes_df = df.iloc[10:22, 5:13]
    tempRes_df.iloc[0,0] = tempRes_df.iloc[0,0].date()
    for i in range(tempRes_df.shape[0]-1):
        if i in [0,1,2,3,5,6,7,8]:
            tempRes_df.iloc[i+1,5] = '%.2f%%' % (tempRes_df.iloc[i+1,5]*100)
        tempRes_df.iloc[i+1,2] = '%d万吨' % tempRes_df.iloc[i+1,2]
        tempRes_df.iloc[i+1,3] = '%.2f万吨' % (tempRes_df.iloc[i+1,3]/10000.0)
        tempRes_df.iloc[i+1,6] = '%d万吨' % tempRes_df.iloc[i+1,6]
        tempRes_df.iloc[i+1,7] = '%d万吨' % tempRes_df.iloc[i+1,7]

    # corn detail
    df1 = pd.read_excel(app.config['EXCEL_TEMPRES'], sheet_name='detail')
    detail_df = df1[-4:]
    detail_df.columns = list(range(1,df1.shape[1]+1))
    l1 = []
    for i in detail_df.index:
        d1 = OrderedDict()
        d1['date'] = detail_df.loc[i,1]
        d1['2014cjl_hlj'] = detail_df.loc[i,9]
        d1['2015cjl_hlj'] = detail_df.loc[i,33]
        d1['2014p_hlj'] = detail_df.loc[i,8]
        d1['2015p_hlj'] = detail_df.loc[i,32]
        d1['2014cjl_jl'] = detail_df.loc[i,15]
        d1['2015cjl_jl'] = detail_df.loc[i,39]
        d1['2014p_jl'] = detail_df.loc[i,14]
        d1['2015p_jl'] = detail_df.loc[i,38]
        d1['2014cjl_ln'] = detail_df.loc[i,21]
        d1['2015cjl_ln'] = detail_df.loc[i,45]
        d1['2014p_ln'] = detail_df.loc[i,20]
        d1['2015p_ln'] = detail_df.loc[i,44]
        d1['2014cjl_nm'] = detail_df.loc[i,27]
        d1['2015cjl_nm'] = detail_df.loc[i,51]
        d1['2014p_nm'] = detail_df.loc[i,26]
        d1['2015p_nm'] = detail_df.loc[i,50]
        l1.append(d1)

    # soy detail
    df2 = pd.read_excel(app.config['EXCEL_TEMPRES'], sheet_name='soydetail')
    # print(df2)
    l2 = []
    for i in df2.index:
        d2 = OrderedDict()
        d2['date'] = i
        d2['2018volume'] = df2.loc[i,'vol']
        d2['2018price'] = df2.loc[i,'price']
        d2['2018ratio'] = df2.loc[i,'ratio']
        l2.append(d2)

    return render_template("corntempres.html", tempRes_df=tempRes_df, l1=l1, l2=l2)
    # return detail_df.to_html()
#------------------------------------------------------------------------------
# shou liang jin du
@app.route('/shouliangjindu')
def shouliangjindu():
    salerate_df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='salerate_avg', index_col=0)
    salerate_df = salerate_df.round(decimals=2)
    salerate_df.columns = list(range(1,salerate_df.shape[1]+1))
    l1 = []
    for i in salerate_df.index:
        d1 = OrderedDict()
        d1['date'] = i
        d1['hlg_5ave'] = salerate_df.loc[i,49]
        d1['jl_5ave'] = salerate_df.loc[i,50]
        d1['ln_5ave'] = salerate_df.loc[i,51]
        d1['nm_5ave'] = salerate_df.loc[i,52]
        d1['hb_5ave'] = salerate_df.loc[i,53]
        d1['sd_5ave'] = salerate_df.loc[i,54]
        d1['hn_5ave'] = salerate_df.loc[i,55]

        d1['hlg_1314'] = salerate_df.loc[i,2]
        d1['jl_1314'] = salerate_df.loc[i,3]
        d1['ln_1314'] = salerate_df.loc[i,4]
        d1['nm_1314'] = salerate_df.loc[i,5]
        d1['hb_1314'] = salerate_df.loc[i,6]
        d1['sd_1314'] = salerate_df.loc[i,7]
        d1['hn_1314'] = salerate_df.loc[i,8]

        d1['hlg_1415'] = salerate_df.loc[i,10]
        d1['jl_1415'] = salerate_df.loc[i,11]
        d1['ln_1415'] = salerate_df.loc[i,12]
        d1['nm_1415'] = salerate_df.loc[i,13]
        d1['hb_1415'] = salerate_df.loc[i,14]
        d1['sd_1415'] = salerate_df.loc[i,15]
        d1['hn_1415'] = salerate_df.loc[i,16]

        d1['hlg_1516'] = salerate_df.loc[i,18]
        d1['jl_1516'] = salerate_df.loc[i,19]
        d1['ln_1516'] = salerate_df.loc[i,20]
        d1['nm_1516'] = salerate_df.loc[i,21]
        d1['hb_1516'] = salerate_df.loc[i,22]
        d1['sd_1516'] = salerate_df.loc[i,23]
        d1['hn_1516'] = salerate_df.loc[i,24]

        d1['hlg_1617'] = salerate_df.loc[i,26]
        d1['jl_1617'] = salerate_df.loc[i,27]
        d1['ln_1617'] = salerate_df.loc[i,28]
        d1['nm_1617'] = salerate_df.loc[i,29]
        d1['hb_1617'] = salerate_df.loc[i,30]
        d1['sd_1617'] = salerate_df.loc[i,31]
        d1['hn_1617'] = salerate_df.loc[i,32]

        d1['hlg_1718'] = salerate_df.loc[i,34]
        d1['jl_1718'] = salerate_df.loc[i,35]
        d1['ln_1718'] = salerate_df.loc[i,36]
        d1['nm_1718'] = salerate_df.loc[i,37]
        d1['hb_1718'] = salerate_df.loc[i,38]
        d1['sd_1718'] = salerate_df.loc[i,39]
        d1['hn_1718'] = salerate_df.loc[i,40]

        d1['hlg_1819'] = salerate_df.loc[i,42]
        d1['jl_1819'] = salerate_df.loc[i,43]
        d1['ln_1819'] = salerate_df.loc[i,44]
        d1['nm_1819'] = salerate_df.loc[i,45]
        d1['hb_1819'] = salerate_df.loc[i,46]
        d1['sd_1819'] = salerate_df.loc[i,47]
        d1['hn_1819'] = salerate_df.loc[i,48]
        l1.append(d1)

    return render_template("shouliangjindu.html", l1=l1)
    # return salerate_df.to_html()
#------------------------------------------------------------------------------
def getPigPriceData():
    df = pd.read_excel(app.config['EXCEL_WEBDATA'], sheet_name='pigPrice', index_col=0)
    # print(df)
    pigPrice_l = []
    for i in range(df.shape[0]):
        d1 = OrderedDict()
        d1['date'] = df.index[i]
        d1['zizhuPrice'] = df.iloc[i,0]
        d1['baitiaozhuPrice'] = df.iloc[i,1]
        d1['zaihoujunzhong'] = df.iloc[i,2]
        d1['gdCornPrice'] = df.iloc[i,3]
        pigPrice_l.append(d1)

    return pigPrice_l
#------------------------------------------------------------------------------
@app.route('/pigprice')
def pigprice():
    pigPrice_l = getPigPriceData()
    # print(pigPrice_l)
    return render_template("PigPrice.html", pigPrice_l=pigPrice_l, title="生猪价格")
#------------------------------------------------------------------------------
# temptest
@app.route('/temptest', methods=['GET', 'POST'])
def temptest():
    df = pd.read_excel(app.config['EXCEL_CORNDATA'], sheet_name='NSPort')
    df = df[1:-1]
    # corn_year_basis_df = corn_year_basis_df.fillna(0)
    l1 = []
    l2 = []
    l3 = []
    for date in df.index:
        d = OrderedDict()
        d['date'] = date
        d['NorthCarryout'] = df.loc[date,'Unnamed: 20']
        d['NorthCarryoutChange'] = df.loc[date,'Unnamed: 21']
        d['JinzhouPrice'] = df.loc[date,'Unnamed: 4']
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

#------------------------------------------------------------------------------
# temptest
@app.route('/temptest2', methods=['GET', 'POST'])
def temptest2():
    return render_template("temptest2.html")



