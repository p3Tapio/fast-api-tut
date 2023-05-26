# https://fastapi.tiangolo.com/tutorial/security/
from typing import Annotated
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

"""
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#oauth2-with-password-and-hashing-bearer-with-jwt-tokens
pip install python-multipart --> form_data
pip install "python-jose[cryptography]" --> jwt
pip install "passlib[bcrypt]" --> hasher
openssl rand -hex 32 --> tuolla komennolla voi generoida random stringin joka secret_key:n arvona
"""

SECRET_KEY = "b5da31f5240b3030373f40b7a7fa63542fa727412558639039d34f2561857261"
ALGORITH = "HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = 30

fake_user_db = {
    "pertti": {
        "username": "pertti",
        "full_name": "Pertti Pasanen",
        "email": "pertti@hotmail.xyz",
        "hashed_pwd": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False
    }
}

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDb(User):
    hashed_pwd: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()


def verify_password(plain_pwd, hashed_pwd):
    return pwd_context.verify(plain_pwd, hashed_pwd)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDb(**user_dict)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_pwd):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITH)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITH])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)

    except JWTError:
        raise credentials_exception

    user = get_user(fake_user_db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token", response_model=Token)
async def login_for_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(
        fake_user_db, form_data.username, form_data.password
    )

    if not user:
        raise credentials_exception

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires)
    # sub tulee  JWT specseistä, optional, mutta sinne käyttäjän tunnistaminen. Voi lisätä muutakin esim. lupatietoa, prefixata sitä esim 'username:' yms. Olennaista että tulisi olla uniikki stringi ym.
    # https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#technical-details-about-the-jwt-subject-sub
    return {"access_token": access_token, "token_type": "Bearer"}


@app.get("/users/me/", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

""" Aikaisemmat chapterit alla, missä feikki-autentikoinnit jne """


# @app.get("/items/")
# async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
#     return {"token": token}


'''
GET CURRENT USER

-- samaa templaa voi käyttää muuhunkin kuin userin palauttamiseen 
-- voi olla myös muutakin datamuotoa kuin classista repästy

-- Mekanismia kantsii kierrätää kaikkiin authia vaativiin endpointteihin

'''


# def fake_decoder(token):
#     return User(
#         username=token+"fakedecoded", email="something@somewhere.com", full_name="John Doe"
#     )


# async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#     user = fake_decoder(token)
#     return user


# @app.get("/users/me")
# async def users_me(current_user: Annotated[User, Depends(get_current_user)]):
#     return current_user

'''


simple OAuth2 with Password and Bearer

- form datana (eli ei json) ja tulee nimetä username & password
- mukaan voi tyrkätä myös muuttujan "scope" (str), käytetää esim users:read / users:write eli käyttisoikeuksien laajuuteen

'''

"""
class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDb(User):
    hashed_pw: str


fake_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@mail.com",
        "hashed_pw": "fakehashsecretpw",
        "disabled": False
    },
    "pertti": {
        "username": "pertti",
        "full_name": "Pertti Pasanen",
        "email": "pertti@example.com",
        "hashed_pw": "fakesecrethash",
        "disabled": True
    }
}


def fake_hash_pw(password: str):
    return "fake" + password


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDb(**user_dict)


def fake_decoder(token):
    user = get_user(fake_db, token)
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    user = fake_decoder(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"} # oayth2 spec, toimii myös ilman
        )
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


@app.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_dict = fake_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Incorrect username or password")
    user = UserInDb(**user_dict)
    hashed = fake_hash_pw(form_data.password)
    if not hashed == user.hashed_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Incorrect username or password")

    # oauth2 spec: palauta json jossa noi (ja sisään form_datana)
    return {"access_token": user.username, "token_type": "bearer"}


@app.get("/users/me", response_model=User, response_model_exclude={"hashed_pw", "disabled"})
async def users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

The OAuth2 spec actually requires a field grant_type with a fixed value of password, but OAuth2PasswordRequestForm doesn't enforce it.
If you need to enforce it, use OAuth2PasswordRequestFormStrict instead of OAuth2PasswordRequestForm

"""
