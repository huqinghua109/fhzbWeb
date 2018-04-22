from flask.ext.wtf import FlaskForm
from wtforms import StringField, BooleanField, IntegerField, FloatField
from wtforms.validators import DataRequired

class TestForm(FlaskForm):
	openid = StringField('openid1', validators=[DataRequired()])
	moistPrice = IntegerField()
	waterpercent = FloatField()
	dryPrice = IntegerField()
	# moistPrice = IntegerField()
	remember_me = BooleanField('remember me', default=False) 