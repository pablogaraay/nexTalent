from dbConn import MongoManager
from config import Config
import pandas as pd
import re

class DataWrangler:

  def get_df():
    db = MongoManager()
    offers = db.load_offers(Config.SCRAPED_COLL)
    df = pd.DataFrame(offers)
    db.close_connection()
    return df

  def check_empty_values(df):
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
 
  def structure_data(df):
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
      df_structured.loc[location_structured, "city"] = parts.loc[0]
    if 1 in parts.columns:
      df_structured.loc[location_structured, "region"] = parts.loc[1]
    if 2 in parts.columns:
      df_structured.loc[location_structured, "country"] = parts.loc[2]

    df_structured = df_structured.drop(columns=["_id"])
    
    return df_structured

  def save_structured_data(df_structured):
    print("Se guardan los datos estructurados en la coleccion offers_structured")
    db = MongoManager()
    offers_array = df_structured.to_dict(orient="records")
    db.upsert_bulk_offers_structured(Config.STRUCTURED_COLL, offers_array)
    db.close_connection()

  def is_non_empty_text(series):
    return series.notna() & (series.astype(str).str.strip() != "") & (series.astype(str).str.strip() != '""')
  
  def apply_cleaning_rules(df_structured):
    df_structured_copy = df_structured.copy()
    valid_urls = DataWrangler.is_non_empty_text(df_structured_copy["url"])
    valid_titles = DataWrangler.is_non_empty_text(df_structured_copy["title"])
    valid_companies = DataWrangler.is_non_empty_text(df_structured_copy["company"])
    valid_locations = DataWrangler.is_non_empty_text(df_structured_copy["location_raw"])
    valid_descriptions = DataWrangler.is_non_empty_text(df_structured_copy["description_raw"])

    valid_offers = valid_urls & valid_titles & valid_companies & valid_locations & valid_descriptions
    df_valid = df_structured_copy[valid_offers].copy()
    df_invalid = df_structured_copy[~valid_offers].copy()
    return df_valid, df_invalid

  def clean_description(df_valid):
    df_cleaned = df_valid.copy()
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
  
  def save_cleaned_data(df_cleaned):
    print("Se guardan los datos limpios en la coleccion offers_cleaned")
    db = MongoManager()
    offers_array = df_cleaned.to_dict(orient="records")
    db.upsert_bulk_offers_cleaned(Config.CLEANED_COLL, offers_array)
    db.close_connection()

if __name__ == "__main__":
  df = DataWrangler.get_df()
  DataWrangler.check_empty_values(df)
  df_structured = DataWrangler.structure_data(df)
  DataWrangler.save_structured_data(df_structured)
  df_valid, df_invalid = DataWrangler.apply_cleaning_rules(df_structured)
  print(df_invalid.head(10))
  df_cleaned = DataWrangler.clean_description(df_valid)
  DataWrangler.save_cleaned_data(df_cleaned)
