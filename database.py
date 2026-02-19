from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
from config import settings
engine=create_engine(settings.DATABASE_URL)
Sessionlocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
Base=declarative_base()

def get_db():
    db=Sessionlocal()
    try:
        yield db
    finally:
        db.close()