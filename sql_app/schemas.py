from pydantic import BaseModel


class ItemBase(BaseModel):
    title: str
    description: str | None = None


class ItemRequest(ItemBase):
    pass


class Item(ItemBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

# ------


class UserBase(BaseModel):
    email: str


class UserRequest(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    items: list[Item] = []

    class Config:
        orm_mode = True

"""
orm_mode mahdollistaa datan lukemisen kuten dict:stä, ja user-items suhteen tjsp:
https://fastapi.tiangolo.com/tutorial/sql-databases/#technical-details-about-orm-mode
"""
