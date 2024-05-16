# Serves static HTML pages, static JS scripts, and also HTMX endpoints

import pathlib

from fastapi import Response,status,APIRouter
from fastapi.responses import HTMLResponse

import pipeline_backend

"""
TODO
- spawn instance
  - popup window figured out
  - loading only a single instance after it spawns
  - consolidate the put/get info for the HTML <-> Object representations for easier API state syncing
- summary status at the top of the page with some sort of info
- instances have variable pinning to give some differentiating information that is useful
- editing popups
- buttons for pausing/running an instance
  - and to force an instance to run right away
- realtime updates from callbacks of the pipeline manager over a websocket for updating the page
- when hovering over a processing step in an instance, highlight the process and step of the process in the workflow details
"""

root_file_folder = pathlib.Path(__file__).absolute().parent / "files"

router = APIRouter()

@router.get("/",response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
def get_homepage_file():
    try:
        f = open(root_file_folder / "index.html")
    except FileNotFoundError:
        return HTMLResponse("Unable to find the UI File",status_code=status.HTTP_404_NOT_FOUND)
    return f.read()

@router.get("/index2.html", response_class=HTMLResponse)
def get_homepage_file():
    try:
        f = open(root_file_folder / "index2.html")
    except FileNotFoundError:
        return HTMLResponse("Unable to find the UI File", status_code=status.HTTP_404_NOT_FOUND)
    return f.read()

@router.get("/js/{filename}")
def get_javascript_file(filename:str):
    js_folder = root_file_folder / "js"
    req_js_path = (js_folder / filename).resolve()
    if not js_folder in req_js_path.parents:
        return Response("Forbidden",status_code=status.HTTP_403_FORBIDDEN)
    if not req_js_path.exists():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    if not req_js_path.is_file():
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    f = open(req_js_path)
    return Response(f.read(), media_type="text/javascript")

@router.get("/image/{filename}")
def get_image_file(filename: str):
    image_folder = root_file_folder / "image"
    req_image_path = (image_folder / filename).resolve()
    if not image_folder in req_image_path.parents:
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if not req_image_path.exists():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    if not req_image_path.is_file():
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    f = open(req_image_path)
    return Response(f.read(), media_type="image")

@router.get("/styles/{filename}")
def get_css_style_file(filename: str):
    style_folder = root_file_folder / "styles"
    req_style_path = (style_folder / filename).resolve()
    if not style_folder in req_style_path.parents:
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if not req_style_path.exists():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    if not req_style_path.is_file():
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    f = open(req_style_path)
    return Response(f.read(), media_type="text/css")

@router.get("/favicon.ico")
def get_favicon_file():
    favicon = root_file_folder / "image" / "favicon.ico"
    if not favicon.exists():
        return Response("Unable to find the File", status_code=status.HTTP_404_NOT_FOUND)
    if not favicon.is_file():
        return Response("Forbidden", status_code=status.HTTP_403_FORBIDDEN)
    f = open(favicon,"rb")
    return Response(f.read(), media_type="image/ico")
