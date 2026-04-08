from fastapi import FastAPI
from pydantic import BaseModel
import requests
import re

app = FastAPI()

class ReferenceRequest(BaseModel):
    references: list[str]


# ----------- Extract Title -----------

def extract_title(ref: str):
    try:
        match = re.search(r"\)\.\s(.+?)\.", ref)
        if match:
            return match.group(1)
        return ref
    except:
        return ref


# ----------- Crossref Search -----------

def search_crossref(title: str):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 1}

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()

        if not data["message"]["items"]:
            return None

        return data["message"]["items"][0]
    except:
        return None


# ----------- DOI Check -----------

def check_doi_link(doi: str):
    url = f"https://doi.org/{doi}"

    try:
        response = requests.get(
            url,
            timeout=5,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code >= 400:
            return False

        return True

    except:
        return False


# ----------- Filter Junk -----------

def is_valid_paper(item):
    if not item.get("author"):
        return False

    if not item.get("container-title"):
        return False

    title = item.get("title", [""])[0].lower()

    if any(x in title for x in ["figure", "review", "call for papers"]):
        return False

    return True


# ----------- APA Format -----------

def format_apa(item):
    authors = item.get("author", [])
    author_str = ""

    for i, a in enumerate(authors):
        name = f"{a.get('family', '')}, {a.get('given', '')[:1]}."
        if i == len(authors) - 1 and i > 0:
            author_str += f", & {name}"
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

    citation = f"{author_str} ({year}). {title}. {journal}"

    if volume:
        citation += f", {volume}"
    if issue:
        citation += f"({issue})"
    if pages:
        citation += f", {pages}"

    citation += f". https://doi.org/{doi}"

    return citation


# ----------- MAIN -----------

@app.post("/verify-batch")
def verify_batch(request: ReferenceRequest):

    results = []
    verified_count = 0
    not_found_count = 0

    for ref in request.references:

        title = extract_title(ref)
        crossref = search_crossref(title)

        if crossref and crossref.get("DOI") and is_valid_paper(crossref):

            doi = crossref.get("DOI")

            if check_doi_link(doi):
                results.append({
                    "status": "verified",
                    "formatted": format_apa(crossref)
                })
                verified_count += 1
            else:
                results.append({
                    "status": "uncertain",
                    "formatted": format_apa(crossref)
                })
                not_found_count += 1

        else:
            results.append({
                "status": "not_found",
                "formatted": ref
            })
            not_found_count += 1

    return {
        "summary": {
            "verified": verified_count,
            "not_found": not_found_count
        },
        "results": results
    }
