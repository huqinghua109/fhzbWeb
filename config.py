import os

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'

UPLOAD_FOLDER = './tmp/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc'])
EXCEL_BASIS = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/cleandata_basis.xlsx')
EXCEL_CORNDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),'report/CornData.xlsx')
