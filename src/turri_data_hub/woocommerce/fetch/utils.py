from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from src.turri_data_hub.settings import WoocommerceSettings


def fetch_single(url: str, creator):
    resp = requests.get(url)
    resp.raise_for_status()
    return creator(resp.json())


def get_text(content, excerpt):
    return BeautifulSoup(
        f"Content: {content}.\n\nExcerpt: {excerpt}", "html.parser"
    ).get_text()


def fetch_list(
    url: str,
    per_page: int = 50,
) -> list:
    settings = WoocommerceSettings()
    page = 1
    url = urljoin(settings.url, url)
    params = {"per_page": per_page, "page": 1}
    resp = requests.get(
        url,
        params=params,
        auth=(settings.WOOCOMERCE_CLIENT_KEY, settings.WOOCOMERCE_SECRET_KEY),
    )

    resp.raise_for_status()
    data = resp.json()
    items = data
    total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))

    if total_pages > 1:
        for page in tqdm(range(2, total_pages + 1), desc="Fetching"):
            params = {"per_page": per_page, "page": page}
            resp = requests.get(
                url,
                params=params,
                auth=(settings.WOOCOMERCE_CLIENT_KEY, settings.WOOCOMERCE_SECRET_KEY),
            )
            resp.raise_for_status()
            items.extend(resp.json())
    return items
