from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import parsers.tax as tax_parser
import parsers.clerk as clerk_parser
import parsers.property_details as property_details_parser

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ScrapeRequest(BaseModel):
    county: str  # County name (e.g., "sublette", "fremont", "lincoln")
    links: Dict[str, Optional[str]]  # keys can be: tax, clerk, property_details

@app.post("/scrape")
async def scrape_endpoint(request: ScrapeRequest):
    """
    Scrape property information from the provided links.
    """
    try:
        result = {
            "tax": None,
            "clerk": None,
            "property_details": None
        }
        
        # Process each link type
        if request.links.get("tax"):
            try:
                result["tax"] = tax_parser.scrape_tax(request.links["tax"], county=request.county)
            except Exception as e:
                print(f"Tax scraper error: {e}")
                result["tax"] = None
        
        if request.links.get("clerk"):
            try:
                result["clerk"] = clerk_parser.scrape_clerk(request.links["clerk"], county=request.county)
            except Exception as e:
                print(f"Clerk scraper error: {e}")
                result["clerk"] = None
        
        if request.links.get("property_details"):
            try:
                result["property_details"] = property_details_parser.scrape_property_details(
                    request.links["property_details"], 
                    config={"county": request.county}
                )
            except Exception as e:
                print(f"Property details scraper error: {e}")
                result["property_details"] = None
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 