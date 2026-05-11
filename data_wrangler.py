from db_conn import MongoManager
from config import Config
import pandas as pd

class DataWrangler:
  def __init__(self):
    self.db = MongoManager()

  def close(self):
    if self.db:
      self.db.close_connection()

  def get_df(self):
    offers = self.db.load_offers(Config.SCRAPED_COLL, active_only=True)
    df = pd.DataFrame(offers)
    return df

  def check_empty_values(self, df):
    print("Se comprueban las campos con valores nulos, dobles comillas o vacios")
    rows = []

    for col in df.columns:
      null_count = int(df[col].isna().sum())
      double_quotes_count = int((df[col].astype(str).str.strip() == '""').sum())
      empty_string_count = int((df[col].astype(str).str.strip() == "").sum())
      valid_count = len(df) - null_count - double_quotes_count - empty_string_count
      
      rows.append({
        "col": col,
        "null_count": null_count,
        "double_quotes_count": double_quotes_count,
        "empty_string_count": empty_string_count,
        "valid_count": valid_count
      })
    print(rows)
 
  def structure_data(self, df):
    print("Se renombran los campos description y location a campos raw, se estructura la localizacion y se elimina _id para evitar problemas de duplicados")
    df_structured = df.copy()
    df_structured = df_structured.rename(columns={"location": "location_raw", "description": "description_raw"})
    df_structured["location_num_parts"] = df_structured["location_raw"].astype(str).str.split(",").str.len()

    parts = df_structured["location_raw"].astype(str).str.split(",", expand=True)

    df_structured["location_structured"] = df_structured["location_num_parts"] == 3

    df_structured["city"] = None
    df_structured["region"] = None
    df_structured["country"] = None

    for col in parts.columns:
      parts[col] = parts[col].str.strip()
    
    location_structured = df_structured["location_structured"]
    if 0 in parts.columns:
      df_structured.loc[location_structured, "city"] = parts[0]
    if 1 in parts.columns:
      df_structured.loc[location_structured, "region"] = parts[1]
    if 2 in parts.columns:
      df_structured.loc[location_structured, "country"] = parts[2]

    df_structured = df_structured.drop(columns=["_id"])
    
    return df_structured

  def save_structured_data(self, df_structured):
    print("Se guardan los datos estructurados en la coleccion offers_structured")
    offers_array = df_structured.to_dict(orient="records")
    self.db.upsert_bulk_offers(Config.STRUCTURED_COLL, offers_array, "structured")

  def is_non_empty_text(self, series):
    return series.notna() & (series.astype(str).str.strip() != "") & (series.astype(str).str.strip() != '""')
  
  def filter_valid_offers(self, df_company_cleaned):
    df_structured_copy = df_company_cleaned.copy()
    valid_urls = self.is_non_empty_text(df_structured_copy["url"])
    valid_titles = self.is_non_empty_text(df_structured_copy["title"])
    valid_companies = self.is_non_empty_text(df_structured_copy["company"])
    valid_locations = self.is_non_empty_text(df_structured_copy["location_raw"])
    valid_descriptions = self.is_non_empty_text(df_structured_copy["description_raw"])

    valid_offers = valid_urls & valid_titles & valid_companies & valid_locations & valid_descriptions
    df_valid = df_structured_copy[valid_offers].copy()
    df_invalid = df_structured_copy[~valid_offers].copy()
    return df_valid, df_invalid

  def filter_company_by_kw(self, df_valid):
    keywords = Config.KEYWORDS
    pattern = "|".join(keywords)
    df_company_cleaned = df_valid[df_valid["company"].str.contains(pattern, case=False, na=False)].copy()
    return df_company_cleaned
  

  def clean_description(self, df_company_cleaned):
    df_cleaned = df_company_cleaned.copy()
    df_cleaned["description_clean"] = (
      df_cleaned["description_raw"]
      .str.replace(r"\r\n", "\n", regex=True)
      .str.replace(r"\r", "\n", regex=True)
      .str.replace(r"\t", " ", regex=True)
      .str.replace(r"\n+", "\n", regex=True)
      .str.replace(r"[ ]+", " ", regex=True)
      .str.replace(
      r"([a-záéíóúñ](?=[A-ZÁÉÍÓÚÑ])|[.!?](?=[A-ZÁÉÍÓÚÑa-záéíóúñ]))",
      r"\1 ",
      regex=True
      )
      .str.strip()
    )
    return df_cleaned
  
  def save_cleaned_data(self, df_cleaned):
    print("Se guardan los datos limpios en la coleccion offers_cleaned")
    offers_array = df_cleaned.to_dict(orient="records")
    self.db.upsert_bulk_offers(Config.CLEANED_COLL, offers_array, "cleaned")

if __name__ == "__main__":
  dw = DataWrangler()
  try:
    df = dw.get_df()
    dw.check_empty_values(df)
    df_structured = dw.structure_data(df)
    dw.save_structured_data(df_structured)
    df_valid, df_invalid = dw.filter_valid_offers(df_structured)
    print(df_invalid.head(10))
    df_company_cleaned = dw.filter_company_by_kw(df_valid)
    df_cleaned = dw.clean_description(df_company_cleaned)
    dw.save_cleaned_data(df_cleaned)
  finally:
    dw.close()
