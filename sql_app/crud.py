from sqlalchemy.orm import Session
from . import models, schemas

"""
Kantsii luoda erikseen, eikä polkuun, jotta voi käyttää kans testeihin
"""

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserRequest):
    fake_hash = user.password + "not-really-a-hash"
    db_user = models.User(email=user.email, hashed_password=fake_hash)
    db.add(db_user)
    db.commit()
    db.refresh(db_user) # refreshi liittää db:stä dataa, esim. luodun id:n
    # return Model ilman hashia?
    return db_user


def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Item).offset(skip).limit(limit).all()


def create_item(db: Session, item: schemas.ItemRequest, user_id: int):
    db_item = models.Item(**item.dict(), owner_id=user_id) # **item.dict() on vaihtoehto sille, että explisiittisesti antaisi joka kentän (esim. title = item.title)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


