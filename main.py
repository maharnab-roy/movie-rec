import os
import pickle
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# =========================
# ENV
# =========================
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_500 = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORIGINAL = "https://image.tmdb.org/t/p/original"

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY missing. Put it in .env as TMDB_API_KEY=your_key_here")


# =========================
# FASTAPI APP
# =========================
app = FastAPI(title="MovieMind API", version="7.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# LOCAL FILES
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DF_PATH = os.path.join(BASE_DIR, "df.pkl")
INDICES_PATH = os.path.join(BASE_DIR, "indices.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_matrix.pkl")
TFIDF_PATH = os.path.join(BASE_DIR, "tfidf.pkl")

df: Optional[pd.DataFrame] = None
indices_obj: Any = None
tfidf_matrix: Any = None
tfidf_obj: Any = None
TITLE_TO_IDX: Optional[Dict[str, int]] = None


# =========================
# MODELS
# =========================
class TMDBMovieCard(BaseModel):
    tmdb_id: int
    title: str
    poster_url: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    adult: bool = False


class TMDBMovieDetails(BaseModel):
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    release_date: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    genres: List[dict] = Field(default_factory=list)
    adult: bool = False


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    tmdb: Optional[TMDBMovieCard] = None


class SearchBundleResponse(BaseModel):
    query: str
    movie_details: TMDBMovieDetails
    tfidf_recommendations: List[TFIDFRecItem]
    genre_recommendations: List[TMDBMovieCard]


# =========================
# TMDB HELPERS
# =========================
def make_img_url(path: Optional[str], original: bool = False) -> Optional[str]:
    if not path:
        return None

    base = TMDB_IMG_ORIGINAL if original else TMDB_IMG_500
    return f"{base}{path}"


def clean_query_text(query: str) -> str:
    return str(query or "").strip().replace("\\", "").replace("/", " ")


async def tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Safe TMDB request helper.
    Retries request and gives real error instead of random unknown 502.
    """

    query_params = dict(params or {})
    query_params["api_key"] = TMDB_API_KEY

    headers = {
        "accept": "application/json",
        "User-Agent": "MovieMind/7.0",
    }

    last_error = None

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0),
                headers=headers,
                follow_redirects=True,
                trust_env=False,
            ) as client:
                response = await client.get(f"{TMDB_BASE}{path}", params=query_params)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"TMDB movie/resource not found: {path}",
                )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid TMDB API key. Check your .env file.",
                )

            last_error = {
                "message": "TMDB request failed",
                "tmdb_status": response.status_code,
                "tmdb_response": response.text,
                "url": str(response.url),
            }

        except HTTPException:
            raise

        except httpx.TimeoutException:
            last_error = "TMDB timeout. Check internet connection or try again."

        except httpx.ConnectError:
            last_error = "Cannot connect to TMDB. Check your internet connection."

        except httpx.RequestError as e:
            last_error = f"TMDB request error: {type(e).__name__}: {str(e)}"

        if attempt < 2:
            await asyncio.sleep(0.6)

    raise HTTPException(status_code=502, detail=last_error or "TMDB request failed")


async def safe_tmdb_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        return await tmdb_get(path, params)
    except Exception:
        return {}


async def tmdb_cards_from_results(results: List[dict], limit: int = 20) -> List[TMDBMovieCard]:
    cards: List[TMDBMovieCard] = []

    for movie in results or []:
        if len(cards) >= limit:
            break

        movie_id = movie.get("id")
        title = movie.get("title") or movie.get("name") or movie.get("original_title") or ""

        if not movie_id or not title:
            continue

        cards.append(
            TMDBMovieCard(
                tmdb_id=int(movie_id),
                title=title,
                poster_url=make_img_url(movie.get("poster_path")),
                release_date=movie.get("release_date") or "",
                vote_average=movie.get("vote_average") or 0,
                adult=bool(movie.get("adult", False)),
            )
        )

    return cards


async def tmdb_search_movies(
    query: str,
    page: int = 1,
    include_adult: bool = False,
) -> Dict[str, Any]:
    query = clean_query_text(query)

    if not query:
        return {
            "page": 1,
            "results": [],
            "total_pages": 0,
            "total_results": 0,
        }

    return await tmdb_get(
        "/search/movie",
        {
            "query": query,
            "include_adult": str(include_adult).lower(),
            "language": "en-US",
            "page": page,
        },
    )


async def tmdb_search_first(query: str) -> Optional[dict]:
    data = await tmdb_search_movies(query=query, page=1, include_adult=False)
    results = data.get("results", [])
    return results[0] if results else None


async def tmdb_movie_details_basic(movie_id: int) -> TMDBMovieDetails:
    data = await tmdb_get(f"/movie/{movie_id}", {"language": "en-US"})

    return TMDBMovieDetails(
        tmdb_id=int(data.get("id")),
        title=data.get("title") or data.get("original_title") or "Unknown Title",
        overview=data.get("overview") or "No overview available.",
        release_date=data.get("release_date") or "",
        poster_url=make_img_url(data.get("poster_path")),
        backdrop_url=make_img_url(data.get("backdrop_path"), original=True),
        genres=data.get("genres", []) or [],
        adult=bool(data.get("adult", False)),
    )


async def tmdb_movie_full(movie_id: int) -> Dict[str, Any]:
    data = await safe_tmdb_get(
        f"/movie/{movie_id}",
        {
            "language": "en-US",
            "append_to_response": "credits,videos,recommendations,similar",
        },
    )

    if data:
        return data

    data = await safe_tmdb_get(
        f"/movie/{movie_id}",
        {
            "language": "en-US",
        },
    )

    return data


def format_movie_details(data: Dict[str, Any]) -> Dict[str, Any]:
    credits = data.get("credits") or {}
    videos = data.get("videos") or {}
    similar = data.get("similar") or {}
    recommendations = data.get("recommendations") or {}

    cast = credits.get("cast") or []
    crew = credits.get("crew") or []

    director = None
    for person in crew:
        if person.get("job") == "Director":
            director = person.get("name")
            break

    trailer = None
    for video in videos.get("results", []):
        if video.get("site") == "YouTube" and video.get("type") in ["Trailer", "Teaser"]:
            trailer = f"https://www.youtube.com/watch?v={video.get('key')}"
            break

    poster_path = data.get("poster_path")
    backdrop_path = data.get("backdrop_path")
    release_date = data.get("release_date") or ""

    return {
        "id": data.get("id"),
        "tmdb_id": data.get("id"),
        "title": data.get("title") or data.get("original_title") or "Unknown Title",
        "overview": data.get("overview") or "No overview available.",
        "release_date": release_date,
        "year": release_date[:4],
        "runtime": data.get("runtime") or 0,
        "rating": data.get("vote_average") or 0,
        "vote_average": data.get("vote_average") or 0,
        "vote_count": data.get("vote_count") or 0,
        "popularity": data.get("popularity") or 0,
        "adult": bool(data.get("adult", False)),

        "genres": data.get("genres") or [],
        "genre_ids": [g.get("id") for g in data.get("genres", []) if g.get("id")],

        "poster_path": poster_path,
        "poster_url": make_img_url(poster_path),

        "backdrop_path": backdrop_path,
        "backdrop_url": make_img_url(backdrop_path, original=True),

        "tagline": data.get("tagline") or "",
        "status": data.get("status") or "",
        "budget": data.get("budget") or 0,
        "revenue": data.get("revenue") or 0,

        "director": director,

        "cast": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "character": c.get("character"),
                "profile_path": c.get("profile_path"),
                "profile_url": make_img_url(c.get("profile_path")),
            }
            for c in cast[:12]
        ],

        "trailer": trailer,

        "similar": similar.get("results", [])[:12],
        "recommendations": recommendations.get("results", [])[:12],
    }


# =========================
# TF-IDF HELPERS
# =========================
def _norm_title(title: str) -> str:
    return str(title).strip().lower()


def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
    title_to_idx: Dict[str, int] = {}

    if isinstance(indices, dict):
        for key, value in indices.items():
            title_to_idx[_norm_title(key)] = int(value)
        return title_to_idx

    try:
        for key, value in indices.items():
            title_to_idx[_norm_title(key)] = int(value)
        return title_to_idx
    except Exception:
        raise RuntimeError("indices.pkl must be dict or pandas Series-like")


def get_local_idx_by_title(title: str) -> int:
    if TITLE_TO_IDX is None:
        raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")

    key = _norm_title(title)

    if key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[key])

    raise HTTPException(status_code=404, detail=f"Title not found in local dataset: '{title}'")


def tfidf_recommend_titles(query_title: str, top_n: int = 10) -> List[Tuple[str, float]]:
    if df is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

    idx = get_local_idx_by_title(query_title)

    qv = tfidf_matrix[idx]
    scores = (tfidf_matrix @ qv.T).toarray().ravel()
    order = np.argsort(-scores)

    output: List[Tuple[str, float]] = []

    for i in order:
        if int(i) == int(idx):
            continue

        try:
            title_i = str(df.iloc[int(i)]["title"])
        except Exception:
            continue

        output.append((title_i, float(scores[int(i)])))

        if len(output) >= top_n:
            break

    return output


async def attach_tmdb_card_by_title(title: str) -> Optional[TMDBMovieCard]:
    try:
        movie = await tmdb_search_first(title)

        if not movie:
            return None

        return TMDBMovieCard(
            tmdb_id=int(movie["id"]),
            title=movie.get("title") or title,
            poster_url=make_img_url(movie.get("poster_path")),
            release_date=movie.get("release_date") or "",
            vote_average=movie.get("vote_average") or 0,
            adult=bool(movie.get("adult", False)),
        )
    except Exception:
        return None


# =========================
# RECOMMENDATION HELPERS
# =========================
def clean_title_keyword(title: str) -> str:
    text = str(title or "").lower()
    text = text.replace(":", " ")
    text = text.replace("-", " ")
    text = text.replace(".", " ")

    remove_words = {
        "part", "chapter", "episode", "vol", "volume",
        "one", "two", "three", "four", "five", "six",
        "i", "ii", "iii", "iv", "v", "vi",
        "1", "2", "3", "4", "5", "6",
        "the", "a", "an",
    }

    words = [word.strip() for word in text.split() if word.strip()]
    final_words = [word for word in words if word not in remove_words]

    if not final_words:
        final_words = words

    return " ".join(final_words[:2]).strip()


def remove_duplicate_cards(cards: List[TMDBMovieCard], selected_id: int) -> List[TMDBMovieCard]:
    seen = set()
    final_cards: List[TMDBMovieCard] = []

    for card in cards:
        if int(card.tmdb_id) == int(selected_id):
            continue

        if card.tmdb_id in seen:
            continue

        seen.add(card.tmdb_id)
        final_cards.append(card)

    return final_cards


async def cards_from_raw_filtered(
    results: List[dict],
    selected_id: int,
    selected_adult: bool,
    limit: int = 20,
) -> List[TMDBMovieCard]:
    cards: List[TMDBMovieCard] = []

    for movie in results or []:
        if len(cards) >= limit:
            break

        movie_id = movie.get("id")
        title = movie.get("title") or movie.get("name") or movie.get("original_title") or ""

        if not movie_id or not title:
            continue

        if int(movie_id) == int(selected_id):
            continue

        movie_adult = bool(movie.get("adult", False))

        if movie_adult != selected_adult:
            continue

        cards.append(
            TMDBMovieCard(
                tmdb_id=int(movie_id),
                title=title,
                poster_url=make_img_url(movie.get("poster_path")),
                release_date=movie.get("release_date") or "",
                vote_average=movie.get("vote_average") or 0,
                adult=movie_adult,
            )
        )

    return cards


# =========================
# STARTUP
# =========================
@app.on_event("startup")
def load_pickles():
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

    try:
        if os.path.exists(DF_PATH):
            with open(DF_PATH, "rb") as file:
                df = pickle.load(file)

        if os.path.exists(INDICES_PATH):
            with open(INDICES_PATH, "rb") as file:
                indices_obj = pickle.load(file)

        if os.path.exists(TFIDF_MATRIX_PATH):
            with open(TFIDF_MATRIX_PATH, "rb") as file:
                tfidf_matrix = pickle.load(file)

        if os.path.exists(TFIDF_PATH):
            with open(TFIDF_PATH, "rb") as file:
                tfidf_obj = pickle.load(file)

        if indices_obj is not None:
            TITLE_TO_IDX = build_title_to_idx_map(indices_obj)

        print("MovieMind startup complete.")

    except Exception as e:
        print(f"Pickle loading skipped because of error: {e}")


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "MovieMind API running",
        "version": "7.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/genres")
async def get_genres():
    data = await tmdb_get("/genre/movie/list", {"language": "en-US"})
    return data.get("genres", [])


@app.get("/home", response_model=List[TMDBMovieCard])
async def home(
    category: str = Query("popular"),
    limit: int = Query(24, ge=1, le=50),
):
    if category == "trending":
        data = await tmdb_get("/trending/movie/day", {"language": "en-US"})
        return await tmdb_cards_from_results(data.get("results", []), limit=limit)

    if category not in {"popular", "top_rated", "upcoming", "now_playing"}:
        raise HTTPException(status_code=400, detail="Invalid category")

    data = await tmdb_get(
        f"/movie/{category}",
        {
            "language": "en-US",
            "page": 1,
        },
    )

    return await tmdb_cards_from_results(data.get("results", []), limit=limit)


@app.get("/home/by-genres", response_model=List[TMDBMovieCard])
async def home_by_genres(
    genre_ids: str = Query(...),
    limit: int = Query(24, ge=1, le=50),
    page: int = Query(1, ge=1, le=10),
    include_adult: bool = Query(False),
    kids: bool = Query(False),
):
    params = {
        "with_genres": genre_ids,
        "include_adult": str(include_adult).lower(),
        "language": "en-US",
        "sort_by": "popularity.desc",
        "page": page,
        "vote_count.gte": 100,
    }

    if kids:
        params["include_adult"] = "false"
        params["certification_country"] = "US"
        params["certification.lte"] = "PG"

    data = await tmdb_get("/discover/movie", params)
    return await tmdb_cards_from_results(data.get("results", []), limit=limit)


@app.get("/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1, le=10),
    include_adult: bool = Query(False),
):
    query = clean_query_text(query)

    data = await tmdb_search_movies(
        query=query,
        page=page,
        include_adult=include_adult,
    )

    results = data.get("results", []) or []

    clean_results = []

    for movie in results:
        poster_path = movie.get("poster_path")
        backdrop_path = movie.get("backdrop_path")
        release_date = movie.get("release_date") or ""

        clean_results.append(
            {
                "id": movie.get("id"),
                "tmdb_id": movie.get("id"),
                "title": movie.get("title") or movie.get("original_title") or "Unknown Title",
                "overview": movie.get("overview") or "No overview available.",
                "release_date": release_date,
                "year": release_date[:4],
                "rating": movie.get("vote_average") or 0,
                "vote_average": movie.get("vote_average") or 0,
                "vote_count": movie.get("vote_count") or 0,
                "popularity": movie.get("popularity") or 0,
                "adult": bool(movie.get("adult", False)),
                "genre_ids": movie.get("genre_ids") or [],

                "poster_path": poster_path,
                "poster_url": make_img_url(poster_path),

                "backdrop_path": backdrop_path,
                "backdrop_url": make_img_url(backdrop_path, original=True),
            }
        )

    return {
        "page": data.get("page", page),
        "query": query,
        "results": clean_results,
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", len(clean_results)),
    }


@app.get("/movie/id/{tmdb_id}")
async def movie_details_route(
    tmdb_id: int,
    include_adult: bool = Query(False),
    kids: bool = Query(False),
):
    data = await tmdb_movie_full(tmdb_id)

    if not data:
        raise HTTPException(status_code=404, detail=f"Movie not found: {tmdb_id}")

    if not include_adult and bool(data.get("adult", False)):
        raise HTTPException(status_code=404, detail="Adult movie hidden")

    genres = data.get("genres") or []
    genre_ids = [genre.get("id") for genre in genres if genre.get("id")]

    if kids:
        blocked_genres = {27, 80, 53, 10752}
        if any(genre_id in blocked_genres for genre_id in genre_ids):
            raise HTTPException(status_code=404, detail="Movie hidden for kids profile")

    return format_movie_details(data)


@app.get("/movie/recommendations")
async def movie_recommendations(
    tmdb_id: int = Query(...),
    limit: int = Query(18, ge=1, le=40),
    include_adult: bool = Query(False),
    kids: bool = Query(False),
):
    movie = await tmdb_movie_full(tmdb_id)

    if not movie:
        return {
            "tmdb_id": tmdb_id,
            "title": "",
            "adult": False,
            "similar_movies": [],
            "more_like_this": [],
        }

    selected_adult = bool(movie.get("adult", False))

    if kids:
        selected_adult = False

    if not include_adult:
        selected_adult = False

    selected_title = movie.get("title") or ""
    genres = movie.get("genres", []) or []

    similar_movies: List[TMDBMovieCard] = []
    more_like_this: List[TMDBMovieCard] = []

    collection = movie.get("belongs_to_collection")

    if collection and collection.get("id"):
        collection_data = await safe_tmdb_get(
            f"/collection/{collection['id']}",
            {"language": "en-US"},
        )

        if collection_data:
            collection_cards = await cards_from_raw_filtered(
                collection_data.get("parts", []),
                selected_id=tmdb_id,
                selected_adult=selected_adult,
                limit=limit,
            )

            similar_movies.extend(collection_cards)

    keyword = clean_title_keyword(selected_title)

    if keyword:
        search_data = await safe_tmdb_get(
            "/search/movie",
            {
                "query": keyword,
                "include_adult": str(selected_adult).lower(),
                "language": "en-US",
                "page": 1,
            },
        )

        if search_data:
            search_cards = await cards_from_raw_filtered(
                search_data.get("results", []),
                selected_id=tmdb_id,
                selected_adult=selected_adult,
                limit=limit,
            )

            similar_movies.extend(search_cards)

    rec_results = movie.get("recommendations", {}).get("results", [])

    rec_cards = await cards_from_raw_filtered(
        rec_results,
        selected_id=tmdb_id,
        selected_adult=selected_adult,
        limit=limit,
    )

    similar_movies.extend(rec_cards)
    similar_movies = remove_duplicate_cards(similar_movies, tmdb_id)[:limit]

    sim_results = movie.get("similar", {}).get("results", [])

    sim_cards = await cards_from_raw_filtered(
        sim_results,
        selected_id=tmdb_id,
        selected_adult=selected_adult,
        limit=limit,
    )

    more_like_this.extend(sim_cards)

    if genres:
        genre_ids_string = ",".join([str(genre["id"]) for genre in genres[:2] if genre.get("id")])

        params = {
            "with_genres": genre_ids_string,
            "include_adult": str(selected_adult).lower(),
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
            "vote_count.gte": 100,
        }

        if kids:
            params["include_adult"] = "false"
            params["certification_country"] = "US"
            params["certification.lte"] = "PG"

        discover_data = await safe_tmdb_get("/discover/movie", params)

        if discover_data:
            genre_cards = await cards_from_raw_filtered(
                discover_data.get("results", []),
                selected_id=tmdb_id,
                selected_adult=selected_adult,
                limit=limit,
            )

            more_like_this.extend(genre_cards)

    more_like_this = remove_duplicate_cards(more_like_this, tmdb_id)[:limit]

    return {
        "tmdb_id": tmdb_id,
        "title": selected_title,
        "adult": selected_adult,
        "similar_movies": similar_movies,
        "more_like_this": more_like_this,
    }


@app.get("/recommend/genre", response_model=List[TMDBMovieCard])
async def recommend_genre(
    tmdb_id: int = Query(...),
    limit: int = Query(18, ge=1, le=50),
):
    details = await tmdb_movie_details_basic(tmdb_id)

    if not details.genres:
        return []

    genre_id = details.genres[0]["id"]

    discover = await safe_tmdb_get(
        "/discover/movie",
        {
            "with_genres": genre_id,
            "include_adult": str(details.adult).lower(),
            "language": "en-US",
            "sort_by": "popularity.desc",
            "page": 1,
        },
    )

    if not discover:
        return []

    return await cards_from_raw_filtered(
        discover.get("results", []),
        selected_id=tmdb_id,
        selected_adult=details.adult,
        limit=limit,
    )


@app.get("/recommend/tfidf")
async def recommend_tfidf(
    title: str = Query(..., min_length=1),
    top_n: int = Query(10, ge=1, le=50),
):
    recs = tfidf_recommend_titles(title, top_n=top_n)
    return [{"title": title, "score": score} for title, score in recs]


@app.get("/movie/search", response_model=SearchBundleResponse)
async def search_bundle(
    query: str = Query(..., min_length=1),
    tfidf_top_n: int = Query(12, ge=1, le=30),
    genre_limit: int = Query(12, ge=1, le=30),
):
    best = await tmdb_search_first(query)

    if not best:
        raise HTTPException(status_code=404, detail=f"No TMDB movie found for query: {query}")

    tmdb_id = int(best["id"])
    details = await tmdb_movie_details_basic(tmdb_id)

    tfidf_items: List[TFIDFRecItem] = []
    recs: List[Tuple[str, float]] = []

    try:
        recs = tfidf_recommend_titles(details.title, top_n=tfidf_top_n)
    except Exception:
        try:
            recs = tfidf_recommend_titles(query, top_n=tfidf_top_n)
        except Exception:
            recs = []

    for title, score in recs:
        card = await attach_tmdb_card_by_title(title)
        tfidf_items.append(
            TFIDFRecItem(
                title=title,
                score=score,
                tmdb=card,
            )
        )

    genre_recs: List[TMDBMovieCard] = []

    if details.genres:
        genre_id = details.genres[0]["id"]

        discover = await safe_tmdb_get(
            "/discover/movie",
            {
                "with_genres": genre_id,
                "include_adult": str(details.adult).lower(),
                "language": "en-US",
                "sort_by": "popularity.desc",
                "page": 1,
            },
        )

        if discover:
            genre_recs = await cards_from_raw_filtered(
                discover.get("results", []),
                selected_id=details.tmdb_id,
                selected_adult=details.adult,
                limit=genre_limit,
            )

    return SearchBundleResponse(
        query=query,
        movie_details=details,
        tfidf_recommendations=tfidf_items,
        genre_recommendations=genre_recs,
    )