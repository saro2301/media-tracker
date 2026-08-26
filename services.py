# Here lives all logic that isn't an endpoint, a schema, or a database model.

from datetime import date, timedelta, datetime, timezone
from dotenv import load_dotenv
from models import Streak, ProgressLog, MediaItem, MediaType, MediaStatus, User
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Annotated
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import bcrypt, os, httpx
from database import get_db

# JWT ACCESS METHOD
load_dotenv()

SECRET_KEY = os.environ["SECRET_KEY"]
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # "point people to this url to get their token/access"

# create token method! placebo: 30 minutes per session. data = user id
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# create refresh token. need this to handle cases where user is logged in after original JWT expires.
def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})        # type "refresh" is just to tell what token type it is
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# get current user method. doing the inverse of creating the token. REMEMBER: access information is user ID, not username!
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]):
    # try/except: is the token itself malformed or expired? is it cryptographically legitimate?
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        user_id: str = payload.get("sub")
        # proper token, but does "sub" include what is expected? did i get what i wanted out of it?
        if user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # does the user exist at all?
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user

# streak recalculation logic:
# first, need to check all categories for streak points.
# book: query all books read today and see if we've exceeded 30 minutes. if so, add streak point.
# game: query all games played today and see if we've exceeded 30 mins playtime. add streak point if so
# album: query all albums marked completed today. add streak point if at least one was marked completed today
# match: query all wrestling matches marked completed today. add streak point as needed

def recalculate_streak(db: Session, current_user: User):
    today = date.today()
    yesterday = today - timedelta(days=1)
    streak_points = 0           # streak points current counter

    # query books read today, and see if >= 30 mins exceeded
    book_minutes = (db.query(func.sum(ProgressLog.progress_time))
    .join(MediaItem, ProgressLog.media_item_id == MediaItem.id)
    .filter(MediaItem.type == MediaType.BOOK, ProgressLog.date_of_progress == today,
            MediaItem.user_id == current_user.id)).scalar()

    if (book_minutes or 0) >= 30:
        streak_points += 1

    # query games played today, same logic as book
    game_minutes = (db.query(func.sum(ProgressLog.progress_time))
    .join(MediaItem, ProgressLog.media_item_id == MediaItem.id)
    .filter(MediaItem.type == MediaType.GAME, ProgressLog.date_of_progress == today,
            MediaItem.user_id == current_user.id)).scalar()

    if (game_minutes or 0) >= 30:
        streak_points += 1

    # query albums listened to today, and see if >= 1 album completed
    albums_completed = db.query(MediaItem).filter(MediaItem.type == MediaType.ALBUM,
    MediaItem.status == MediaStatus.COMPLETED, MediaItem.finish_date == today, MediaItem.user_id == current_user.id).first()

    if albums_completed is not None:
        streak_points += 1

    # query matches, same thing.
    matches_completed = db.query(MediaItem).filter(MediaItem.type == MediaType.WRESTLING,
    MediaItem.status == MediaStatus.COMPLETED, MediaItem.finish_date == today, MediaItem.user_id == current_user.id).first()

    if matches_completed is not None:
        streak_points += 1


    # STREAK LOGIC:
    streak = db.query(Streak).filter(Streak.user_id == current_user.id).first()

    # first ever run, need to create the rows.
    if streak is None:
        streak = Streak(
            user_id=current_user.id,
            current_streak=0,
            longest_streak=0,
            current_streak_start=None,
            longest_streak_start=None,
            current_streak_end=None,
            longest_streak_end=None,
        )
        db.add(streak)

    # if streak_points >= 2 (if there's something new to add to the streak)
    if streak_points >= 2:
        # if streak last updated today, don't change anything.
        if streak.last_updated == today:
            pass
        # if streak last updated yesterday, increment streak counter and change last_updated to today.
        elif streak.last_updated == yesterday:
            streak.current_streak += 1
            streak.last_updated = today
            streak.current_streak_end = today
        # if streak last updated WAS NOT yesterday, make streak counter 1, and change last_updated to today.
        else:
            streak.current_streak = 1
            streak.current_streak_start = today
            streak.current_streak_end = today
            streak.last_updated = today

        # if current streak is now bigger than the longest streak...
        # longest streak is now equal to current streak,
        # longest streak start is now equal to current streak start,
        # and longest streak end is not equal to current streak end, which is today.
        # then add streak to the db.
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
            streak.longest_streak_start = streak.current_streak_start
            streak.longest_streak_end = today
    # if none apply, and if there is no streak at all, then our current streak becomes zero.
    else:
        streak.current_streak = 0

    # NOTE: only commit here, as adding is just making the rows.
    # this part of the function is to patch the existing streak rows,
    # not to make new ones.
    db.commit()

    return streak

# function to hash password. going to be using bcrypt as it's lighter.
def hash_password(password: str) -> str:
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed_password.decode("utf-8")      # NOTE: not decoding the password, decoding the HASH (for DB storage). bytes to string

# MUSICBRAINZ API ALBUM SEARCH FUNCTION
# The goal of MusicBrainz API with this app is to:
# 1. give me experience working with external API's, JSONs and file parsing (very transferrable skill)
# 2. make it easier for user to create album medias.
# search album function, this uses MusicBrainz API to search albums.

def search_album(album: str, artist: str | None = None):
    # query album that is needed.
    search_query = album
    # if we plan on also searching using an artist, search using both.
    if artist:
        search_query = f'{album} AND artist:"{artist}"'

    # get the album itself that is being searched.
    response = httpx.get(
        "https://musicbrainz.org/ws/2/release-group/",
        params={"query": search_query, "fmt": "json"},         # query is the album being searched, JSON format.
        headers={"User-Agent": "MediaTracker/1.0 (samrod2301@gmail.com)"}
    )

    data = response.json()

    # now, make a list of what the result is going to consist of
    # we need a title, artist, MusicBrainz ID (for convenience) and a score
    # the score being measured on a scale of 1-100,
    # how accurate is the album we want?
    results = []

    # in case of an internal server error (likely MusicBrainz's rate limit), add a check.
    if "release-groups" not in data:
        return []

    for releases in data["release-groups"]:
        # to account for multiple artists (e.g. Freddie Gibbs AND Madlib in Pinata), have to treat as a list.
        artists = [credit["name"] for credit in releases["artist-credit"]]

        results.append({
            "title": releases["title"],
            "artist": artists, # element 0 as the artist name is usually the creator we care most about.
            "mbid": releases["id"],
            "score": releases["score"]
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results

