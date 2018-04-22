from flask import Flask
import os

app = Flask(__name__)
app.config.from_object('config')
app.config['UPLOADED_OBJ_DEST'] = os.getcwd() + '/report'

from app import views