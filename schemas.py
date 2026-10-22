# Here live the Pydantic schemas.

from datetime import date
from models import MediaType, MediaStatus, CreatorType, BookType
from pydantic import BaseModel, model_validator

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
    book_type: BookData | None = None             # many book types, if not a book then None.
    wrestling_data: WrestlingData | None = None   # to store event data.
    status: MediaStatus = MediaStatus.BACKLOGGED
    rating: float | None = None             # default as None, rating isn't necessary initially.
    picture: str | None = None              # default as None, picture isn't necessary initially.
    finish_date: date | None = None     # default as None (finish date is TBD)

    # We need a finish date validator. Why? When something is completed, we need a finish date no matter what.
    @model_validator(mode="after")
    def finish_date_validator(self):
        if self.status == MediaStatus.COMPLETED and self.finish_date is None:
            raise ValueError("finish date is required when marking something completed")
        return self

# media item update class for patching (changing information)
# editable: rating, image, status.
class MediaUpdate(BaseModel):
    rating: float | None = None
    picture: str | None = None
    status: MediaStatus | None = None
    finish_date: date | None = None

    # same finish date validator
    @model_validator(mode="after")
    def finish_date_validator(self):
        if self.status == MediaStatus.COMPLETED and self.finish_date is None:
            raise ValueError("finish date is required when marking something completed")
        return self

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

# refresh class that holds the refresh token, sent in the body to get a new access token.
class RefreshRequest(BaseModel):
    refresh_token: str


