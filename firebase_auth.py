# firebase_auth.py
import requests
from typing import Optional, Dict, Any

from config import FIREBASE_API_KEY, FIREBASE_DB_URL


class FirebaseAuthError(Exception):
    pass


class FirebaseAuthClient:
    def __init__(self, api_key: str = FIREBASE_API_KEY, db_url: str = FIREBASE_DB_URL):
        self.api_key = api_key
        self.db_url = db_url.rstrip("/")
        self.user = None  # holds current signed-in user info

    def get_user_email(self) -> Optional[str]:
        """Return the signed-in user's email or None if not signed in."""
        return self.user.get("email") if self.user else None


    # ---------- AUTH ----------

    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        resp = requests.post(url, json=payload)
        data = resp.json()
        if resp.status_code != 200:
            raise FirebaseAuthError(data.get("error", {}).get("message", "Sign up failed"))
        self.user = data
        # Initialize basic profile in DB
        self._init_user_profile()
        return data

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        resp = requests.post(url, json=payload)
        data = resp.json()
        if resp.status_code != 200:
            raise FirebaseAuthError(data.get("error", {}).get("message", "Sign in failed"))
        self.user = data
        return data

    def sign_out(self):
        self.user = None

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None

    @property
    def id_token(self) -> Optional[str]:
        return self.user.get("idToken") if self.user else None

    @property
    def user_id(self) -> Optional[str]:
        return self.user.get("localId") if self.user else None

    # ---------- DB HELPERS ----------

    def _user_path(self, path: str) -> str:
        if not self.user_id:
            raise FirebaseAuthError("No authenticated user")
        return f"{self.db_url}/users/{self.user_id}/{path}.json"

    def _init_user_profile(self):
        if not self.id_token or not self.user_id:
            return
        url = self._user_path("")
        payload = {
            "email": self.user.get("email"),
            "watchlist": {},
        }
        requests.patch(url + f"?auth={self.id_token}", json=payload)

    # ---------- WATCHLIST API ----------

    def add_to_watchlist(self, imdb_id: str, movie_data: Dict[str, Any]):
        """
        movie_data: a small dict you store under /users/{uid}/watchlist/{imdb_id}
        """
        if not self.id_token:
            raise FirebaseAuthError("User not authenticated")
        url = self._user_path(f"watchlist/{imdb_id}") + f"?auth={self.id_token}"
        resp = requests.put(url, json=movie_data)
        if resp.status_code not in (200, 204):
            raise FirebaseAuthError("Failed to save to watchlist")

    def get_watchlist(self) -> Dict[str, Any]:
        if not self.id_token:
            raise FirebaseAuthError("User not authenticated")
        url = self._user_path("watchlist") + f"?auth={self.id_token}"
        resp = requests.get(url)
        if resp.status_code != 200:
            raise FirebaseAuthError("Failed to fetch watchlist")
        data = resp.json()
        return data or {}
