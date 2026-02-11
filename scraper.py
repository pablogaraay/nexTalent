import requests
from bs4 import BeautifulSoup
import re
import time
import random
from config import Config

def get_description(offer_link):
  try:
    response = requests.get(offer_link)
  except requests.exceptions.RequestException as e:
    print(f"Error al obtener la descripción de la oferta {offer_link}: {e}")
    return ""

  soup = BeautifulSoup(response.text, 'html.parser')
  try:
    description = soup.find('div', class_=re.compile("show-more-less-html__markup")).get_text(strip=True)
    
    try:
      details_list = soup.find_all('li', class_=re.compile("description__job-criteria"))
      details = ""
      for detail in details_list:
        title = detail.find('h3').get_text(strip=True)
        value = detail.find('span').get_text(strip=True)
        details += f"{title}: {value}\n"
      info = description + "\n\n" + details
      return info
    
    except AttributeError:
      print(f"Error al obtener los detalles de la oferta {offer_link}")
      return description
  except AttributeError:
    print(f"Error al obtener la descripcion de la oferta {offer_link}")
    return ""
  

def extract_offers(linkedin_api):
  for keyword in Config.KEYWORDS:
    i = 0
    while True:
      parameters = {'keywords': keyword, 'location': Config.LOCATION, 'start': i}
      try:
        response = requests.get(linkedin_api, params=parameters)
      except requests.exceptions.RequestException as e:
        print(f"Error al obtener las ofertas para {keyword}: {e}")
        break

      soup = BeautifulSoup(response.text, 'html.parser')
      jobs = soup.find_all('li')

      if len(jobs) == 0:
        print(f"No se han encontrado mas ofertas de {keyword}. Codigo de estado: {response.status_code}\n")
        break

      for job in jobs:
        i+=1

        title = job.find('h3', class_=re.compile("title")).get_text(strip=True)
        company = job.find('h4', class_=re.compile("subtitle")).get_text(strip=True)
        location = job.find('span', class_=re.compile("location")).get_text(strip=True)
        a_link = job.find('a', class_=re.compile("full-link"))
        link = a_link["href"] if a_link and a_link.has_attr("href") else ""
        description = get_description(link) if link else ""

        offer = {
          "title": title,
          "company": company,
          "location": location,
          "link": link,
          "description": description
        }

        print(f"Titulo: {title}")
        print(f"Empresa: {company}")
        print(f"Ubicación: {location}")
        print(f"Enlace: {link}")
        print(f"Descripción: {description}")
        print("-" * 50)

        print(f"Se han mostrado {i} ofertas para {keyword}\n")

        time.sleep(random.uniform(0,1))
      time.sleep(random.uniform(1,2))

if __name__ == "__main__":
  extract_offers(Config.LINKEDIN_API)
