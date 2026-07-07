from models import Base, MediaItem, Book, Album, Game, Wrestling, Creator, CreatorType, ProgressLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# creating database engine (CRUD = create, read, update, delete)
engine = create_engine('sqlite:///database.db')

# creating a sessionmaker, one time and global session creator.
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# create the database.
Base.metadata.create_all(engine)


