from fastapi import FastAPI, Depends
from database import get_db
from schemas import Media
from typing import Annotated
from sqlalchemy.orm import Session
from models import MediaItem, MediaType, Book, Creator, MediaCreator
from datetime import datetime

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# post endpoint to create a media item by sending the info.
# NOTE: once external APIs are integrated, change to async.
@app.post("/media/")
def create_media(media: Media, db: Annotated[Session, Depends(get_db)]):

    # NOTE: media_dict (the Pydantic schema "Media" has fields NOT in MediaItem. unpacking manually, just to be safe.)
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
    db.flush()

    # if the media type is a book, add the book type.
    if media.type == MediaType.BOOK and media.book_type is not None:
        new_book = Book(
            media_item_id=new_media.id,             # this book belongs to this media
            book_type=media.book_type.book_type     # this book type belongs to this book
        )
        db.add(new_book)

    # add all creators.
    for creator in media.creators:
        # creator type
        new_creator = Creator(
            name=creator.name,
            creator_type=creator.creator_type,
        )

        db.add(new_creator)
        db.flush()              # need to flush to get the id

        # media creator type to link the creator and the creator type.
        new_media_creator = MediaCreator(
            media_item_id=new_media.id,
            creator_id=new_creator.id,
        )

        db.add(new_media_creator)


    db.commit()

    # get DB-generated ID for returning.
    db.refresh(new_media)

    return new_media

# get endpoint to retrieve info from the database.
# NOTE: once external APIs are integrated, change to async.

@app.get("/media/")
def get_media(db: Session = Depends(get_db)):
    return db.query(MediaItem).all()
