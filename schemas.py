from datetime import date
from models import MediaType, MediaStatus, CreatorType, BookType
from pydantic import BaseModel

# creators class, dependent on media type
class CreatorData(BaseModel):
    name: str
    creator_type: CreatorType

# book class, dependent on book type
class BookData(BaseModel):
    book_type: BookType

# wrestling class to store events
class WrestlingData(BaseModel):
    event: str

# media class for posting (requesting a media)
class Media(BaseModel):
    title: str
    type: MediaType
    creators: list[CreatorData] = []        # can have multiple creators, so it's a list of creators.
    book_type: BookData | None              # many book types, if not a book then None.
    wrestling_data: WrestlingData | None    # to store event data.
    status: MediaStatus = MediaStatus.BACKLOGGED
    rating: float | None = None             # default as None, rating isn't necessary initially.
    picture: str | None = None              # default as None, picture isn't necessary initially.
    finish_date: date | None = None     # default as None (finish date is TBD)

# media item update class for patching (changing information)
# editable: rating, image, status.
class MediaUpdate(BaseModel):
    rating: float | None = None
    picture: str | None = None
    status: MediaStatus | None = None

# progress log class to track how much media was consumed.
# as creation date (date of logging) is already logged, only need time and notes.
# time being MINUTES logged. notes are optional
class ProgressLogData(BaseModel):
    time: int
    notes: str | None = None

# user create class to create a user.
class UserCreation(BaseModel):
    email: str
    username: str
    password: str

# login class that holds info user needs to log in.
class UserLogin(BaseModel):
    username: str
    password: str


