import requests
from bs4 import BeautifulSoup
import tomllib
import re
from pathlib import Path
from datetime import date
from typing import List


today_date = date.today()
today_date = int(today_date.strftime("%Y%m%d"))

data_path = Path.cwd() / "data"
output_dir = data_path / "ads"
data_path.mkdir(parents=True, exist_ok=True)

with open("src/config.toml", "rb") as f:
    config = tomllib.load(f)
car_codes = config["car_codes"]
basic_finn_url = config["scraper"]["basic_finn_url"]
filters = config.get("filters", {})


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,nb;q=0.8",
}


def build_search_url(car_code: str) -> str:
    url = f"{basic_finn_url}{car_code}"
    year_from = filters.get("year_from")
    if year_from not in (None, ""):
        url += f"&year_from={year_from}"
    year_to = filters.get("year_to")
    if year_to not in (None, ""):
        url += f"&year_to={year_to}"
    return url


def fetch_ad_codes_from_url(url: str, ad_codes: list | None = None, pagination=1):
    print(pagination)
    paginated_url = f"{url}&page={pagination}"
    response = requests.get(paginated_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    new_ad_codes = get_ad_codes_from_soup(soup)

    if ad_codes is None:
        ad_codes = new_ad_codes
    else:
        ad_codes.extend(new_ad_codes)

    has_next_page = soup.find("a", rel="next") is not None

    if has_next_page:
        return fetch_ad_codes_from_url(url, ad_codes, pagination + 1)
    return ad_codes


AD_CODE_PATTERNS = [
    re.compile(r"finnkode=(\d+)"),
    re.compile(r"/mobility/item/(\d+)"),
]


def get_ad_codes_from_soup(soup: BeautifulSoup) -> list:
    links = soup.find_all("a", href=True)
    ad_codes = []
    for link in links:
        href = link["href"]
        for pattern in AD_CODE_PATTERNS:
            match = pattern.search(href)
            if match:
                ad_codes.append(int(match.group(1)))
                break
    return ad_codes


def fetch_and_save_ad_soup(ad_code, output_dir: Path):
    try:
        url = f"https://www.finn.no/car/used/ad.html?finnkode={ad_code}"
        response = requests.get(url)
        response.raise_for_status()  # Check for request errors
        soup = BeautifulSoup(response.content, "html.parser")
        file_name = f"{ad_code}.txt"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / file_name
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(str(soup))
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")


def scrape_car_model(car_code: str, basic_finn_url: str, output_dir: Path):
    basic_finn_url = build_search_url(car_code)
    ad_codes_old = read_saved_ad_codes(output_dir)
    ad_codes_new = fetch_ad_codes_from_url(basic_finn_url)
    ad_codes_diff = [code for code in ad_codes_new if code not in ad_codes_old]
    print(
        f"Found {len(ad_codes_diff)} new ads, total {len(set(ad_codes_new + ad_codes_old))}"
    )

    for ad_code in ad_codes_diff:
        fetch_and_save_ad_soup(ad_code, output_dir)


def read_saved_ad_codes(ads_folder: Path) -> List[int]:
    return [int(file.stem) for file in ads_folder.iterdir() if file.is_file()]


for model, car_code in car_codes.items():
    print(model)
    scrape_car_model(
        car_code=car_code, basic_finn_url=basic_finn_url, output_dir=output_dir
    )
