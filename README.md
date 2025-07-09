# AVROTROS Opgelicht Alerts Web App

Een Python Flask web applicatie die nieuwsberichten en alerts van de AVROTROS "Opgelicht" website toont.

## Functionaliteiten

- 📰 Haalt automatisch alerts op van opgelicht.avrotros.nl
- 🎨 Moderne, responsive interface met Tailwind CSS
- 🔄 Automatisch vernieuwen elke 5 minuten
- 📱 Mobiel-vriendelijk design
- 🔗 API endpoint voor JSON data
- ⚡ Snelle en efficiënte web scraping

## Installatie

1. **Clone of download het project**
   ```bash
   cd /pad/naar/project
   ```

2. **Maak een virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Op macOS/Linux
   # of
   venv\Scripts\activate  # Op Windows
   ```

3. **Installeer dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Gebruik

1. **Start de applicatie**
   ```bash
   python app.py
   ```

2. **Open je browser**
   - Ga naar: `http://localhost:5000`
   - De applicatie toont alle beschikbare alerts

3. **API toegang**
   - JSON data: `http://localhost:5000/api/alerts`

## Endpoints

- `/` - Hoofdpagina met alle alerts
- `/api/alerts` - JSON API endpoint
- `/refresh` - Vernieuw alerts handmatig

## Technische Details

### Gebruikte Libraries
- **Flask** - Web framework
- **Requests** - HTTP verzoeken
- **BeautifulSoup4** - HTML parsing
- **lxml** - XML/HTML parser

### Scraping Functionaliteit
De applicatie gebruikt meerdere strategieën om alerts te vinden:
1. Zoekt naar specifieke CSS selectors
2. Probeert verschillende alert patronen
3. Extraheert titel, beschrijving, datum en URL
4. Heeft fallback voor onverwachte website structuren

### Responsieve Design
- Tailwind CSS voor moderne styling
- Mobile-first approach
- Hover effecten en smooth transitions
- Gradient backgrounds en moderne iconen

## Troubleshooting

### Geen alerts gevonden
- De website structuur kan zijn gewijzigd
- Controleer of de website bereikbaar is
- Kijk naar de console logs voor meer details

### Scraping problemen
- De applicatie heeft meerdere fallback strategieën
- Bij problemen wordt een foutmelding getoond
- Logs worden getoond in de console

## Uitbreidingen

Mogelijke verbeteringen:
- Database opslag voor alerts
- Notificatie systeem
- Meer gedetailleerde filtering
- Export functionaliteit
- Admin interface

## Licentie

Dit project is voor educatieve doeleinden. De gegevens komen van AVROTROS en zijn eigendom van hen.