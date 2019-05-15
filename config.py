import os

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'

UPLOAD_FOLDER = './tmp/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc'])

EXCEL_TEMPRES = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/CornTempRes.xlsx')

EXCEL_WEBDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/WebData.xlsx')
EXCEL_CORNPRICE = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/CornPrice.xlsx')
EXCEL_DEEPPROCESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/DeepProcessOprationAndProfit.xlsx')
