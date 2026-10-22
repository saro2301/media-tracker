# Test environment to test streaks and validate if they work.
# Why not testing endpoints? Already did, and that's what Swagger docs are for anyway. Did that with curl.
# Since calculating streaks aren't dependent on endpoints, I can test them alone.
# They are only dependent on the session (can go back and look at recalculate_streak to check).
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base, MediaType, MediaItem, MediaStatus, ProgressLog, Streak, User
from services import recalculate_streak
import pytest, os
from datetime import date, timedelta

# we will be testing using a dummy, memory only DB. why not database.db?
# don't want my database data getting polluted!!!
load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(bind=engine)

# define db fixture
@pytest.fixture
def db():
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)

# define user1 fixture
@pytest.fixture
def user1(db):
    user = User(username="user1", email="test@test.com", password_hash="test")
    db.add(user)
    db.flush()
    return user
# define user2 fixture
@pytest.fixture
def user2(db):
    user = User(username="user2", email="test2@test.com", password_hash="test2")
    db.add(user)
    db.flush()
    return user
# FIRST TEST: BOOK AND GAME ON THE SAME DAY (30+ mins each, one user)
def test_book_game_same_days_single_user(db, user1):
    # create a book and game!
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED, user_id=user1.id)

    # we add both entries and flush them (send them) to the database.
    db.add(book)
    db.add(game)
    db.flush()

    # add 30-minute streaks for both of them (30 minutes+ for each is one streak point for each).
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    # run the function under test environment
    streak = recalculate_streak(db, user1)

    # assert expected outcome.
    assert streak.current_streak == 1

# SECOND TEST: ALBUM AND WRESTLING MATCH ON THE SAME DAY
# criteria for each to get one streak point: must be completed today.
def test_streak_album_and_wrestling_same_day_same_user(db, user1):
    album = MediaItem(title="Test Album", type=MediaType.ALBUM, status=MediaStatus.COMPLETED, finish_date=date.today(), user_id=user1.id)
    match = MediaItem(title="Test Match", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED, finish_date=date.today(), user_id=user1.id)
    db.add(album)
    db.add(match)
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak == 1

# THIRD TEST: ONLY ONE STREAK POINT ACCUMULATED (will test with all individually)
# ALL WORK! tested each individually by replacing media type.
def test_only_one_streak_point_same_user(db, user1):
    # game is BACKLOGGED, NEVER completed!
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    db.add(game)
    db.flush()

    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak == 0

# FOURTH TEST: STREAK CONTINUES CORRECTLY
# in the case of having a streak already, making another one, and having it increment the streak counter.
# NOTE: we don't have to test every combination anymore, did that already!
def test_streak_continues_same_user(db, user1):
    yesterday = date.today() - timedelta(days=1)

    existing_streak = Streak(
        id=1,
        user_id=user1.id,
        current_streak=3,
        current_streak_start=yesterday - timedelta(days=2),  # streak started a few days ago
        longest_streak=3,
        last_updated=yesterday
    )
    db.add(existing_streak)

    # now create today's qualifying activity
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    db.add(book)
    db.add(game)
    db.flush()

    # add logs for both
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak == 4  # incremented from 3.
    assert streak.current_streak_start == yesterday - timedelta(days=2)  # unchanged, proves it continued, not reset.

