from app import app
from flask import render_template

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")

@app.route('/extract')
def extract():
    return render_template("extract.html")

@app.route('/products')
def products():
    return render_template("products.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/name/<name>')
def name(name):
    return f"Hello, {name}!"

@app.route('/name/<product_id>')
def product_id(product_id):
    return render_template("product.html", product_id=product_id)