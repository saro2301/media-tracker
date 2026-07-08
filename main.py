from fastapi import FastAPI, Depends
from database import get_db
from schemas import Media
from typing import Annotated
from sqlalchemy.orm import Session
from models import MediaItem
from datetime import datetime

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# post endpoint to create a media item by sending the info.
# NOTE: once external APIs are integrated, change to async.
@app.post("/media/")
def create_media(media: Media, db: Annotated[Session, Depends(get_db)]):

    # NOTE: media_dict has fields NOT in media item. unpacking manually, just to be safe.
    new_media = MediaItem(
        title=media.title,
        type=media.type,
        status=media.status,
        rating=media.rating,
        picture=media.picture,
        creation_date=datetime.now()
    )

    # add it to the session and commit
    db.add(new_media)
    db.commit()

    # get DB-generated ID for returning.
    db.refresh(new_media)

    return new_media
