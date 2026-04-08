from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import asyncio
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


# ----------- APA FORMAT -----------

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


# ----------- Async Crossref -----------

async def search_crossref(client, title):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 1}

    try:
        r = await client.get(url, params=params, timeout=5)
        data = r.json()

        if not data["message"]["items"]:
            return None

        return data["message"]["items"][0]

    except:
        return None


# ----------- Async DOI Check -----------

async def check_doi_link(client, doi):
    url = f"https://doi.org/{doi}"

    try:
        response = await client.get(
            url,
            timeout=5,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if "doi.org" in str(response.url):
            return False

        if response.status_code >= 400:
            return False

        return True

    except:
        return False


# ----------- VALIDATION FILTER -----------

def is_valid_paper(item):
    if not item.get("author"):
        return False

    if not item.get("container-title"):
        return False

    title = item.get("title", [""])[0].lower()

    if any(x in title for x in ["figure", "review", "call for papers"]):
        return False

    return True


# ----------- PROCESS SINGLE REFERENCE -----------

async def process_reference(ref, client, semaphore):
    async with semaphore:

        title = extract_title(ref)
        crossref = await search_crossref(client, title)

        if crossref and crossref.get("DOI") and is_valid_paper(crossref):
            doi = crossref.get("DOI")

            if await check_doi_link(client, doi):
                return {
                    "status": "verified",
                    "formatted": format_apa(crossref)
                }

            return {
                "status": "uncertain",
                "formatted": format_apa(crossref)
            }

        return {
            "status": "not_found",
            "formatted": ref
        }


# ----------- MAIN ENDPOINT -----------

@app.post("/verify-batch")
async def verify_batch(request: ReferenceRequest):

    semaphore = asyncio.Semaphore(10)  # limit concurrency

    async with httpx.AsyncClient() as client:

        tasks = [
            process_reference(ref, client, semaphore)
            for ref in request.references
        ]

        results = await asyncio.gather(*tasks)

    verified_count = sum(1 for r in results if r["status"] == "verified")
    not_found_count = len(results) - verified_count

    return {
        "summary": {
            "verified": verified_count,
            "not_found": not_found_count
        },
        "results": results
    }
