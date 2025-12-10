# omdb_client.py
import requests
from typing import Dict, Any, List, Optional

from config import OMDB_API_KEY

BASE_URL = "http://www.omdbapi.com/"


class OMDbError(Exception):
    pass


def search_movies(query: str, page: int = 1) -> List[Dict[str, Any]]:
    params = {
        "apikey": OMDB_API_KEY,
        "s": query,
        "page": page,
    }
    resp = requests.get(BASE_URL, params=params)
    data = resp.json()
    if data.get("Response") == "False":
        # no results or error
        if data.get("Error") == "Movie not found!":
            return []
        raise OMDbError(data.get("Error", "Unknown OMDb error"))
    return data.get("Search", [])


def get_movie_details(imdb_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    if not imdb_id and not title:
        raise ValueError("Provide either imdb_id or title")

    params = {
        "apikey": OMDB_API_KEY,
        "plot": "full"
    }
    if imdb_id:
        params["i"] = imdb_id
    else:
        params["t"] = title

    resp = requests.get(BASE_URL, params=params)
    data = resp.json()
    if data.get("Response") == "False":
        raise OMDbError(data.get("Error", "Unknown OMDb error"))
    return data
