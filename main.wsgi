import sys
import os

sys.path.insert(0, '/path/to/your/project')
os.environ['FLASK_ENV'] = 'production'

from main import app as application
