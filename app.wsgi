import sys
sys.path.insert(0, 'C:\Users\Administrator\Desktop\myfinalcode\app.py')  # Replace with the actual path to your Flask app
from app.py import app as application  # Replace 'your_flask_app' with the name of your Flask app variable

application.secret_key = '10.18.0.26'  # Set a secret key for your Flask app