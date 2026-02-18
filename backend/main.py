from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any
import pandas as pd
import json
import uvicorn

app = FastAPI()

# Temporary store
session_data = {
    "df": None,
    "columns": [],
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your EC2 IP
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Excel Backend API is running"}

@app.post("/upload/")
async def upload_excel(file: UploadFile = File(...)):
    contents = await file.read()
    with open("temp.xlsx", "wb") as f:
        f.write(contents)

    try:
        excel_file = pd.ExcelFile("temp.xlsx")
        return {"sheets": excel_file.sheet_names}
    except Exception as e:
        return {"error": f"Failed to read Excel: {str(e)}"}

@app.post("/select-sheet/")
async def select_sheet(sheet_name: str = Form(...)):
    try:
        df = pd.read_excel("temp.xlsx", sheet_name=sheet_name)
        session_data["df"] = df
        session_data["columns"] = df.columns.tolist()
        return {"columns": session_data["columns"]}
    except Exception as e:
        return {"error": f"Failed to load sheet: {str(e)}"}

@app.get("/search/")
def search_data(filters: Optional[str] = None, columns: Optional[str] = None):
    df = session_data.get("df")
    if df is None:
        return []

    result_df = df.copy()

    if filters:
        try:
            filters_obj = json.loads(filters)
            if isinstance(filters_obj, list) and all(isinstance(f, dict) for f in filters_obj):
                for filter_item in filters_obj:
                    field = filter_item.get("field")
                    query = filter_item.get("query")
                    exact = filter_item.get("exact", False)
                    
                    if field and query and field in result_df.columns:
                        if exact:
                            result_df = result_df[result_df[field].astype(str) == str(query)]
                        else:
                            result_df = result_df[result_df[field].astype(str).str.contains(str(query), case=False, na=False)]
        except Exception as e:
            print(f"Filter error: {e}")
            pass

    if columns:
        cols = [col.strip() for col in columns.split(",") if col.strip() in result_df.columns]
        if cols:
            result_df = result_df[cols]

    return result_df.fillna("").to_dict(orient="records")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)