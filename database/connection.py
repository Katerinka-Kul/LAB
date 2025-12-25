from sqlmodel import SQLModel, Session, create_engine, select
from models.users import User
from models.events import Event

# Одна БД для всего приложения
DATABASE_FILE = "soulmate.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"
connect_args = {"check_same_thread": False}

# Создаем единый движок для всей БД
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Показывать SQL запросы в консоли
    connect_args=connect_args
)

# Создание всех таблиц
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Генератор сессий для dependency injection
def get_session():
    with Session(engine) as session:
        yield session

# Инициализация БД с тестовыми данными
def init_db():
    create_db_and_tables()
    
    with Session(engine) as session:
        # Проверяем, есть ли уже администратор
        admin = session.exec(
            select(User).where(User.username == "Administrator")
        ).first()
        
        if not admin:
            # Создаем администратора
            admin_user = User(
                username="Administrator",
                age=21,
                password="12345678",
                is_admin=True,
                preferences={
                    "food": ["pizza", "burgers"],
                    "books": ["fantasy", "detective"],
                    "movies": ["fantasy", "action"]
                }
            )
            session.add(admin_user)
            print("Administrator created")
        
        # Проверяем, есть ли тестовые события
        events = session.exec(select(Event)).all()
        if len(events) == 0:
            # Создаем тестовые события
            sample_events = [
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
            
            for event in sample_events:
                session.add(event)
            print("Sample events created")
        
        session.commit()
        print(" Database initialized successfully!")