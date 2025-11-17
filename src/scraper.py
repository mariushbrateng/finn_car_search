import pandas as pd
from bs4 import BeautifulSoup
from functools import partial
from pydantic import BaseModel
from pathlib import Path
import plotly.express as px
import tomllib
from typing import List
import json


data_path = Path.cwd() / "data"
ads_folder = data_path / "ads"


class Ad(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_year: int | None
    model_km: int | None
    price: int | None
    tldr: str | None
    brand: str | None
    model: str | None
    id: int | None
    link: str | None
    safety_elements: List[str] | None
    is_leasing: bool | None


def get_top_row_item(item: str, soup: BeautifulSoup) -> int | None:
    try:
        parent_div = soup.find("div", string=item)

        content_div = parent_div.find_next_sibling("div", class_="u-strong")

        # Extract the text, clean it, and convert to integer
        content_text = content_div.get_text(strip=True)
        content_text = int(content_text.replace("\xa0", "").replace(" km", ""))

        return content_text
    except:
        return None


get_model_year = partial(get_top_row_item, "Modellår")
get_model_km = partial(get_top_row_item, "Kilometer")


def get_tldr(soup) -> str | None:
    try:
        first_h1 = soup.find("h1")
        return first_h1.find_next_sibling("p").get_text(strip=True)
    except:
        return None


def get_price(soup) -> int | None:
    totalpris_label = soup.find("span", string="Totalpris")

    try:
        # First attempt using the provided method
        totalpris_value = totalpris_label.find_next_sibling(
            "span", class_="u-t3"
        ).get_text(strip=True)
        return int(
            totalpris_value.replace("\xa0", "").replace(" kr", "").replace(" ", "")
        )

    except Exception as e:
        try:
            # Alternative method based on the new approach
            script_tag = soup.find("script", {"id": "horseshoe-config"})
            if script_tag and script_tag.string:
                # Parse the JSON content
                json_content = json.loads(script_tag.string)

                # Extract the value of "pris"
                return int(json_content["xandr"]["feed"]["pris"])
            raise ValueError("horseshoe-config script missing")

        except Exception as e:
            print("Alternative method failed:", e)
            return None


def get_brand_type_id(soup):
    try:
        anchors = soup.find_all("a", id="carSearchLink")

        make_text = anchors[0].get_text(strip=True)
        model_text = anchors[1].get_text(strip=True)
        model_text = model_text.split(" ")[1:]
        model_text = " ".join(model_text)
        model_identifier = anchors[1]["href"].split("model=")[1]

        return make_text, model_text, model_identifier
    except:
        return None, None, None


def get_safty_elements(soup):
    try:
        ul_element = soup.find(
            "ul",
            {
                "aria-label": "Trygghetselementer",
                "class": "tabs__control u-position-relative",
                "role": "tablist",
            },
        )

        # Find all <p> tags with the class 'u-strong' within the located <ul> element
        safety_elements = [
            p.get_text(strip=True) for p in ul_element.select("li p.u-strong")
        ]

        return safety_elements
    except:
        return None


def get_leasing(soup):
    return "Månedspris" in soup.get_text()


files_list = [file for file in ads_folder.iterdir() if file.is_file()]
ad_link = "https://www.finn.no/car/used/ad.html?finnkode="
ad_lst = []
for file in files_list:
    with open(file) as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    try:
        ad = Ad(
            model_year=get_model_year(soup),
            model_km=get_model_km(soup),
            price=get_price(soup),
            tldr=get_tldr(soup),
            brand=get_brand_type_id(soup)[0],
            model=get_brand_type_id(soup)[1],
            id=int(file.stem),
            link=ad_link + str(file.stem),
            safety_elements=get_safty_elements(soup),
            is_leasing=get_leasing(soup),
        )

        ad_lst.append(ad)
    except Exception as e:
        print(e)
        print(file)

ads_df = pd.DataFrame([ad.model_dump() for ad in ad_lst])
for index, row in ads_df.iterrows():
    if row["tldr"]:
        if "Touring" in row["tldr"]:
            ads_df.at[index, "model"] = "Corolla Touring"

ads_df.to_parquet(data_path / "ads.parquet")