# FIFTH TEST: STREAK FURTHER BACK THAN A DAY, NEW STREAK GENERATED
# streak should go to 1.
def test_streak_resets_same_user(db, user1):
    days_ago = date.today() - timedelta(days=2)

    existing_streak = Streak(
        id=1,
        user_id=user1.id,
        current_streak=3,
        current_streak_start=days_ago-timedelta(days=2),
        longest_streak=3,
        last_updated=days_ago
    )
    db.add(existing_streak)

    # now we create today's activity.
    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    match = MediaItem(title="Test Match", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED, finish_date=date.today(), user_id=user1.id)
    db.add(book)
    db.add(match)
    db.flush()

    # add the completions of progress
    db.add(ProgressLog(media_item_id=book.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak == 1

# SIXTH TEST: ONE QUALIFYING STREAK POINT, ANOTHER OUTDATED STREAK POINT
# outdated streak point example: when an album was logged completed, but it was NOT completed today.
def test_backdated_streak_case_one_user(db, user1):
    game = MediaItem(title="Test Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    album = MediaItem(title="Test Album", type=MediaType.ALBUM, status=MediaStatus.BACKLOGGED, finish_date=None, user_id=user1.id)
    db.add(game)
    db.add(album)
    db.flush()

    # add completion of time-dependent progress
    db.add(ProgressLog(media_item_id=game.id, progress_time=30, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak != 1

# SEVENTH TEST: two users, one streak point each. streaks for both users should be zero.
# since all work, can do any combo. Game for user 1, album for user 2.
def test_one_streak_point_two_users(db, user1, user2):
    entry1 = MediaItem(title="User 1 Game", type=MediaType.GAME, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    entry2 = MediaItem(title="User 2 Album", type=MediaType.ALBUM, status=MediaStatus.COMPLETED, finish_date= date.today(),user_id=user2.id)
    db.add(entry1)
    db.add(entry2)
    db.flush()

    # add completion of game progress for user 1
    db.add(ProgressLog(media_item_id=entry1.id, progress_time=30, date_of_progress=date.today()))
    db.commit()
    streak1 = recalculate_streak(db, user1)
    streak2 = recalculate_streak(db, user2)

    assert streak1.current_streak == 0 and streak2.current_streak == 0

# EIGHTH TEST: two users, with an existing streak of one, get two streak points each.
# both streaks should increment to 2.
def test_existing_streak_point_two_users(db, user1, user2):
    yesterday = date.today() - timedelta(days=1)
    # user 1's existing streak
    existing_streak1 = Streak(
        id=1,
        user_id=user1.id,
        current_streak=1,
        longest_streak=1,
        current_streak_start=yesterday,
        last_updated=yesterday
    )
    # user 2's existing streak
    existing_streak2 = Streak(
        id=2,
        user_id=user2.id,
        current_streak=1,
        longest_streak=1,
        current_streak_start=yesterday,
        last_updated=yesterday
    )
    db.add(existing_streak1)
    db.add(existing_streak2)
    db.flush()

    # user 1 now gets two streak points, and adds to their streak! since all work, let's do album and wrestling for both.
    user1_wrestling = MediaItem(title="User1Wrestling", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED, user_id=user1.id, finish_date=date.today())
    user1_album = MediaItem(title="User1Album", type=MediaType.ALBUM, status=MediaStatus.COMPLETED, user_id=user1.id, finish_date=date.today())
    db.add(user1_wrestling)
    db.add(user1_album)
    db.flush()

    # user 2's points
    user2_wrestling = MediaItem(title="User2Wrestling", type=MediaType.WRESTLING, status=MediaStatus.COMPLETED,
                                user_id=user2.id, finish_date=date.today())
    user2_album = MediaItem(title="User2Album", type=MediaType.ALBUM, status=MediaStatus.COMPLETED, user_id=user2.id,
                           finish_date=date.today())
    db.add(user2_wrestling)
    db.add(user2_album)
    db.flush()

    streak1 = recalculate_streak(db, user1)
    streak2 = recalculate_streak(db, user2)

    assert streak1.current_streak == 2 and streak2.current_streak == 2
# NINTH TEST: STREAK FROM YESTERDAY SURVIVES A PARTIAL DAY
# logging less than a full day's points shouldn't wipe a streak that was kept yesterday.
def test_partial_day_keeps_streak_same_user(db, user1):
    yesterday = date.today() - timedelta(days=1)

    existing_streak = Streak(
        id=1,
        user_id=user1.id,
        current_streak=5,
        current_streak_start=yesterday - timedelta(days=4),
        longest_streak=5,
        last_updated=yesterday
    )
    db.add(existing_streak)

    book = MediaItem(title="Test Book", type=MediaType.BOOK, status=MediaStatus.BACKLOGGED, user_id=user1.id)
    db.add(book)
    db.flush()

    db.add(ProgressLog(media_item_id=book.id, progress_time=10, date_of_progress=date.today()))
    db.commit()

    streak = recalculate_streak(db, user1)

    assert streak.current_streak == 5
