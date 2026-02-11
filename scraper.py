import requests
from bs4 import BeautifulSoup
import re
import time
import random

def extract_offers(linkedin_api):
  keywords = ["Deloitte", "Accenture", "KPMG", "EY", "Capgemini", "PwC", "Indra", "NTT Data", "BCG", "Kyndryl"]
  for keyword in keywords:
    i = 0
    while True:
      parameters = {'keywords': keyword, 'location': 'Spain', 'start': i}
      
      try:
        response = requests.get(linkedin_api, params=parameters)
      except requests.exceptions.RequestException as e:
        print(f"Error al obtener las ofertas para {keyword}: {e}")
        break

      soup = BeautifulSoup(response.text, 'html.parser')
      jobs = soup.find_all('li')

      if len(jobs) == 0:
        break

      for job in jobs:
        i+=1

        title = job.find('h3', class_=re.compile("title")).get_text(strip=True)
        company = job.find('h4', class_=re.compile("subtitle")).get_text(strip=True)
        location = job.find('span', class_=re.compile("location")).get_text(strip=True)
        a_link = job.find('a', class_=re.compile("full-link"))
        link = a_link["href"] if a_link and a_link.has_attr("href") else ""

        offer = {
          "title": title,
          "company": company,
          "location": location,
          "link": link
        }

        print(f"Oferta {i}: {title}")
        print(f"Empresa: {company}")
        print(f"Ubicación: {location}")
        print(f"Enlace: {link}")
        print("-" * 50)

        print(f"Se han mostrado {i} ofertas para {keyword}\n")

        time.sleep(random.uniform(0,1))
      time.sleep(random.uniform(1,2))

if __name__ == "__main__":
  linkedin_api = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
  extract_offers(linkedin_api)
