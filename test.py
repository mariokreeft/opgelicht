import requests
from bs4 import BeautifulSoup

# 1. Ophalen van de homepage
url = "https://opgelicht.avrotros.nl/"
resp = requests.get(url)
resp.raise_for_status()

print("begin")

# 2. Parsen van de HTML
soup = BeautifulSoup(resp.text, "html.parser")

# 3. Selecteren van de berichten (klasse "preloader")
items = soup.select("li.preloader a")

# 4. Uitschrijven van titel en URL
for a in items:
    titel = a.get_text(strip=True)
    link = a["href"]
    print(f"- {titel} → https://opgelicht.avrotros.nl{link}")

