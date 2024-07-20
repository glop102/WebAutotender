# Serves static HTML pages, static JS scripts, and also HTMX endpoints

import pathlib
import mimetypes

from fastapi import Response,status,APIRouter
from fastapi.responses import HTMLResponse

import pipeline_backend

"""
TODO
- summary status at the top of the page with some sort of info
- when hovering over a processing step in an instance, highlight the process and step of the process in the workflow details
"""

root_file_folder = pathlib.Path(__file__).absolute().parent / "static"

router = APIRouter()

@router.get("/",response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
def get_homepage_file():
    try:
        f = open(root_file_folder / "index.html")
    except FileNotFoundError:
        return HTMLResponse("Unable to find the UI File",status_code=status.HTTP_404_NOT_FOUND)
    return f.read()

@router.get("/assets/{filename}")
def get_asset_file(filename:str):
    asset_folder = root_file_folder / "assets"
    req_asset_path = (asset_folder / filename).resolve()
    if not asset_folder in req_asset_path.parents:
        return Response("Forbidden",status_code=status.HTTP_403_FORBIDDEN)
    if not req_asset_path.exists():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    if not req_asset_path.is_file():
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    f = open(req_asset_path,"rb")
    mimetype,encoding = mimetypes.guess_type(req_asset_path)
    return Response(f.read(), media_type=mimetype)

@router.get("/favicon.ico")
def get_favicon_file():
    favicon = root_file_folder / "assets" / "favicon.ico"
    if not favicon.exists() or not favicon.is_file():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    f = open(favicon,"rb")
    return Response(f.read(), media_type="image/ico")
