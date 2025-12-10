from __future__ import annotations
import requests
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from requests.adapters import HTTPAdapter, Retry

try:
    from config import TMDB_API_KEY, BASE_DIR, OMDB_API_KEY
except Exception:
    import os
    TMDB_API_KEY = os.getenv('TMDB_API_KEY')
    OMDB_API_KEY = os.getenv('OMDB_API_KEY')
    BASE_DIR = Path('.')

API_BASE = 'https://api.themoviedb.org/3'
IMAGE_BASE = 'https://image.tmdb.org/t/p'
POSTER_SIZE = 'w500'
CACHE_FILE = BASE_DIR / 'tmdb_cache.json'
CACHE_TTL = 60 * 60  # 1 hour

_session = requests.Session()
_retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
adapter = HTTPAdapter(max_retries=_retry)
_session.mount('https://', adapter)
_session.mount('http://', adapter)


def _load_cache() -> Dict[str, Any]:
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            now = time.time()
            # drop expired
            keys = list(data.keys())
            changed = False
            for k in keys:
                e = data.get(k)
                if not e:
                    continue
                if e.get('ts', 0) + e.get('ttl', CACHE_TTL) < now:
                    del data[k]
                    changed = True
            if changed:
                with open(CACHE_FILE, 'w', encoding='utf-8') as fw:
                    json.dump(data, fw)
            return data
    except Exception:
        return {}
    return {}


def _save_cache(cache: Dict[str, Any]):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f)
    except Exception:
        pass


def _cache_get(key: str) -> Optional[Any]:
    c = _load_cache()
    entry = c.get(key)
    if not entry:
        return None
    return entry.get('value')


def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL):
    c = _load_cache()
    c[key] = {'ts': time.time(), 'ttl': ttl, 'value': value}
    _save_cache(c)


class TMDbError(RuntimeError):
    pass


