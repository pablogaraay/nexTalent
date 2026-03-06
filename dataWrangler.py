from dbConn import MongoManager
from config import Config
import pandas as pd

class DataWrangler:

  def get_df():
    db = MongoManager()
    offers = db.load_offers(Config.SCRAPED_COLL)
    df = pd.DataFrame(offers)
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
    print("Se renombran los campos description y location a campos raw y se estructura la localizacion")
    df_structured = df.copy()
    df_structured = df_structured.rename(columns={"location": "location_raw", "description": "description_raw"})
    df_structured["location_num_parts"] = df_structured["location_raw"].astype(str).str.split(",").str.len()

    parts = df_structured["location_raw"].astype(str).str.split(",", expand=True)

    df_structured["city"] = None
    df_structured["region"] = None
    df_structured["country"] = None

    for col in parts.columns:
      parts[col] = parts[col].str.strip()
      if col == 0:
        df_structured["city"] = parts[col]
      elif col == 1:
        df_structured["region"] = parts[col]
      elif col == 2:
        df_structured["country"] = parts[col]

    df_structured["location_structured"] = df_structured["location_num_parts"] == 3
    
    return df_structured



    
if __name__ == "__main__":
  df = DataWrangler.get_df()
  print(df.head(3))
  print(df.info())
  DataWrangler.check_empty_values(df)
