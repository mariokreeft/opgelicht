from flask import Flask, render_template, jsonify, redirect, url_for
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertScraper:
    def __init__(self):
        self.base_url = "https://opgelicht.avrotros.nl"
        self.alerts_url = f"{self.base_url}/alerts/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.driver = None
    
    def _setup_driver(self):
        """Setup Chrome driver with headless options"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Setup Chrome for Heroku chrome-for-testing buildpack
            import os
            
            # Heroku chrome-for-testing buildpack sets these environment variables
            chrome_bin = os.environ.get('GOOGLE_CHROME_BIN')
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
            
            if chrome_bin:
                chrome_options.binary_location = chrome_bin
                logger.info(f"Using Chrome from buildpack: {chrome_bin}")
            else:
                # Try common locations for other deployments
                for location in ['/usr/bin/chromium', '/usr/bin/google-chrome', '/usr/bin/chromium-browser']:
                    if os.path.exists(location):
                        chrome_options.binary_location = location
                        logger.info(f"Using Chrome from: {location}")
                        break
            
            try:
                # Try Heroku chrome-for-testing buildpack first
                if chromedriver_path and os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Chrome driver setup successful (Heroku buildpack)")
                else:
                    # Try common chromedriver locations
                    for driver_path in ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver', '/app/.chromedriver/bin/chromedriver']:
                        if os.path.exists(driver_path):
                            service = Service(driver_path)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                            logger.info(f"Chrome driver setup successful (system): {driver_path}")
                            break
                    else:
                        # Fallback to webdriver-manager
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        logger.info("Chrome driver setup successful (webdriver-manager)")
            except Exception as e:
                logger.error(f"Failed to setup Chrome driver: {e}")
                return False
        return True
    
    def _cleanup_driver(self):
        """Clean up the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_alerts(self):
        """Scrape alerts from the AVROTROS website using Selenium"""
        try:
            logger.info("Fetching alerts from AVROTROS website...")
            
            # Setup selenium driver
            if not self._setup_driver():
                return self._fallback_to_requests()
            
            # Use the main homepage instead of alerts page
            main_url = "https://opgelicht.avrotros.nl/"
            
            try:
                self.driver.get(main_url)
                
                # Wait for page to load and images to appear
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Wait a bit more for lazy loading
                time.sleep(3)
                
                # Scroll down to trigger lazy loading
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Scroll back up and wait for images to load
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # Try to trigger image loading by scrolling through all images
                self.driver.execute_script("""
                    var images = document.querySelectorAll('img[data-src]');
                    images.forEach(function(img) {
                        img.scrollIntoView({behavior: 'smooth', block: 'center'});
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                        }
                    });
                """)
                time.sleep(3)
                
                # Get page source after JavaScript execution
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
            except TimeoutException:
                logger.error("Timeout waiting for page to load")
                return self._fallback_to_requests()
            except Exception as e:
                logger.error(f"Error with selenium: {e}")
                return self._fallback_to_requests()
            finally:
                self._cleanup_driver()
            
            # Look for the preloader items as shown in test.py
            alerts = []
            items = soup.select("li.preloader a")
            
            logger.info(f"Found {len(items)} preloader items")
            
            for item in items:
                title = item.get_text(strip=True)
                link = item.get('href', '')
                
                if title and link:
                    full_url = f"https://opgelicht.avrotros.nl{link}" if link.startswith('/') else link
                    
                    # Try to find image in the parent container
                    parent = item.parent
                    image_url = None
                    if parent:
                        # Look for teaser-figure-image class first
                        img_elem = parent.select_one('.teaser-figure-image')
                        if img_elem:
                            image_url = img_elem.get('src') or img_elem.get('data-src')
                        
                        # If not found, look for teaser-crop figure
                        if not image_url:
                            figure_elem = parent.select_one('figure.teaser-crop img')
                            if figure_elem:
                                image_url = figure_elem.get('src') or figure_elem.get('data-src')
                        
                        # Skip placeholder images, but log what we found
                        if image_url and image_url.startswith('data:image/'):
                            logger.info(f"Found placeholder image, looking for real image in parent structure")
                            # Try to find the real image in the surrounding structure
                            for elem in parent.select('img'):
                                src = elem.get('src') or elem.get('data-src')
                                if src and not src.startswith('data:image/') and 'avrotros.nl' in src:
                                    image_url = src
                                    logger.info(f"Found real image: {src}")
                                    break
                            else:
                                image_url = None
                    
                    alert = {
                        'title': title,
                        'description': f'Nieuws van AVROTROS Opgelicht: {title}',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'url': full_url,
                        'image_url': image_url
                    }
                    alerts.append(alert)
            
            # If no preloader items found, try other selectors including teaser elements
            if not alerts:
                logger.info("No preloader items found, trying other selectors...")
                selectors = [
                    '.teaser',
                    '.teaser-crop',
                    '.alert-item',
                    '.news-item',
                    '.article-item',
                    '.article',
                    '[class*="alert"]',
                    '[class*="news"]',
                    'article',
                    '.content-item'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        for element in elements:
                            alert = self._extract_alert_info(element)
                            if alert:
                                alerts.append(alert)
                        if alerts:
                            break
            
            # If still no alerts, create a sample alert to show the structure works
            if not alerts:
                alerts = [{
                    'title': 'Geen alerts gevonden',
                    'description': 'Er konden geen alerts worden opgehaald van de website. De site structuur is mogelijk gewijzigd.',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'url': main_url,
                    'image_url': None
                }]
            
            logger.info(f"Successfully scraped {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Error scraping alerts: {str(e)}")
            return [{
                'title': 'Fout bij ophalen alerts',
                'description': f'Er is een fout opgetreden bij het ophalen van de alerts: {str(e)}',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': self.alerts_url,
                'image_url': None
            }]
    
    def _fallback_to_requests(self):
        """Fallback to requests if selenium fails"""
        logger.info("Falling back to requests method...")
        try:
            main_url = "https://opgelicht.avrotros.nl/"
            response = self.session.get(main_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            alerts = []
            
            # Same parsing logic as before but with fallback
            selectors = ['.teaser', '.teaser-crop', '.article']
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        alert = self._extract_alert_info(element)
                        if alert:
                            alerts.append(alert)
                    if alerts:
                        break
            
            if not alerts:
                alerts = [{
                    'title': 'Geen alerts gevonden (fallback)',
                    'description': 'Er konden geen alerts worden opgehaald van de website.',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'url': main_url,
                    'image_url': None
                }]
            
            return alerts
            
        except Exception as e:
            logger.error(f"Fallback method also failed: {str(e)}")
            return [{
                'title': 'Fout bij ophalen alerts',
                'description': f'Er is een fout opgetreden: {str(e)}',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': self.alerts_url,
                'image_url': None
            }]
    
    def _extract_alert_info(self, element):
        """Extract alert information from a DOM element"""
        try:
            # Try to find title
            title = None
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '[class*="title"]', 'a']
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    break
            
            # Try to find description - look for teaser-test specifically
            description = None
            desc_selectors = ['.teaser-text', 'p', '.description', '[class*="desc"]', '.content', '.teaser']
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem and desc_elem.get_text(strip=True):
                    description = desc_elem.get_text(strip=True)
                    break
            
            # Try to find image from teaser-crop figure elements
            image_url = None
            # Look for the specific teaser-figure-image class first
            img_elem = element.select_one('.teaser-figure-image')
            if img_elem:
                # Try src first, then data-src
                image_url = img_elem.get('src') or img_elem.get('data-src')
            
            # If no teaser-figure-image, try figure with teaser-crop class
            if not image_url:
                figure_elem = element.select_one('figure.teaser-crop img')
                if figure_elem:
                    image_url = figure_elem.get('src') or figure_elem.get('data-src')
            
            # If still no image, try other image selectors
            if not image_url:
                img_selectors = ['img', '.image img', '[class*="image"] img', 'figure img']
                for selector in img_selectors:
                    img_elem = element.select_one(selector)
                    if img_elem:
                        image_url = img_elem.get('src') or img_elem.get('data-src')
                        # Skip placeholder/lazy loading images
                        if image_url and not image_url.startswith('data:image/'):
                            break
                        else:
                            image_url = None
            
            # Final attempt: look for any avrotros image in the entire element
            if not image_url:
                for img in element.select('img'):
                    src = img.get('src') or img.get('data-src')
                    if src and not src.startswith('data:image/') and 'avrotros.nl' in src:
                        image_url = src
                        logger.info(f"Found avrotros image: {src}")
                        break
            
            # Try to find date
            date_text = datetime.now().strftime('%Y-%m-%d')
            date_selectors = ['.date', '[class*="date"]', 'time']
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    raw_date = date_elem.get_text(strip=True)
                    # Clean up date text - remove icon class names and other artifacts
                    date_text = re.sub(r'clockOval\s*\d*', '', raw_date).strip()
                    # Remove other common artifacts like standalone numbers or dashes
                    date_text = re.sub(r'^\d+$', '', date_text).strip()
                    date_text = re.sub(r'^-\d+-\d+$', '', date_text).strip()
                    if not date_text or len(date_text) < 3:
                        date_text = datetime.now().strftime('%Y-%m-%d')
                    break
            
            # Try to find URL
            url = "https://opgelicht.avrotros.nl/"
            link_elem = element.select_one('a')
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    url = self.base_url + href
                elif href.startswith('http'):
                    url = href
            
            if title and len(title) > 3:  # Only return if we have a meaningful title
                return {
                    'title': title,
                    'description': description or 'Geen beschrijving beschikbaar',
                    'date': date_text,
                    'url': url,
                    'image_url': image_url
                }
            
        except Exception as e:
            logger.error(f"Error extracting alert info: {str(e)}")
        
        return None

# Initialize scraper
scraper = AlertScraper()

@app.route('/')
def index():
    """Main page showing all alerts"""
    alerts = scraper.get_alerts()
    return render_template('index.html', alerts=alerts)

@app.route('/api/alerts')
def api_alerts():
    """API endpoint to get alerts as JSON"""
    alerts = scraper.get_alerts()
    return jsonify(alerts)

@app.route('/refresh')
def refresh():
    """Refresh alerts and redirect to main page"""
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)