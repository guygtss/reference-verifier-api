from fastapi import FastAPI
from pydantic import BaseModel
import requests
import re

app = FastAPI()

# ----------- Request Model -----------

class ReferenceRequest(BaseModel):
    references: list[str]


# ----------- Helper: Extract Title -----------

def extract_title(ref: str):
    try:
        # Extract title after year
        match = re.search(r"\)\.\s(.+?)\.", ref)
        if match:
            return match.group(1)
        return ref
    except:
        return ref


# ----------- Helper: Query CrossRef -----------

def search_crossref(title: str):
    url = "https://api.crossref.org/works"
    params = {
        "query.title": title,
        "rows": 1
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()

        if not data["message"]["items"]:
            return None

        return data["message"]["items"][0]

    except:
        return None


# ----------- Helper: Format APA -----------

def format_apa(item):
    authors = item.get("author", [])
    author_str = ""

    for i, a in enumerate(authors):
        name = f"{a.get('family', '')}, {a.get('given', '')[:1]}."
        if i == len(authors) - 1 and i > 0:
            author_str += f" & {name}"
        elif i > 0:
            author_str += f", {name}"
        else:
            author_str += name

    year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
    title = item.get("title", [""])[0]
    journal = item.get("container-title", [""])[0]
    volume = item.get("volume", "")
    issue = item.get("issue", "")
    pages = item.get("page", "")
    doi = item.get("DOI", "")

    citation = f"{author_str} ({year}). {title}. *{journal}"

    if volume:
        citation += f", {volume}"
    if issue:
        citation += f"({issue})"
    if pages:
        citation += f", {pages}"

    citation += f". https://doi.org/{doi}"

    return citation


# ----------- Root -----------

@app.get("/")
def home():
    return {"message": "Batch Reference Verifier API is running"}


# ----------- Batch Endpoint -----------

@app.post("/verify-batch")
def verify_batch(request: ReferenceRequest):
    results = []

    for ref in request.references:
        title = extract_title(ref)
        data = search_crossref(title)

        if data:
            results.append({
                "status": "found",
                "formatted": format_apa(data)
            })
        else:
            results.append({
                "status": "not_found",
                "original": ref
            })

    return {
        "total": len(request.references),
        "results": results
    }
