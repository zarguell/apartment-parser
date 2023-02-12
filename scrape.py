import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Function to get the URLs of the Craigslist listings
def get_craigslist_urls(search_url):
    # Set up options for the Chrome browser to run in headless mode
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument('--disable-gpu')
    options.add_argument('start-maximized')
    options.add_argument('disable-infobars')
    options.add_argument('--disable-gpu-sandbox')
    options.add_argument('--no-sandbox')

    # Start the Chrome browser using the options defined above
    driver = webdriver.Chrome(options=options)
    driver.get(search_url)

    # Wait for 5 seconds to allow the page to load
    time.sleep(5)

    # Use WebDriverWait to wait until all the elements with the class "titlestring" are present on the page
    wait = WebDriverWait(driver, 20)
    links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.titlestring")))

    # Extract the URLs of the listings from the elements found above
    urls = [link.get_attribute("href") for link in links]

    # Quit the browser
    driver.quit()

    # Return the list of URLs
    return urls

def parse_craigslist_info(url):
    # Make a request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the information you need
        beds_baths = soup.select_one('span.shared-line-bubble')
        beds = beds_baths.find_all('b')[0].text
        baths = beds_baths.find_all('b')[1].text
        sqft = soup.select_one('span.shared-line-bubble:-soup-contains("ft")').text.strip().split('ft')[0].strip()
        price = soup.select_one('span.price').text.strip().replace('$', '')

        title = soup.select_one('span#titletextonly').text.strip()

        # Try to extract the address, and if it fails, print a message and move on
        try:
            address = soup.select_one('div.mapaddress').text.strip()
        except AttributeError:
            address = None
            print("Address not found, moving on...")

        # Select the span containing sidebar attributes to parse data
        attributes = soup.select('p.attrgroup span')

        cats = 'Not OK'
        dogs = 'Not OK'
        for attribute in attributes:
            if 'cats are OK' in attribute.text:
                cats = 'OK'
            elif 'dogs are OK' in attribute.text:
                dogs = 'OK'

        furnished = 'No'
        if 'furnished' in [a.text.strip() for a in attributes]:
            furnished = 'Yes'

        condo = 'No'
        if 'condo' in [a.text.strip() for a in attributes]:
            condo = 'Yes'

        wd = 'No'
        if 'w/d in unit' in [a.text.strip() for a in attributes]:
            wd = 'Yes'

        garage = 'No'
        if 'attached garage' in [a.text.strip() for a in attributes]:
            garage = 'Yes'

        rent_period = 'Unknown'
        for attribute in attributes:
            if 'rent period:' in attribute.text:
                rent_period = attribute.find('b').text

        # Parse the posting body
        postingbody = soup.select_one('section#postingbody')
        qr_code_divs = postingbody.select('div.print-information')

        for div in qr_code_divs:
            div.decompose()

        description = postingbody.text.strip()


        # Format the information as a JSON object
        result = {
            'beds': beds if beds else None,
            'baths': baths if baths else None,
            'sqft': sqft if sqft else None,
            'price': price if price else None,
            'cats': cats is not None,
            'dogs': dogs is not None,
            'furnished': furnished is not None,
            'condo': condo is not None,
            'washer_dryer': wd is not None,
            'garage': garage is not None,
            'rent_period': rent_period if rent_period else None,
            'address': address if address else None,
            'title': title if title else None,
            'url': url if url else None,
            'description': description if description else None
        }

        return result
    else:
        raise Exception('Failed to fetch the URL')

# Function to post to a NoCoDB instance. Assumes you have a table configured with the columns matching the JSON data returned by previous parsing function.
def post_to_nocodb(url, data, token):
    headers = {
        'accept': 'application/json',
        'xc-token': token,
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Data successfully posted to Nocodb API")
    else:
        print(f"Error posting data to Nocodb API. Response status code: {response.status_code}")


if __name__ == '__main__':
    # set search parameters
    city = "newyork"
    max_bedrooms = "1"
    max_price = "2000"
    minSqft = "500"
    postal = "10001"
    search_distance = "2"

    # set nocodb endpoint
    noco = "https://nocodb.example.com/api/v1/db/data/v1/rent/craigslist"
    api_token = "myapikey"
    
    # craft craigslist search
    search_url = f"https://{city}.craigslist.org/search/apa?max_bedrooms={max_bedrooms}&max_price={max_price}&minSqft={minSqft}&postal={postal}&search_distance={search_distance}"
    
    # get listing urls, iterate through, posting data to nocodb
    urls = get_craigslist_urls(search_url)
    for url in urls:
        print(url)
        r = parse_craigslist_info(url)
        post_to_nocodb(noco,r,api_token)