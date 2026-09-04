"""
State Contractors Scraper
==========================

Scrapes contractor listings (company name, address, phone, fax) from
GravityView list pages like:

    https://training669.org/view/state-contractors/?filter_2_4=Florida&mode=any

How to use
----------
1. Add every page URL you want scraped to the ``URLS`` list below
   (one URL per state / filter, or paginated URLs of the same filter --
   pagination is followed automatically so you only need the first page
   of each state).
2. Run:  python scraper.py
3. Results are written to ``contractors.csv`` in this folder and also
   printed to the console.

Install dependencies once with:
    pip install requests beautifulsoup4
"""

import csv
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 1) ADD YOUR PAGE URLS HERE (one per state / filter you want to scrape).
#    Pagination on the same filter is followed automatically, so just the
#    first page of results for each state is enough.
# ---------------------------------------------------------------------------
URLS = [
    "https://training669.org/view/state-contractors/?filter_2_4=District%20of%20Columbia&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Florida&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Georgia&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Guam&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Hawaii&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Idaho&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Illinois&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Indiana&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Iowa&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Kansas&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Kentucky&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Louisiana&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Maine&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Maryland&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Massachusetts&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Michigan&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Minnesota&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Mississippi&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Missouri&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Montana&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Nebraska&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Nevada&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=New%20Hampshire&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=New%20Jersey&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=New%20Mexico&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=New%20York&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=North%20Carolina&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=North%20Dakota&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Northern%20Mariana%20Islands&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Ohio&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Oklahoma&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Oregon&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Pennsylvania&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Puerto%20Rico&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Rhode%20Island&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=South%20Carolina&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=South%20Dakota&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Tennessee&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Texas&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Utah&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=U.S.%20Virgin%20Islands&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Vermont&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Virginia&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Washington&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=West%20Virginia&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Wisconsin&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Wyoming&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Armed%20Forces%20Americas&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Armed%20Forces%20Europe&mode=any",
    "https://training669.org/view/state-contractors/?filter_2_4=Armed%20Forces%20Pacific&mode=any",
]

OUTPUT_CSV = "contractors.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

REQUEST_DELAY_SECONDS = 1.5   # be polite between requests
MAX_PAGES_PER_URL = 50        # safety cap so a broken "next" link can't loop forever


def guess_state_label(url: str) -> str:
    """Pull the filter value (e.g. 'Florida') out of the URL's query string."""
    qs = parse_qs(urlparse(url).query)
    for key, values in qs.items():
        if key.startswith("filter_") and values:
            return values[0]
    return url


def find_next_page_url(soup: BeautifulSoup, current_url: str):
    """Look for a GravityView 'next page' link and return its absolute URL."""
    next_link = soup.select_one("a[rel='next']") or soup.select_one("a.next.page-numbers")
    if next_link and next_link.get("href"):
        return urljoin(current_url, next_link["href"])
    return None


def extract_field(entry, field_label: str):
    """
    Find a labeled field (e.g. 'Phone', 'Fax') inside one listing block
    and return its text, looking it up by its visible label rather than
    a hardcoded field id (which can differ between views).
    """
    label_span = entry.find("span", class_="gv-field-label", string=re.compile(field_label, re.I))
    if not label_span:
        return ""
    container = label_span.find_parent(["div", "p"])
    if not container:
        return ""
    link = container.find("a")
    if link:
        return link.get_text(strip=True)
    text = container.get_text(strip=True)
    return text.replace(field_label, "", 1).strip(": ").strip()


def parse_address(entry):
    """
    Split the GravityView subtitle block into street address / city /
    state / zip, and grab the 'Map It' link if present.
    """
    subtitle = entry.select_one(".gv-list-view-subtitle h4")
    if not subtitle:
        return "", "", "", "", ""

    subtitle = BeautifulSoup(str(subtitle), "html.parser")  # work on a copy
    for br in subtitle.find_all("br"):
        br.replace_with("\n")

    map_link_tag = subtitle.select_one("a.map-it-link")
    map_link = map_link_tag["href"] if map_link_tag else ""
    if map_link_tag:
        map_link_tag.decompose()

    lines = [line.strip() for line in subtitle.get_text().split("\n") if line.strip()]
    if not lines:
        return "", "", "", "", map_link

    # Last line is typically "City, State Zip"
    city_state_zip = lines[-1]
    street_lines = lines[:-1]
    street_address = " ".join(street_lines)

    city, state, zip_code = "", "", ""
    match = re.match(r"^(.*),\s*([A-Za-z .]+?)\s+(\d{5}(?:-\d{4})?)$", city_state_zip)
    if match:
        city, state, zip_code = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    else:
        city = city_state_zip

    return street_address, city, state, zip_code, map_link


def scrape_url(start_url: str, session: requests.Session):
    """Scrape one filtered listing URL, following pagination, and return rows."""
    rows = []
    state_label = guess_state_label(start_url)
    url = start_url

    for page_num in range(1, MAX_PAGES_PER_URL + 1):
        print(f"  Fetching page {page_num}: {url}")
        response = session.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        entries = soup.select("div.gv-list-view")
        if not entries:
            print("    No listings found on this page -- stopping.")
            break

        for entry in entries:
            name_tag = entry.select_one(".gv-list-view-title h3")
            company = name_tag.get_text(strip=True) if name_tag else ""

            street_address, city, state, zip_code, map_link = parse_address(entry)
            phone = extract_field(entry, "Phone")
            fax = extract_field(entry, "Fax")

            rows.append({
                "Filter": state_label,
                "Company": company,
                "Street Address": street_address,
                "City": city,
                "State": state,
                "Zip": zip_code,
                "Phone": phone,
                "Fax": fax,
                "Map Link": map_link,
                "Source URL": url,
            })

        next_url = find_next_page_url(soup, url)
        if not next_url or next_url == url:
            break
        url = next_url
        time.sleep(REQUEST_DELAY_SECONDS)

    return rows


def main():
    all_rows = []
    with requests.Session() as session:
        for url in URLS:
            print(f"Scraping: {url}")
            all_rows.extend(scrape_url(url, session))
            time.sleep(REQUEST_DELAY_SECONDS)

    if not all_rows:
        print("No data scraped.")
        return

    fieldnames = ["Filter", "Company", "Street Address", "City", "State", "Zip",
                  "Phone", "Fax", "Map Link", "Source URL"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} contractor records to {OUTPUT_CSV}")
    for row in all_rows:
        print(row)


if __name__ == "__main__":
    main()
