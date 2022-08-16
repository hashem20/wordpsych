from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectMultipleField, form, PasswordField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import Length, DataRequired, Email

class textbox(FlaskForm):
	txt = TextAreaField('txt', validators=[Length(min=50)])
	submit = SubmitField('submit')

class ID(FlaskForm):
	user = StringField('user',validators=[DataRequired()])
	submit = SubmitField('submit')

class fileupload(FlaskForm):
	file = FileField('file', validators=[FileAllowed(['txt'])]) 
	submit = SubmitField('submit')


