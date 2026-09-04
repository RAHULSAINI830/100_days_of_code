"""
NAFED Directory Scraper
========================

Scrapes the NAFED (National Association of Fire Equipment Distributors)
member directory listing page:

    https://web.nafed.org/Fire-sprinkler-systems

The site shows results paginated (e.g. "11 pages") in the browser, but
that pagination is done client-side in JavaScript -- the full member
list is already present in the raw HTML of a single GET request. This
script fetches that one page and extracts every listing regardless of
its membership "level" (the different visual styles -- Level1, Level2,
Level3, Level5 -- all share the same underlying microdata fields).

For each listing it extracts:
    - Company name
    - Street address / City / State / Zip
    - Phone
    - Website ("Visit Site" link, present on some listings)
    - Google Maps link
    - Profile URL on nafed.org

Install dependencies once with:
    pip install requests beautifulsoup4
"""

import csv
import html as html_lib
import re

import requests
from bs4 import BeautifulSoup

URL = "https://web.nafed.org/Fire-sprinkler-systems"
BASE_URL = "https://web.nafed.org"
OUTPUT_CSV = "nafed_fire_sprinkler_systems.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def text_of(tag):
    return tag.get_text(strip=True) if tag else ""


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    rows = []
    for entry in soup.select("div[class*='ListingResults_All_CONTAINER']"):
        name_link = entry.select_one("span[itemprop='name'] a")
        company = text_of(name_link)
        company = html_lib.unescape(company)
        profile_url = BASE_URL + name_link["href"] if name_link and name_link.get("href") else ""

        street = text_of(entry.select_one("span[itemprop='street-address']"))
        city = text_of(entry.select_one("span[itemprop='locality']"))
        state = text_of(entry.select_one("span[itemprop='region']"))
        zip_code = text_of(entry.select_one("span[itemprop='postal-code']"))

        phone_div = entry.select_one("div[class*='_PHONE1']")
        phone = ""
        if phone_div:
            # the phone number is the div's own text, after the <img> icon
            phone = re.sub(r"\s+", " ", phone_div.get_text(strip=True))

        map_link_tag = entry.find("a", string=re.compile("View on Google Maps"))
        map_link = map_link_tag["href"] if map_link_tag else ""

        website_tag = entry.find("a", string=re.compile("Visit Site"))
        website = website_tag["href"] if website_tag else ""

        if not company:
            continue

        rows.append({
            "Company": company,
            "Street Address": street,
            "City": city,
            "State": state,
            "Zip": zip_code,
            "Phone": phone,
            "Website": website,
            "Map Link": map_link,
            "Profile URL": profile_url,
        })

    return rows


def main():
    rows = scrape()
    if not rows:
        print("No data scraped.")
        return

    fieldnames = ["Company", "Street Address", "City", "State", "Zip",
                  "Phone", "Website", "Map Link", "Profile URL"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} listings to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