def _req(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not TMDB_API_KEY:
        raise TMDbError('TMDB_API_KEY not set')
    url = f"{API_BASE}{path}"
    p = {'api_key': TMDB_API_KEY}
    if params:
        p.update(params)
    try:
        r = _session.get(url, params=p, timeout=10)
    except requests.RequestException as e:
        raise TMDbError(f'Network error: {e}')
    if r.status_code != 200:
        try:
            j = r.json()
            msg = j.get('status_message') or j
        except Exception:
            msg = r.text
        raise TMDbError(f'TMDB {r.status_code}: {msg}')
    try:
        return r.json()
    except Exception:
        raise TMDbError('Failed to decode JSON')


def _poster_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"{IMAGE_BASE}/{POSTER_SIZE}{path}"


def search_multi(query: str, kind: str = 'multi', page: int = 1) -> List[Dict[str, Any]]:
    """Search movies/tv or both. kind = 'movie'|'tv'|'multi'"""
    key = f"search:{kind}:{query}:{page}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    results = []
    if kind in ('multi', 'both'):
        data = _req('/search/multi', {'query': query, 'page': page, 'include_adult': False})
        items = data.get('results', [])
        for it in items:
            typ = it.get('media_type')
            if typ not in ('movie', 'tv'):
                continue
            title = it.get('title') if typ == 'movie' else it.get('name')
            results.append({
                'type': typ,
                'id': it.get('id'),
                'title': title,
                'release_date': (it.get('release_date') or it.get('first_air_date')),
                'overview': it.get('overview'),
                'poster': _poster_url(it.get('poster_path')),
                'popularity': it.get('popularity'),
                'tmdb_raw': it,
            })
    else:
        path = '/search/movie' if kind == 'movie' else '/search/tv'
        data = _req(path, {'query': query, 'page': page, 'include_adult': False})
        for it in data.get('results', []):
            title = it.get('title') or it.get('name')
            results.append({
                'type': kind,
                'id': it.get('id'),
                'title': title,
                'release_date': (it.get('release_date') or it.get('first_air_date')),
                'overview': it.get('overview'),
                'poster': _poster_url(it.get('poster_path')),
                'popularity': it.get('popularity'),
                'tmdb_raw': it,
            })
    _cache_set(key, results)
    return results


def get_movie_details(tmdb_id: int) -> Dict[str, Any]:
    key = f'movie:{tmdb_id}'
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = _req(f'/movie/{tmdb_id}', {'append_to_response': 'credits,external_ids'})
    out = {
        'type': 'movie',
        'id': data.get('id'),
        'title': data.get('title'),
        'overview': data.get('overview'),
        'poster': _poster_url(data.get('poster_path')),
        'backdrop': _poster_url(data.get('backdrop_path')),
        'genres': [g.get('name') for g in data.get('genres', [])],
        'runtime': data.get('runtime'),
        'rating': data.get('vote_average'),
        'credits': data.get('credits', {}),
        'imdb_id': data.get('external_ids', {}).get('imdb_id'),
    }
    # try fetch awards via OMDb if possible
    if out.get('imdb_id') and OMDB_API_KEY:
        aw = _get_awards_from_omdb(out['imdb_id'])
        out['awards'] = aw
    _cache_set(key, out)
    return out


def get_tv_details(tmdb_id: int) -> Dict[str, Any]:
    key = f'tv:{tmdb_id}'
    cached = _cache_get(key)
    if cached is not None:
        return cached
    data = _req(f'/tv/{tmdb_id}', {'append_to_response': 'credits,external_ids'})
    out = {
        'type': 'tv',
        'id': data.get('id'),
        'title': data.get('name'),
        'overview': data.get('overview'),
        'poster': _poster_url(data.get('poster_path')),
        'backdrop': _poster_url(data.get('backdrop_path')),
        'genres': [g.get('name') for g in data.get('genres', [])],
        'runtime': None,
        'rating': data.get('vote_average'),
        'credits': data.get('credits', {}),
        'imdb_id': data.get('external_ids', {}).get('imdb_id'),
    }
    if out.get('imdb_id') and OMDB_API_KEY:
        aw = _get_awards_from_omdb(out['imdb_id'])
        out['awards'] = aw
    _cache_set(key, out)
    return out


def get_details(kind: str, tmdb_id: int) -> Dict[str, Any]:
    if kind == 'movie':
        return get_movie_details(tmdb_id)
    if kind == 'tv':
        return get_tv_details(tmdb_id)
    raise TMDbError('kind must be movie or tv')


def _get_awards_from_omdb(imdb_id: str) -> Optional[str]:
    # OMDb returns an 'Awards' field for movies/series; this function is optional and requires OMDB_API_KEY
    if not imdb_id or not OMDB_API_KEY:
        return None
    url = 'http://www.omdbapi.com/'
    try:
        r = requests.get(url, params={'i': imdb_id, 'apikey': OMDB_API_KEY}, timeout=8)
        if r.status_code != 200:
            return None
        j = r.json()
        return j.get('Awards')
    except Exception:
        return None

def get_trending(media_type="all", time_window="week", page=1):
    """
    Get trending items from TMDB.

    media_type: "all", "movie", or "tv"
    time_window: "day" or "week"  (use "week" for weekly trending)
    page: TMDB paging

    Returns: list of items, each with keys:
      - id
      - media_type (movie | tv)
      - title (title or name)
      - release_date (release_date or first_air_date)
      - poster_path (relative path, e.g. /abc.jpg)
      - popularity, vote_average, etc (raw TMDB fields preserved)
    """
    if media_type not in ("all", "movie", "tv"):
        raise ValueError("media_type must be 'all', 'movie' or 'tv'")
    if time_window not in ("day", "week"):
        raise ValueError("time_window must be 'day' or 'week'")

    path = f"/trending/{media_type}/{time_window}"
    data = _req(path, params={"page": page})
    results = data.get("results", [])
    items = []
    for r in results:
        # normalize
        title = r.get("title") or r.get("name")
        release = r.get("release_date") or r.get("first_air_date") or ""
        items.append({
            "id": r.get("id"),
            "media_type": r.get("media_type") or media_type if media_type != "all" else r.get("media_type"),
            "title": title,
            "release_date": release,
            "poster_path": r.get("poster_path"),
            "poster": ("https://image.tmdb.org/t/p/w342" + r["poster_path"]) if r.get("poster_path") else None,
            "popularity": r.get("popularity"),
            "vote_average": r.get("vote_average"),
            "raw": r
        })
    return items

# convenience wrappers
def get_trending_week(media_type="all", page=1):
    return get_trending(media_type=media_type, time_window="week", page=page)

def get_trending_day(media_type="all", page=1):
    return get_trending(media_type=media_type, time_window="day", page=page)