import logging
import requests
import re
import datetime
from bs4 import BeautifulSoup
from flathunter.abstract_crawler import Crawler

class CrawlEbayKleinanzeigen(Crawler):
    __log__ = logging.getLogger(__name__)
    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'
    URL_PATTERN = re.compile(r'https://www\.ebay-kleinanzeigen\.de')
    MONTHS = {
      "Januar": "01",
      "Februar": "02",
      "März": "03",
      "April": "04",
      "Mai": "05",
      "Juni": "06",
      "Juli": "07",
      "August": "08",
      "September": "09",
      "Oktober": "10",
      "November": "11",
      "Dezember": "12"
    }

    def __init__(self):
        logging.getLogger("requests").setLevel(logging.WARNING)

    def get_results(self, search_url, max_pages=None):
        self.__log__.debug("Got search URL %s" % search_url)

        soup = self.get_page(search_url)

        # get data from first page
        entries = self.extract_data(soup)
        self.__log__.debug('Number of found entries: ' + str(len(entries)))

        return entries

    def get_page(self, search_url):
        resp = requests.get(search_url, headers={'User-Agent': self.USER_AGENT})  # TODO add page_no in url
        if resp.status_code != 200:
            self.__log__.error("Got response (%i): %s" % (resp.status_code, resp.content))
        return BeautifulSoup(resp.content, 'html.parser')

    def get_expose_details(self, expose):
        soup = self.get_page(expose['url'])
        for detail in soup.find_all('li', { "class": "addetailslist--detail" }):
            if re.match(r'Verfügbar ab', detail.text):
                date_string = re.match(r'(\w+) (\d{4})', detail.text)
                if date_string is not None:
                    expose['from'] = "01." + self.MONTHS[date_string[1]] + "." + date_string[2]
        if 'from' not in expose:
            expose['from'] = datetime.datetime.now().strftime('%02d.%02m.%Y')
        return expose

    def extract_data(self, soup):
        entries = list()
        soup = soup.find(id="srchrslt-adtable")
        try:
            title_elements = soup.find_all(lambda e: e.has_attr('class') and 'ellipsis' in e['class'])
        except AttributeError:
            return entries
        expose_ids = soup.find_all("article", class_="aditem")

        # soup.find_all(lambda e: e.has_attr('data-adid'))
        # print(expose_ids)
        for idx, title_el in enumerate(title_elements):
            price = expose_ids[idx].find("strong").text
            tags = expose_ids[idx].find_all(class_="simpletag tag-small")
            url = "https://www.ebay-kleinanzeigen.de" + title_el.get("href")
            address = expose_ids[idx].find("div", {"class": "aditem-details"})
            address.find("strong").extract()
            address.find("br").extract()
            image_element = expose_ids[idx].find("div", {"class": "srpimagebox"})
            if image_element is not None:
                image = image_element["data-imgsrc"]
            else:
                image = None
            self.__log__.debug(address.text.strip())
            address = address.text.strip()
            address = address.replace('\n', ' ').replace('\r', '')
            address = " ".join(address.split())
            try:
                self.__log__.debug(tags[1].text)
                rooms = re.match(r'(\d+)', tags[1].text)[1]
            except IndexError:
                self.__log__.debug("Keine Zimmeranzahl gegeben")
                rooms = "Nicht gegeben"
            try:
                self.__log__.debug(tags[0].text)
                size = tags[0].text
            except IndexError:
                size = "Nicht gegeben"
                self.__log__.debug("Quadratmeter nicht angegeben")
            details = {
                'id': int(expose_ids[idx].get("data-adid")),
                'image': image,
                'url': url,
                'title': title_el.text.strip(),
                'price': price,
                'size': size,
                'rooms': rooms,
                'address': address,
                'crawler': self.get_name()
            }
            entries.append(details)

        self.__log__.debug('extracted: ' + str(entries))

        return entries

    @staticmethod
    def load_address(url):
        # extract address from expose itself
        expose_html = requests.get(url, headers={'User-Agent': CrawlEbayKleinanzeigen.USER_AGENT}).content
        expose_soup = BeautifulSoup(expose_html, 'html.parser')
        try:
            street_raw = expose_soup.find(id="street-address").text
        except AttributeError:
            street_raw = ""
        try:
            address_raw = expose_soup.find(id="viewad-locality").text
        except AttributeError:
            address_raw = ""
        address = address_raw.strip().replace("\n", "") + " " + street_raw.strip()

        return address
