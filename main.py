from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/verify")
def verify(title: str):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 3}

    r = requests.get(url, params=params).json()
    items = r["message"]["items"]

    if not items:
        return {"status": "not_found"}

    best = items[0]

    return {
        "status": "found",
        "title": best.get("title", [""])[0],
        "authors": best.get("author", []),
        "year": best.get("issued", {}).get("date-parts", [[None]])[0][0],
        "journal": best.get("container-title", [""])[0],
        "doi": best.get("DOI")
    }
