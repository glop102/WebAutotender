# Serves static HTML pages, static JS scripts, and also HTMX endpoints

from fastapi import Response,status,APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/")
def get_homepage_file():
    print(__file__)
    return HTMLResponse("debug sucessful!")