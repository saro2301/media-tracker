from fastapi import FastAPI, Depends, HTTPException
from database import get_db
from schemas import Media, MediaUpdate, ProgressLogData
from typing import Annotated
from sqlalchemy.orm import Session
from models import MediaItem, MediaType, Book, Creator, MediaCreator, ProgressLog
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

# get endpoint to retrieve ALL entries from the database.
# NOTE: once external APIs are integrated, change to async.
@app.get("/media/")
def get_all_media(db: Annotated[Session, Depends(get_db)]):
    return db.query(MediaItem).all()

# get endpoint to retrieve ONE entry from the database.
@app.get("/media/{id}")
def get_one_media(id: int, db: Annotated[Session, Depends(get_db)]):
    media = db.query(MediaItem).filter(MediaItem.id == id).first()

    # NOTE: not completely necessary to handle ID not found case, as media must be made.
    # won't hurt to do it! raise 404 not found.
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return media

# patch endpoint to change certain fields in data.
# editable: title, rating, status.
@app.patch("/media/{id}")
def update_media(id: int, media_update: MediaUpdate, db: Annotated[Session, Depends(get_db)]):
    item = db.query(MediaItem).filter(MediaItem.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Media not found")

    if media_update.rating is not None:
        item.rating = media_update.rating
    if media_update.status is not None:
        item.status = media_update.status
    if media_update.picture is not None:
        item.picture = media_update.picture

    db.commit()
    db.refresh(item)
    return item

# delete endpoint to remove an entry entirely.
@app.delete("/media/{id}")
def delete_data(id: int, db: Annotated[Session, Depends(get_db)]):
    item = db.query(MediaItem).filter(MediaItem.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Media not found")

    db.delete(item)
    db.commit()

    return item

# PROGRESS LOG ENDPOINTS

# post endpoint to send media progress to the database.
# REMINDER: only games and books can be loggable. albums and matches cannot be logged.
@app.post("/media/{id}/log")
def create_log_entry(id: int, log: ProgressLogData, db: Annotated[Session, Depends(get_db)]):
    item = db.query(MediaItem).filter(MediaItem.id == id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Media not found")
    if item.type == MediaType.BOOK or item.type == MediaType.GAME:
        new_log = ProgressLog(
            media_item_id=id,
            progress_time=log.time,
            notes=log.notes,
            date_of_progress=datetime.now()
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log
    else:
        raise HTTPException(status_code=400, detail="Log entry not applicable for media type")


