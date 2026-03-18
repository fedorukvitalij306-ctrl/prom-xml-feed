from flask import Flask, Response
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

CACHE = {"xml": "", "time": 0}
CACHE_TTL = 60 * 60  # 1 година

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    return BeautifulSoup(r.text, "html.parser")


def parse_product(url):
    soup = get_soup(url)

    name = soup.find("h1").text.strip()

    price_raw = soup.select_one("[data-qaid='product_price']")
    price = 0
    if price_raw:
        price = float(price_raw.text.replace("₴","").replace(" ","").replace(",","."))
        price = int(price * 2)

    desc = soup.select_one(".b-product-info__description")
    desc = desc.text.strip() if desc else ""

    image = soup.select_one("img")
    image = image["src"] if image else ""

    article = url.split("-")[-1].replace(".html","")

    # характеристики
    params = []
    rows = soup.select(".b-product-info__characteristics tr")
    for r in rows:
        cols = r.find_all("td")
        if len(cols) == 2:
            params.append((cols[0].text.strip(), cols[1].text.strip()))

    return name, price, desc, image, article, params


def generate_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="">
<shop>
<name>My Earrings Shop</name>
<company>My Earrings Shop</company>
<url>https://your-domain.com</url>

<currencies>
<currency id="UAH" rate="1"/>
</currencies>

<categories>
<category id="1">Сережки</category>
</categories>

<offers>
"""

    for page in range(1, 21):
        url = f"https://tsatsa.com.ua/ua/g12802961-sergi?page={page}"
        soup = get_soup(url)

        products = soup.select(".b-product-gallery__item a")

        for p in products:
            link = p["href"]

            try:
                name, price, desc, image, article, params = parse_product(link)

                xml += f"""
<offer id="{article}" available="true">
<name>{name}</name>
<price>{price}</price>
<currencyId>UAH</currencyId>
<categoryId>1</categoryId>
<picture>{image}</picture>
<vendor>TSATSA</vendor>
<vendorCode>{article}</vendorCode>
<description><![CDATA[{desc}]]></description>
"""

                for k, v in params:
                    xml += f'<param name="{k}">{v}</param>'

                xml += "</offer>"

                time.sleep(0.5)  # антибан

            except:
                continue

    xml += "</offers></shop></yml_catalog>"
    return xml


@app.route("/products.xml")
def feed():
    now = time.time()

    if now - CACHE["time"] > CACHE_TTL:
        try:
            CACHE["xml"] = generate_xml()
            CACHE["time"] = now
        except:
            pass

    return Response(CACHE["xml"], mimetype="application/xml")


app.run(host="0.0.0.0", port=10000)
