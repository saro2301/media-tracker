# File that holds all database models.

# import files as needed.
import enum
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# define base class
class Base(DeclarativeBase):
    pass

# ENUMS

# enum for the MediaType class. these are the types I'm going to be using
class MediaType(enum.Enum):
    BOOK = "book"
    ALBUM = "album"
    GAME = "game"
    WRESTLING = "wrestling"

# enum for the status of the media
class MediaStatus(enum.Enum):
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    BACKLOGGED = "backlogged"
    DROPPED = "dropped"

# enum for the Book types
class BookType(enum.Enum):
    MANGA = "manga"
    VISUAL_NOVEL = "visual novel"
    FICTION = "fiction"
    NON_FICTION = "non-fiction"

# enum for the Creator types
class CreatorType(enum.Enum):
    AUTHOR = "author"
    GAME_STUDIO = "game studio"
    PROMOTION = "promotion"
    ARTIST = "artist"

# media item class
class MediaItem(Base):
    __tablename__ = 'media_item'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    status: Mapped[MediaStatus] = mapped_column(Enum(MediaStatus))
    rating: Mapped[float | None] = mapped_column()
    picture: Mapped[str | None] = mapped_column()
    creation_date: Mapped[datetime | None] = mapped_column()
    finish_date: Mapped[datetime | None] = mapped_column()

# MEDIA TYPE CLASSES

# book class
class Book(Base):
    __tablename__ = 'book'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))
    book_type: Mapped[BookType] = mapped_column(Enum(BookType))

# game class
class Game(Base):
    __tablename__ = 'game'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))

# album class
class Album(Base):
    __tablename__ = 'album'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))

# wrestling match class
class Wrestling(Base):
    __tablename__ = 'wrestling'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))
    event: Mapped[str] = mapped_column()

# Creator class. all types of creators will go here.
class Creator(Base):
    __tablename__ = 'creator'
    name: Mapped[str] = mapped_column()
    id: Mapped[int] = mapped_column(primary_key=True)
    creator_type: Mapped[CreatorType] = mapped_column(Enum(CreatorType))

# MediaCreator class. all creators (can be more than one) will go here.
class MediaCreator(Base):
    __tablename__ = 'media_creator'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))
    creator_id: Mapped[int] = mapped_column(ForeignKey('creator.id'))

# Progress Log class. Class to keep track of media progress
class ProgressLog(Base):
    __tablename__ = 'progress_log'
    id: Mapped[int] = mapped_column(primary_key=True)
    media_item_id: Mapped[int] = mapped_column(ForeignKey('media_item.id'))
    progress_time: Mapped[int] = mapped_column()
    date_of_progress: Mapped[datetime] = mapped_column()
    notes: Mapped[str | None] = mapped_column()



