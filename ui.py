"""Streamlit UI for CineBase."""
from typing import Dict, Any, Optional

import requests
import streamlit as st

from firebase_auth import FirebaseAuthClient, FirebaseAuthError
import ai_client
import tmdb_client

PRIMARY = "#E17154"
SECONDARY = "#1EA9A8"
TERTIARY = "#edc979"
BG_LIGHT = "#FFFFFF"
BG_DARK = "#0F1720"
TEXT_DARK = "#0B1220"
TEXT_LIGHT = "#ECEFF1"
PROFILE_BASE = "https://image.tmdb.org/t/p/w185"
SYSTEM_FONT = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"


def inject_css() -> None:
    """Inject base dark theme plus top navigation styling."""
    css = f"""
    <style>
        :root {{
            --primary: {PRIMARY};
            --secondary: {SECONDARY};
            --tertiary: {TERTIARY};
            --bg: {BG_DARK};
            --text: {TEXT_LIGHT};
            --font: {SYSTEM_FONT};
        }}
    .stApp {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
    }}
    body, button, input, textarea, select {{
      font-family: var(--font) !important;
    }}
    .movie-card {{
      padding: 8px;
      border-radius: 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(0,0,0,0.02));
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }}
    .primary-btn {{
      background: var(--primary) !important;
      color: white !important;
    }}
        .top-nav-wrapper {{
            background: #080b11;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            padding: 16px 24px 22px;
            margin-bottom: 24px;
            box-shadow: 0 24px 32px rgba(5, 7, 11, 0.85);
        }}
    .top-brand {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 1.2rem;
    }}
    .brand-mark {{
      width: 34px;
      height: 34px;
      border-radius: 12px;
      background: linear-gradient(135deg, #ffb347, #ffcc33);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      color: #111;
    }}
        .top-search {{
            margin-bottom: 18px;
        }}
        .top-search input {{
            background: #03070d;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 999px;
            padding: 14px 22px;
            color: #f5f7ff;
            font-size: 0.98rem;
        }}
        .nav-slot {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .nav-slot button {{
            border-radius: 999px !important;
            padding: 10px 28px;
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            color: #f6f7ff !important;
            font-size: 0.95rem;
            font-weight: 600;
        }}
        .nav-slot button:hover {{
            border-color: rgba(255,255,255,0.55) !important;
        }}
        .nav-slot.active button {{
            background: rgba(225,113,84,0.2) !important;
            border-color: {PRIMARY} !important;
            box-shadow: 0 10px 20px rgba(225,113,84,0.35);
        }}
    .account-email {{
      font-size: 0.9rem;
      color: rgba(255,255,255,0.75);
      margin-bottom: 6px;
      word-break: break-all;
    }}
    .account-actions .stButton>button {{
      background: transparent;
      border: 1px solid rgba(255,255,255,0.25);
      border-radius: 12px;
      color: var(--text);
      padding: 6px 12px;
    }}
    .account-actions .stButton>button:hover {{
      border-color: {PRIMARY};
      color: {PRIMARY};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def profile_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"{PROFILE_BASE}{path}"


class AppUI:
    """Thin Streamlit UI layer orchestrating navigation and Firebase actions."""

    def __init__(self) -> None:
        self.auth = FirebaseAuthClient()
        if "query" not in st.session_state:
            st.session_state.query = ""
        if "user" not in st.session_state:
            st.session_state.user = None
        if "nav_page" not in st.session_state:
            st.session_state.nav_page = "Home"
        if "selected_media" not in st.session_state:
            st.session_state.selected_media = None
        if st.session_state.get("user") and not self.auth.is_authenticated:
            self.auth.user = st.session_state.user

    # ---------- AUTH helpers ----------
    def sign_in(self, email: str, password: str) -> Optional[str]:
        try:
            res = self.auth.sign_in(email, password)
            st.session_state.user = res
            self.auth.user = res
            st.success("Signed in!")
            return None
        except FirebaseAuthError as exc:
            return str(exc)
        except Exception as exc:
            return f"Sign in error: {exc}"

    def sign_up(self, email: str, password: str) -> Optional[str]:
        try:
            res = self.auth.sign_up(email, password)
            st.session_state.user = res
            self.auth.user = res
            st.success("Account created and signed in!")
            return None
        except FirebaseAuthError as exc:
            return str(exc)
        except Exception as exc:
            return f"Sign up error: {exc}"

    def sign_out(self) -> None:
        self.auth.sign_out()
        st.session_state.user = None
        st.session_state.selected_media = None
        st.success("Signed out")

    # ---------- Watchlist helpers ----------
    def add_to_watchlist(self, imdb_or_id: str, movie_data: Dict[str, Any]) -> None:
        if not self.auth.is_authenticated:
            st.error("Please sign in to manage your watchlist.")
            return
        try:
            self.auth.add_to_watchlist(imdb_or_id, movie_data)
            st.success("Added to watchlist")
        except Exception as exc:
            st.error(f"Failed to add to watchlist: {exc}")

    def remove_from_watchlist(self, imdb_or_id: str) -> None:
        if not self.auth.id_token or not self.auth.user_id:
            st.error("Not authenticated")
            return
        url = f"{self.auth.db_url}/users/{self.auth.user_id}/watchlist/{imdb_or_id}.json?auth={self.auth.id_token}"
        resp = requests.delete(url)
        if resp.status_code in (200, 204):
            st.success("Removed from watchlist")
        else:
            st.error("Failed to remove from watchlist")

    def get_watchlist(self) -> Dict[str, Any]:
        try:
            return self.auth.get_watchlist()
        except Exception:
            st.warning("Could not fetch watchlist (not signed in?)")
            return {}

    # ---------- Account helpers ----------
    def update_email_or_password(
        self,
        id_token: str,
        email: Optional[str],
        password: Optional[str],
    ) -> Optional[str]:
        try:
            payload = {"idToken": id_token, "returnSecureToken": True}
            if email:
                payload["email"] = email
            if password:
                payload["password"] = password
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.auth.api_key}"
            resp = requests.post(url, json=payload)
            data = resp.json()
            if resp.status_code != 200:
                return data.get("error", {}).get("message", "Failed to update account")
            st.session_state.user.update(data)
            return None
        except Exception as exc:
            return str(exc)

    def clear_watchlist_db(self) -> None:
        if not self.auth.id_token or not self.auth.user_id:
            st.error("Not signed in")
            return
        url = f"{self.auth.db_url}/users/{self.auth.user_id}/watchlist.json?auth={self.auth.id_token}"
        resp = requests.delete(url)
        if resp.status_code in (200, 204):
            st.success("Cleared watchlist")
        else:
            st.error("Failed to clear watchlist")

    # ---------- UI helpers ----------
    def render_navbar(self) -> None:
        email = self.auth.get_user_email() or "Unknown"
        nav_items = ["Home", "Watchlist", "Settings / Account"]
        with st.container():
            st.markdown("<div class='top-nav-wrapper'>", unsafe_allow_html=True)
            brand_col, nav_col, account_col = st.columns([1.5, 2.4, 1.3])
            with brand_col:
                st.markdown(
                    "<div class='top-brand'><div class='brand-mark'>CB</div><div>CineBase</div></div>",
                    unsafe_allow_html=True,
                )
                st.caption("Merge movies, shows & watchlists in one place.")
            with nav_col:
                icon_cols = st.columns(len(nav_items))
                for idx, page in enumerate(nav_items):
                    with icon_cols[idx]:
                        active = st.session_state.nav_page == page
                        slot_class = "nav-slot active" if active else "nav-slot"
                        st.markdown(f"<div class='{slot_class}'>", unsafe_allow_html=True)
                        key_name = page.lower().replace(" ", "_")
                        if st.button(page, key=f"nav_{key_name}"):
                            st.session_state.nav_page = page
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            with account_col:
                st.markdown(f"<div class='account-email'>{email}</div>", unsafe_allow_html=True)
                st.caption("Logged in")
                st.markdown("<div class='account-actions'>", unsafe_allow_html=True)
                if st.button("Log out", key="top_sign_out", use_container_width=True):
                    self.sign_out()
                    st.session_state.nav_page = "Home"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='top-search'>", unsafe_allow_html=True)
        query = st.text_input(
            "Search across CineBase",
            value=st.session_state.get("query", ""),
            key="global_search_input",
            label_visibility="collapsed",
        )
        st.session_state.query = query
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ---------- Selection helpers ----------
    def select_media(self, media_type: Optional[str], tmdb_id: Optional[int]) -> None:
        if not tmdb_id:
            return
        kind = media_type or "movie"
        st.session_state.selected_media = {"type": kind, "id": tmdb_id}

    def clear_selected_media(self) -> None:
        st.session_state.selected_media = None

    def render_detail_view(self) -> None:
        selected = st.session_state.get("selected_media")
        if not selected:
            return
        try:
            detail = tmdb_client.get_details(selected["type"], selected["id"])
        except Exception as exc:
            st.error(f"Could not load details: {exc}")
            self.clear_selected_media()
            return

        title = detail.get("title") or "Untitled"
        release = detail.get("release_date") or ""
        genres = ", ".join(detail.get("genres", []))
        runtime = detail.get("runtime")
        rating = detail.get("rating") or "—"
        imdb_id = detail.get("imdb_id") or str(detail.get("id"))

        st.caption(f"Home / {selected['type'].title()} / {title}")

        hero = st.container()
        with hero:
            col_poster, col_info = st.columns([1, 2])
            with col_poster:
                if detail.get("poster"):
                    st.image(detail["poster"], width=320)
                if st.button("← Back to picks", key="detail_back", use_container_width=True):
                    self.clear_selected_media()
                    st.rerun()
            with col_info:
                st.markdown(f"## {title}")
                runtime_meta = f"{runtime} min" if isinstance(runtime, (int, float)) else None
                meta_bits = [release, runtime_meta, genres]
                meta = " • ".join(bit for bit in meta_bits if bit)
                if meta:
                    st.markdown(f"*{meta}*")
                st.markdown("#### Synopsis")
                st.write(detail.get("overview") or "No overview available.")

                action_cols = st.columns(3)
                with action_cols[0]:
                    if st.button("➕ Add to Watchlist", key=f"detail_watch_{detail['id']}", use_container_width=True):
                        movie_data = {
                            "title": title,
                            "poster": detail.get("poster"),
                            "type": selected["type"],
                        }
                        self.add_to_watchlist(str(imdb_id), movie_data)
                with action_cols[1]:
                    st.button(
                        "⭐ Add to Favorites",
                        key=f"detail_fav_{detail['id']}",
                        use_container_width=True,
                        disabled=True,
                    )
                with action_cols[2]:
                    if st.button("✖ Close", key="detail_close", use_container_width=True):
                        self.clear_selected_media()
                        st.rerun()

        st.markdown("---")
        info_cols = st.columns([2, 1])
        with info_cols[0]:
            st.markdown("#### Details")
            director = next((c for c in detail.get("credits", {}).get("crew", []) if c.get("job") == "Director"), None)
            if director:
                st.markdown(f"**Director:** {director.get('name')}" )
            if genres:
                st.markdown(f"**Genres:** {genres}")
            st.markdown(f"**Runtime:** {f'{runtime} min' if isinstance(runtime, (int, float)) else '—'}")
            st.markdown(f"**User score:** {rating}")

            st.markdown("#### Cast & Crew")
            cast = detail.get("credits", {}).get("cast", [])[:5]
            if not cast:
                st.write("Cast data unavailable")
            else:
                cast_cols = st.columns(len(cast))
                for idx, actor in enumerate(cast):
                    with cast_cols[idx]:
                        img = profile_url(actor.get("profile_path"))
                        if img:
                            st.image(img, width=90)
                        st.markdown(f"**{actor.get('name')}**")
                        st.caption(actor.get("character", ""))

        with info_cols[1]:
            st.markdown("#### Ratings")
            st.metric("TMDB", f"{rating}")
            st.caption("Additional ratings from OMDb/Rotten Tomatoes appear when available.")

            st.markdown("#### AI Insights")
            cached_ai = st.session_state.setdefault("detail_ai_cache", {})
            detail_id = detail.get("id")
            if cached_ai.get(detail_id):
                st.info(cached_ai[detail_id])
            if st.button("✨ Generate", key=f"detail_ai_{detail_id}", use_container_width=True):
                try:
                    insight = ai_client.get_movie_insights(title, detail.get("overview") or "")
                    cached_ai[detail_id] = insight
                    st.info(insight)
                except Exception as exc:
                    st.error(f"AI error: {exc}")

    def sign_in_page(self) -> None:
        st.title("🎬 CineBase")
        st.caption("Sign in to explore trending picks, sync your watchlist, and get quick AI insights.")
        col1, col2 = st.columns([3, 2])

        with col1:
            tab1, tab2 = st.tabs(["Sign In", "Create Account"])
            with tab1:
                with st.form("signin_form"):
                    email = st.text_input("Email", key="signin_email")
                    pwd = st.text_input("Password", type="password", key="signin_pwd")
                    submitted = st.form_submit_button("Sign In", use_container_width=True)
                    if submitted:
                        err = self.sign_in(email.strip(), pwd)
                        if err:
                            st.error(err)
                        else:
                            st.session_state.nav_page = "Home"
                            st.rerun()
            with tab2:
                with st.form("signup_form"):
                    email = st.text_input("Email", key="signup_email")
                    pwd = st.text_input("Password", type="password", key="signup_pwd")
                    submitted = st.form_submit_button("Create Account", use_container_width=True)
                    if submitted:
                        err = self.sign_up(email.strip(), pwd)
                        if err:
                            st.error(err)
                        else:
                            st.session_state.nav_page = "Home"
                            st.rerun()

        with col2:
            st.markdown("#### Why sign in?")
            st.markdown("- Save and sync a watchlist\n- Keep AI insights history\n- Unlock personalized settings")
            st.markdown("#### Need help?")
            st.caption("Configure TMDB + Firebase keys locally before authenticating.")

        st.divider()
        st.caption("Need an API key? Configure TMDB/Firebase/.env before signing in.")

    def home_page(self) -> None:
        if st.session_state.get("selected_media"):
            self.render_detail_view()

        st.subheader("Trending this week")
        try:
            trending = tmdb_client.get_trending_week(media_type="all", page=1)
        except Exception as exc:
            st.error(f"Could not fetch trending: {exc}")
            trending = []

        cols = st.columns(4)
        for i, item in enumerate(trending[:12]):
            c_col = cols[i % 4]
            with c_col:
                st.image(item.get("poster") or "", width=260)
                st.markdown(f"**{item.get('title')}**")
                st.caption(f"{item.get('media_type')} • {item.get('release_date')}")
                if st.button("View details", key=f"detail_trending_{item['id']}"):
                    self.select_media(item.get("media_type"), item.get("id"))
                    st.rerun()
        st.divider()

        query = st.session_state.query.strip()
        if query:
            st.subheader(f"Results for '{query}'")
            try:
                results = tmdb_client.search_multi(query, kind="multi", page=1)
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                results = []

            if not results:
                st.info("No results found")
            else:
                cols = st.columns(4)
                for i, res in enumerate(results):
                    c_col = cols[i % 4]
                    with c_col:
                        st.markdown("<div class='movie-card'>", unsafe_allow_html=True)
                        if res.get("poster"):
                            st.image(res.get("poster"), width=260)
                        st.markdown(f"**{res.get('title')}**")
                        st.caption(f"{res.get('type')} • {res.get('release_date') or ''}")
                        if st.button("View details", key=f"detail_search_{res.get('id')}"):
                            self.select_media(res.get("type"), res.get("id"))
                            st.rerun()
                        if st.button("Add to Watchlist", key=f"add_{res.get('id')}"):
                            key = str(res.get("id"))
                            movie_data = {
                                "title": res.get("title"),
                                "poster": res.get("poster"),
                                "type": res.get("type"),
                            }
                            self.add_to_watchlist(key, movie_data)
                        st.markdown("</div>", unsafe_allow_html=True)

    def watchlist_page(self) -> None:
        st.subheader("Your Watchlist")
        if not self.auth.is_authenticated:
            st.info("Sign in to view your synced watchlist.")
            return
        watchlist = self.get_watchlist()
        if not watchlist:
            st.info("Your watchlist is empty.")
            return
        items = list(watchlist.items())
        cols = st.columns(4)
        for i, (key, value) in enumerate(items):
            c_col = cols[i % 4]
            with c_col:
                st.markdown("<div class='movie-card'>", unsafe_allow_html=True)
                if value.get("poster"):
                    st.image(value.get("poster"), width=260)
                st.markdown(f"**{value.get('title')}**")
                done_key = f"done_{key}"
                finished = st.checkbox("Finished / remove", key=done_key)
                if finished:
                    self.remove_from_watchlist(key)
                st.markdown("</div>", unsafe_allow_html=True)

    def settings_page(self) -> None:
        st.subheader("Settings & Account")
        if not st.session_state.user:
            st.info("Sign in to view account details.")
            return
        profile = st.session_state.user
        st.markdown("#### Profile")
        with st.form("profile_form"):
            name = st.text_input("Display name", value=profile.get("displayName") or "")
            email = st.text_input("Email", value=profile.get("email") or "")
            submitted = st.form_submit_button("Update profile")
            if submitted:
                id_token = self.auth.id_token
                err = self.update_email_or_password(id_token, email=email, password=None)
                if err:
                    st.error(f"Failed to update email: {err}")
                else:
                    url = f"{self.auth.db_url}/users/{self.auth.user_id}/profile.json?auth={self.auth.id_token}"
                    requests.patch(url, json={"name": name})
                    st.success("Profile updated")

        st.markdown("#### Security")
        with st.form("security_form"):
            new_email = st.text_input("Change email", key="change_email")
            new_pwd = st.text_input("New password", type="password", key="change_pwd")
            sec_submit = st.form_submit_button("Apply changes")
            if sec_submit:
                id_token = self.auth.id_token
                err = self.update_email_or_password(id_token, email=new_email or None, password=new_pwd or None)
                if err:
                    st.error(err)
                else:
                    st.success("Account updated (email/password)")

        st.markdown("#### Settings")
        with st.expander("Preferences"):
            if st.button("Clear watchlist"):
                self.clear_watchlist_db()

        st.markdown("#### AI insights (optional)")
        st.caption("Get a quick AI summary & trivia for a movie (Perplexity API must be configured).")
        movie_title = st.text_input("Title for AI insights", key="ai_title")
        movie_plot = st.text_area("Plot (or leave blank to fetch basic plot via TMDB)", key="ai_plot")
        if st.button("Get AI insights"):
            if not movie_plot and movie_title:
                try:
                    res = tmdb_client.search_multi(movie_title, kind="movie", page=1)
                    if res:
                        mid = res[0].get("id")
                        details = tmdb_client.get_movie_details(mid)
                        movie_plot = details.get("overview") or ""
                except Exception:
                    movie_plot = ""
            if not movie_title or not movie_plot:
                st.error("Need a title and/or plot to run AI insights.")
            else:
                try:
                    txt = ai_client.get_movie_insights(movie_title, movie_plot)
                    st.text(txt)
                except Exception as exc:
                    st.error(f"AI error: {exc}")

    # ---------- Entry point ----------
    def run(self) -> None:
        inject_css()

        if not st.session_state.user:
            self.sign_in_page()
            return

        self.render_navbar()
        pages = ["Home", "Watchlist", "Settings / Account"]
        choice = st.session_state.get("nav_page", "Home")
        if choice not in pages:
            choice = "Home"
            st.session_state.nav_page = choice

        if choice == "Home":
            self.home_page()
        elif choice == "Watchlist":
            self.watchlist_page()
        else:
            self.settings_page()

        st.markdown("---")
        st.caption(
            "Palette: Primary: {p} • Secondary: {s} • Tertiary: {t}".format(
                p=PRIMARY,
                s=SECONDARY,
                t=TERTIARY,
            )
        )

