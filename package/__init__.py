from flask import Flask
from package.forms import textbox, fileupload, ID

app = Flask(__name__)

app.config['SECRET_KEY'] = '2792628ee0b13ce0d676dfde280ba275'

from package import routes