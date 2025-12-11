from sqlmodel import SQLModel, Session, create_engine
from models.events import Event
from models.users import User

# SQLite database file
database_file = "soulmate.db"
database_connection_string = f"sqlite:///{database_file}"

# Connection arguments for SQLite
connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(
    database_connection_string,
    echo=True,  # Set to False in production
    connect_args=connect_args
)

# Create all tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Get session dependency
def get_session():
    with Session(engine) as session:
        yield session

# Initialize database
def init_db():
    create_db_and_tables()
    
    # Add initial events if database is empty
    with Session(engine) as session:
        events_count = session.query(Event).count()
        if events_count == 0:
            # Add sample events
            events = [
                Event(
                    title="Italian Cuisine Evening",
                    image="/static/images/italian-food.jpg",
                    description="Let's cook pasta and pizza together! Recipe exchange and tasting for Italian cuisine lovers",
                    location="Culinary Studio 'Tasty'",
                    tags=["cooking", "italian cuisine", "pasta", "pizza"],
                    participants=[]
                ),
                Event(
                    title="Book Club: Science Fiction",
                    image="/static/images/book-club.jpg",
                    description="Discussion of the latest sci-fi releases. Bring your favorite books to exchange opinions!",
                    location="Coffee Shop 'Reading Room'",
                    tags=["books", "science fiction", "literature", "discussion"],
                    participants=[]
                ),
                Event(
                    title="Movie Night: Best Comedies",
                    image="/static/images/movie-night.jpg",
                    description="Screening and discussion of classic comedies with popcorn and good company",
                    location="Cinema Center 'Rodina'",
                    tags=["movies", "comedies", "screening", "discussion"],
                    participants=[]
                )
            ]
            
            for event in events:
                session.add(event)
            session.commit()