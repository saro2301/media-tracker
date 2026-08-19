# Test environment to test streaks and validate if they work.
# Why not testing endpoints? Already did, and that's what Swagger docs are for anyway. Did that with curl.
# Since calculating streaks aren't dependent on endpoints, I can test them alone.
# They are only dependent on the session (can go back and look at recalculate_streak to check).

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, MediaType, MediaItem, MediaStatus, ProgressLog, Streak
from services import recalculate_streak
import pytest
from datetime import date, timedelta

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

# THIRD TEST: ONLY ONE STREAK POINT ACCUMULATED (will test with all individually)
# ALL WORK! tested each individually by replacing media type.
def test_only_one_streak_point(db):
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED)
    db.add(game)
    db.flush()

    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db)

    assert streak.current_streak == 0

# FOURTH TEST: STREAK CONTINUES CORRECTLY
# in the case of having a streak already, making another one, and having it increment the streak counter.
# NOTE: we don't have to test every combination anymore, did that already!
def test_streak_continues(db):
    yesterday = date.today() - timedelta(days=1)

    existing_streak = Streak(
        id=1,
        current_streak=3,
        current_streak_start=yesterday - timedelta(days=2),  # streak started a few days ago
        longest_streak=3,
        last_updated=yesterday
    )
    db.add(existing_streak)

    # now create today's qualifying activity
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED)
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED)
    db.add(book)
    db.add(game)
    db.flush()

    # add logs for both
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db)

    assert streak.current_streak == 4  # incremented from 3.
    assert streak.current_streak_start == yesterday - timedelta(days=2)  # unchanged, proves it continued, not reset.

# FIFTH TEST: STREAK FURTHER BACK THAN A DAY, NEW STREAK GENERATED
# streak should go to 1.
def test_streak_resets(db):
    days_ago = date.today() - timedelta(days=2)

    existing_streak = Streak(
        id=1,
        current_streak=3,
        current_streak_start=days_ago-timedelta(days=2),
        longest_streak=3,
        last_updated=days_ago
    )
    db.add(existing_streak)

    # now we create today's activity.
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED)
    match = MediaItem(title="Test Match", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED, finish_date=date.today())
    db.add(book)
    db.add(match)
    db.flush()

    # add the completions of progress
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db)

    assert streak.current_streak == 1

# SIXTH TEST: ONE QUALIFYING STREAK POINT, ANOTHER OUTDATED STREAK POINT
# outdated streak point example: when an album was logged completed, but it was NOT completed today.
def test_backdated_streak_case(db):
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED)
    album = MediaItem(title="Test Album", type=MediaType.ALBUM, status=MediaStatus.BACKLOGGED, finish_date=None)
    db.add(game)
    db.add(album)
    db.flush()

    # add completion of time-dependent progress
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db)

    assert streak.current_streak != 1