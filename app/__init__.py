from flask import Flask
import os

for folder in ["app/opinions", "app/products"]:
    os.makedirs(folder, exist_ok=True)
app = Flask(__name__)
from app import routes
app.run(debug=True)