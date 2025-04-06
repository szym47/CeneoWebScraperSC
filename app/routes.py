from app import app
from flask import render_template,request,redirect,url_for,send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from . import utils
import json 
import os
import io

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/extract', methods = ['POST', 'GET'])
def extract():
    if request.method == "POST":
        product_id = request.form.get("product_id")
        url = f"https://www.ceneo.pl/{product_id}#tab=reviews"  # Pierwsza strona z #tab=reviews
        response = requests.get(url)
        if response.status_code == requests.codes["ok"]:
            page_dom = BeautifulSoup(response.text, "html.parser")
            opinions_count = utils.extract(page_dom, "a.product-review__link > span")
            if opinions_count:
                product_name = utils.extract(page_dom, "h1")
                all_opinions = []
                page_number = 2  

                # Przetwarzamy pierwszą stronę (opinie z #tab=reviews)
                opinions = page_dom.select("div.js_product-review")
                for opinion in opinions:
                    single_opinion = {
                        key: utils.extract(opinion, *value)
                        for key, value in utils.selectors.items()
                    }
                    all_opinions.append(single_opinion)

                # Kolejne strony /opinie-2, /opinie-3 itd.
                while True:
                    url = f"https://www.ceneo.pl/{product_id}/opinie-{page_number}"  # Kolejne strony opinii
                    response = requests.get(url)
                    if response.status_code != 200:
                        break
                    page_dom = BeautifulSoup(response.text, "html.parser")
                    opinions = page_dom.select("div.js_product-review")
                    if not opinions:
                        break  # Jeśli nie ma opinii na stronie
                    for opinion in opinions:
                        single_opinion = {
                            key: utils.extract(opinion, *value)
                            for key, value in utils.selectors.items()
                        }
                        all_opinions.append(single_opinion)

                    page_number += 1  # Przechodzimy do kolejnej strony

                # Zapisujemy zebrane opinie do pliku JSON
                if not os.path.exists("app/opinions"):
                    os.makedirs("app/opinions")
                with open(f"app/opinions/{product_id}.json", "w", encoding="UTF-8") as jf:
                    json.dump(all_opinions, jf, indent=4, ensure_ascii=False)

                # Tworzymy DataFrame z opiniami i obliczamy statystyki
                opinions = pd.DataFrame.from_dict(all_opinions)
                opinions.stars = opinions.stars.apply(
                    lambda s: float(s.split("/")[0].replace(",", ".")) if isinstance(s, str) else None
                )
                opinions.recommendations = opinions.recommendations.apply(
                    lambda r: "Brak rekomendacji" if r is None else r
                )

                stats = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'opinions_count': opinions.shape[0],
                    'pros_count': int(opinions.pros.apply(lambda p: bool(p)).sum()),
                    'cons_count': int(opinions.cons.apply(lambda p: bool(p)).sum()),
                    'average_stars': opinions.stars.mean(),
                    'stars_distribution': opinions.stars.value_counts().reindex(list(np.arange(0, 5.5, 0.5)), fill_value=0).to_dict(),
                    'recommendations_distribution': opinions.recommendations.value_counts(dropna=False).reindex(
                        ["Polecam", "Brak rekomendacji", "Nie polecam"], fill_value=0).to_dict()
                }

                if not os.path.exists("app/products"):
                    os.makedirs("app/products")
                with open(f"app/products/{product_id}.json", "w", encoding="UTF-8") as jf:
                    json.dump(stats, jf, indent=4, ensure_ascii=False)

                return redirect(url_for("product", product_id=product_id))
            return render_template("extract.html", error="Podany produkt nie ma żadnych opinii")
        return render_template("extract.html", error="Produkt o podanym kodzie nie istnieje")
    return render_template("extract.html")


@app.route('/products')
def products():
    if os.path.exists("app/opinions"):
        products_list = [filename.split(".")[0] for filename in os.listdir("app/opinions")]
    else:
        products_list = []
    products=[]
    for product_id in products_list:
        product_path = f"app/products/{product_id}.json"
        if os.path.exists(product_path):
            with open(product_path, "r", encoding="UTF-8") as jf:
                products.append(json.load(jf))
        else:
            print(f"Plik {product_path} nie istnieje – pomijam.")

    return render_template("products.html",products=products)

@app.route('/autor')
def autor():
    return render_template("autor.html")

@app.route('/product/<product_id>')
def product(product_id):
    product_file_path = os.path.join('app/products', f'{product_id}.json')
    product_data = None
    try:
        with open(product_file_path, 'r', encoding='utf-8') as file:
            product_data = json.load(file)
    except FileNotFoundError:
        return render_template("product.html", error=f"Nie znaleziono danych produktu {product_id}", product_id=product_id)
    except json.JSONDecodeError:
        return render_template("product.html", error=f"Błąd przy wczytywaniu danych JSON dla produktu {product_id}", product_id=product_id)
    if product_data is None:
        f"Unexpected error for product with ID {product_id}"

    return render_template("product.html", product=product_data,product_id=product_id)

@app.route('/product/download_json/<product_id>')
def download_json(product_id):
    return send_file(f"app/opinions/{product_id}.json", "application/json", as_attachment=True)

@app.route('/product/download_csv/<product_id>')
def download_csv(product_id):
    opinions = pd.read_json(f"app/opinions/{product_id}.json")
    opinions.stars=opinions.stars.apply(lambda s:"'"+s)
    buffer = io.BytesIO(opinions.to_csv(sep=";",decimal=",",index=False,quotechar='"').encode())
    return send_file(buffer,"text/csv",as_attachment=True,download_name=f'{product_id}.csv')

@app.route('/product/download_xlsx/<product_id>')
def download_xlsx(product_id):
    opinions = pd.read_json(f"app/opinions/{product_id}.json")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        opinions.to_excel(writer, sheet_name="Opinie", index=False)
    buffer.seek(0)
    return send_file(buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"{product_id}.xlsx")
