# Test environment to test streaks and validate if they work.
# Why not testing endpoints? Already did, and that's what Swagger docs are for anyway. Did that with curl.
# Since calculating streaks aren't dependent on endpoints, I can test them alone.
# They are only dependent on the session (can go back and look at recalculate_streak to check).

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, MediaType, MediaItem, MediaStatus, ProgressLog, Streak
from services import recalculate_streak
import pytest
from datetime import date

# we will be testing using a dummy, memory only DB. why not database.db?
# don't want my database data getting polluted!!!
engine = create_engine('sqlite:///:memory:')
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

# FIRST TEST: BOOK AND GAME ON THE SAME DAY (30+ mins each)
def test_book_game_same_days(db):
    # create a book and game!
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED)
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED)

    # we add both entries and flush them (send them) to the database.
    db.add(book)
    db.add(game)
    db.flush()

    # add 30-minute streaks for both of them (30 minutes+ for each is one streak point for each).
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    # run the function under test environment
    streak = recalculate_streak(db)

    # assert expected outcome.
    assert streak.current_streak == 1

# SECOND TEST: ALBUM AND WRESTLING MATCH ON THE SAME DAY
# criteria for each to get one streak point: must be completed today.
def test_streak_album_and_wrestling_same_day(db):
    album = MediaItem(title="Test Album", type=MediaType.ALBUM, status=MediaStatus.COMPLETED, finish_date=date.today())
    match = MediaItem(title="Test Match", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED, finish_date=date.today())
    db.add(album)
    db.add(match)
    db.commit()

    streak = recalculate_streak(db)

    assert streak.current_streak == 1

