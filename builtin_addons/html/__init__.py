# Serves static HTML pages, static JS scripts, and also HTMX endpoints

from fastapi import Response,status,APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()