from models import Base, MediaItem, Book, Wrestling, Creator, MediaCreator, ProgressLog, Streak, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# creating database engine (CRUD = create, read, update, delete)
engine = create_engine(os.getenv("DATABASE_URL"))

# creating a sessionmaker, one time and global session creator.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# creating the dependency generator. using yield to clean up after API request is done.
def get_db():
    db = SessionLocal()
    try:
        yield db    # session injected into endpoint here
    finally:
        db.close()  # session close after yield finishes.

# create the database.
Base.metadata.create_all(engine)


