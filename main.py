from datetime import datetime
from enum import Enum
import random
from string import Template
from fastapi import FastAPI, HTTPException, Response, status, Query, Path, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Union
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Annotated
import os

# env testi: jos ENV=production uvicorn main:app --reload, niin ei doksuja, muuten /redoc tai /docs
env = os.environ['ENV']
app = FastAPI(openapi_url=None if env == 'production' else '/openapi.json')

# alkuun käytetty Union[] on python < 3.10 version takia, myöhempi | toimii > 3.10:ssä

'''
PATH PARAMS & ENUM
'''


@app.get("/items/{item_id}")
# "All the data validation is performed under the hood by https://pydantic-docs.helpmanual.io"
async def return_item(item_id: int):
    return {"item_id": item_id}


# arvioidaan järjestyksessä: /me tulee olla ekana tai kutsu osuu alempana olevaan polkuun
@app.get("/users/me")
async def return_users_me():
    return {"user_id": "Hello, me!"}


@app.get("/users/{user_id}")
async def return_user(user_id: str):
    return {"user_id": user_id}


# -- ENUM mm. validointiin ---


class CountryName(str, Enum):
    finland = "finland"
    italy = "italy"
    bhutan = "bhutan"


@app.get("/countries/{country_name}")
# esimerkkinä miten saa enumin arvon, ja pari tapaa konkanoida stringiä
async def get_country(country_name: CountryName):
    if country_name is CountryName.finland:
        return {"country": country_name, "message": 'It is cold in {name}!'.format(name=country_name)}
    elif country_name.value == 'bhutan':
        return {"country": country_name, "message": f'Can you find {country_name} from world map?'}

    t = Template("Mamma mia, it is $name!")
    return {"country": country_name, "message": t.substitute(name=country_name.value)}

'''
QUERY PARAMS
- Näissä voi käyttää kans Enumia kuten yllä
'''
fake_items_db = [{"item_name": "Foo"}, {
    "item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/fake-db/")
# /fake-db?skip=1&limit=2
# saapuu striginä, mutta konvertoituu kun alla int ja validoituu sen mukaan (esim limit=x kyykkää). Tässä asetettu myös defaultit.
async def return_fake_db(skip: int = 0, limit: int = 10):
    return fake_items_db[skip: skip + limit]


@app.get("/opt-params/{some_id}")
# optional query params: eli q, joka str tai none ja defaulttina none
# Union tai python 3.10: str | None
async def return_something(some_id: str, q: Union[str, None] = None):
    if q:
        return {"id": some_id, "q": q}
    return {"id": some_id}


@app.get("/opt-params-2/{some_id}")
# huom update (ja boolean)
# /opt-params-2/asd?q=hello&short=true (tai koklaa 0/1, tai yes / no)
# näitä voi olla myös enemmän, ooh! https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
async def return_something_again(some_id: str, q: Union[str, None] = None, short: bool = False):
    something = {"id": some_id}

    if q:
        something.update({"q": q})

    if not short:
        something.update(
            {"description": "This is some really long thingy that results if short is false!"})

    return something


"""
Required query parameters

- jos default arvot, niin paramsit ei pakollisia (toimii myös ilman arvoa kun esim param: str = None)
- Ilman defaultteja param on pakollinen
- routessa voi olla kaikkee: pakollisia ja ei, query ja path parameja (tosin 404, jos tuonne nakkaa ei-pakollisen path paramin väliin ja ei anna sitä kutsussa)

"""


@app.get("/required-params/{required_param}")
async def return_thingies(required_param: str, required_query: str,  not_required_query: Union[int, None] = None):
    return {"required_param": required_param, "required_query": required_query, "not_required_query": not_required_query}


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
REQUEST BODY

Validointi-ilon lisäksi, class / Pydantic BaseModel niin VSC osaa ehdottaa attribuutit
str | None = None --> not required
"""


class Movie(BaseModel):
    id: int | None = None
    title: str
    description: str | None = None
    director: str
    ticket_price: float | None = None
    audience: int | None = None
    revenue: float | None = None

    # "extra fields not permitted"
    class Config:
        extra = "forbid"


@app.post("/movies/")
async def create_movie(movie: Movie):
    movie.id = random.randint(0, 10000)
    if movie.revenue:
        return JSONResponse(status_code=status.HTTP_406_NOT_ACCEPTABLE, content={"message": "Let me do the counting for you :)"})
    if movie.audience and movie.ticket_price:
        movie.revenue = movie.audience * movie.ticket_price
    return movie

"""""""""""""""""""""
REQUEST BODY + PATH & QUERY PARAMS

- tunnistaa paramit mitä ovatkaan
"""


@app.put("/movies/{movie_id}")
async def edit_movie(movie_id: int, movie: Movie, q: str | None = None):
    result = {"movie_id": movie_id, **movie.dict()}
    # ** = ? -- ei ainakaan herjaa: "Dictionary entries must contain key/value pairs"
    if q:
        result.update({"query": q})
    return result


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Query Parameters and String Validations
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


@app.get("/validated-query")
# maksimi query param siis 3-10 pitkä, ja alettava 'id-'
# wanhemassa pythonissa siis näin: Annotated[Union[str, None]]
# ilman Annotated: (q: str | None = Query(default=None, max_length=50)
# molemmissa None tekee siitä unrequired -- Annotated suositeltu, koska syitä xyz
async def validated(q: Annotated[str | None, Query(min_length=3, max_length=10, regex="^id-")] = None):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

"""""
default arvot
- jos on niin defaulttaa määritettyy arvoon, ja jos ei niin on pakollinen:
     - testaa poistamalla = "fixedquery"
     - vaihtehtoinen tapa: (q: Annotated[str, Query(min_length=3)] = ...)
     - Jälkimmäisen käyttökohde esim: jos halutaan queryn arvo edes muodossa None: (q: Annotated[str | None, Query(min_length=3)] = ...):
       (miten tuo edes eroaa jos tota =... ei ole \_('_')_/)
    - kolmen pisteen tilalla voi käyttää Required -taikasanaa (from pydantic import Required)
"""


@app.get("/validated-query-defaults")
async def validated_defaults(q: Annotated[str | None, Query(min_length=3)] = ...):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results

"""
Query parameter list / multiple values

    - tarttee list[str] + Query(), koska muuten loput tulkitaan request bodynä
    - vois myös olla pelkkä list ilman str määritystä: Annotated[list, Query()] = []

    - defaultit voi asettaa array-tyylillä: (q: Annotated[list[str], Query()] = ["foo", "bar"]):
    --> palauttaa [foo, bar] jos ei yhtään q:ta request urlissa
"""


@app.get("/query-list/")
# /query-list?q=123&q=abc&q....
async def query_list(q: Annotated[list[str] | None, Query()] = None):
    query_items = {"q": q}
    return query_items


"""
Alias parameters

    - jos query param on esim: item-query kyseessä ei ole validi pythoni muuttuja nimi
    - jos sen on oltava tuossa muodossa niiiin tämä ratkaisee.
"""


@app.get("/alias")
# /alias?item-query=123
async def alias_query(q: Annotated[str | None, Query(alias="item-query")] = None):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results


"""
Dokumentaatiohommeleita:

Declare more metadata (= OpenAPI:iin lisätietoja)
https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#declare-more-metadata

Deprecating params = varoitus doksuihin että joku vanhenee
https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#deprecating-parameters

Koko töräys esimi:
    Query(
            alias="item-query",
            title="Query string",
            description="Query string for the items to search in the database that have a good match",
            min_length=3,
            max_length=50,
            regex="^id-",
            deprecated=True,
        ),


Exclude from OpenAPI
https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#exclude-from-openapi

"""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Path Parameters and Numeric Validations

- kuten yllä, voi antaa metadataa doksuille ja yhdistää query parameihin:  item_id: Annotated[int, Path()], q: Annotated[str | None, Query()] = None,
- Järjestyksellä jolla queryt ja path paramit annetaan ei ole väliä jos Annotated käytössä, ks jos ei ym. tuosta etiäppäin:
https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/#order-the-parameters-as-you-need

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


@app.get("/path-items/{item_id}")
async def path_params(item_id: Annotated[int, Path()]):
    results = {"item_id": item_id}
    return results


"""
Number validations:
 - greater than (gt=1)
 - greater than or equal (ge=10)
 - greater than and less than or equal (ge=10, le=1000)
 - floats, greater than and less than:  Annotated[float, Path(gt=0, lt=10.5)]

"""


@app.get("/number-validation/{item_id}")
async def number_validated(item_id: Annotated[int, Path(ge=10, le=20)]):
    results = {"item_id": item_id}
    return results


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Body - Multiple parameters

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


class User(BaseModel):
    username: str
    full_name: str | None = None


@app.put("/thingy/{item_id}")
# kutsussa vähintään: { "item": {"name": "Banana", "price": 12.2}, "user": {"username": "Pertti"}, "importance": 1 }
# jostain kumman syystä tässä se hiffaa että q on query param myös ilman Query():ä: singular values are interpreted as query parameters, you don't have to explicitly add a Query
async def update_thingy(item_id: int, item: Item, user: User, importance: Annotated[int, Body(gt=0, le=5)], q: str | None = None):
    results = {"item_id": item_id, "item": item,
               "user": user, "importance": importance}
    if q:
        results.update({"q": q})
    return results


"""
 Embed a SINGLE body parameter

 - tyyppaa: embeded_item(item_id: int, item: Item):
    --> Tällöin requestin tulee olla: {"name": "Banana", "price": 12.2}
    --> embedin kanssa: {"item": {"name": "Banana", "price": 12.2}}

- jostain syystä yllä ei tartte, kun useampi sisus requestissa ..
"""


@app.put("/embeded/{item_id}")
# {"item": {"name": "Banana", "price": 12.2}}
async def embeded_item(item_id: int, item: Annotated[Item, Body(embed=True)]):
    results = {"item_id": item_id, "item": item}
    return results


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Body - Fields

- fieldille voi antaa samat paramit ja toimii kuten Query, Path tai Body, mutta importataan pydanticista fastapin sijaan
- Field(description="", title="") -- doksuja varten

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class AnotherItem(BaseModel):
    name: str
    description: str | None = Field(
        default=None, title="The description of the item", max_length=30, min_length=10
    )
    price: float = Field(gt=0)
    tax: float | None = None


@app.put("/another-item/{item_id}")
# {"item": {"name": "Banana", "price": 12.2, "description": "hello"}}
async def another_item_route(item_id: int, item: Annotated[AnotherItem, Body(embed=True)]):
    results = {"item_id": item_id, "item": item}
    return results


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

 **** Body - Nested Models *****

 - peruslista aka json array, esim (python > 3.9, muuten joutuu importtaa List from typing )
    tags: list = [],

 - typitetty lisa
    tags: list[str] = []


- vain uniikkeja stringejä --> set! (eli siis jos tags listassa duplikaatteja, menee ne kaivoon):
    tags: set[str] = set()

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class Image(BaseModel):
    url: HttpUrl  # pydantic special types and validation
    name: str


class Product(BaseModel):
    name: str
    description: str | None = None
    price: float
    tags: set[str] = set()
    # yksittäinen image --> image: Image | None = None
    # image lista:
    images: list[Image] | None = None


@app.put("/products/{item_id}")
async def update_product(item_id: int, product: Product):
    results = {"item_id": item_id, "product": product}
    return results

"""
esim ylle:
{
    "name": "Makkara",
    "price": 12.2,
    "tags": ["hk", "blue"],
    "images": [
        {"name": "kiekura-lenkki", "url": "http://www.makkara.fi"}
    ]
}
"""


"""""

Deeply nested models

esim yllä olevien jatkoksi, voi jatkaa vielä seuraavaan ja seuraavaan .....
"""""


class ShoppingBasket(BaseModel):
    name: str
    products: list[Product]


@app.post("/shopping/")
async def my_basket(shopping: ShoppingBasket):
    return shopping

"""
Tällöin kutsu esim:
{
    "name": "Pertti",
    "products": [
       {
        "name": "Makkara",
        "price": 12.2,
        "tags": ["hk", "blue"],
        "images": [
                {"name": "kiekura-lenkki", "url": "http://www.makkara.fi"}
            ]
        }
    ]
}
"""

##########

""""
Bodies of arbitrary dicts
-  kätevää jos et tiedö mitä kenttiä, attribuuttien nimiä tulee (nämä siis ennalta määrättyjä yllä olevissa pydantikilla tehdyissä classeissa)
 (tyypit tosin määritelty, kyykkää esim jos {"nimi": "Pertti"})
"""


@app.post("/index-weights/")
async def create_index_weights(weights: dict[int, float]):
    return weights


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Skipedi-skipedi:

#declare-request-example-data
* Doksukamaa, esimi responssi OpenAPI:iin ym: https://fastapi.tiangolo.com/tutorial/schema-extra-example/

* Extra Data Types, eli siis esim datetime, UUID: https://fastapi.tiangolo.com/tutorial/extra-data-types/#extra-data-types

* cookie params: https://fastapi.tiangolo.com/tutorial/cookie-params/

* header params: https://fastapi.tiangolo.com/tutorial/header-params/

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

#####

""""""""""""""""""""""""""""""""""

Response Model - Return Type

mm.
- validoi palautuvan datan
- rajaa ja filtteröi palautuvan datan
- kaataa serverin jos yrittää palauttaa jotain määrittelyn ulkopuolelta, joten varmistaa että data tulee oletetussa muodossa, eikä mitään ylimääräistä pääse vahingossa vuotamaan
- voi määrittää classien kautta kuten yllä


"""""""""""""""""""""""""""""""""


@app.post("/validated-response")
async def validated_response(param: str) -> str:
    return param


@app.get("/validated-response")
async def validated_again() -> list[str]:
    return [
        "miuku", "mauku"
    ]

"""
response_model
  - käytetään kun ei haluta palauttaa just sitä mitä classissa on määritelty
  - Ja sen kautta voi määrittää eri palautusmuodon
  - Ks. Extra / Multiple Models

tai näin:
- ei ota sisään eikä päästä ulos muuta kuin mitä on modeliin määritelty
"""


class UserOut(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None


class UserIn(UserOut):
    password: str

    # "extra fields not permitted" -- millä tämän saisi aina vakiona? :thinking-face:
    class Config:
        extra = "forbid"


@app.post("/create-user/")
async def create_user(user: UserIn) -> UserOut:
    return user

"""
tai kolmas tapa response_model_exclude={"password"} alempana
"""


"""
 Response tyyppi
 - alla olevat ok koska ne ovat Responsen "alaluokkia"
"""


@app.get("/portal")
async def get_portal(teleport: bool = False) -> Response:
    if teleport:
        return RedirectResponse(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    return JSONResponse(content={"message": "Here's your interdimensional portal."})


"""
Annotate a Response Subclass, Invalid Return Type Annotations ja Disable response model skipattu
https://fastapi.tiangolo.com/tutorial/response-model/#response_model_include-and-response_model_exclude

----

- Response Model encoding parameters: voit skipata default arvojen palautuksen response_model_exclude_unsetillä:
@app.get("/items/{item_id}", response_model=Item, response_model_exclude_unset=True)

- response_model_include and response_model_exclude:
"""


@app.post("/create-another-user/", response_model=UserIn, response_model_exclude={"password"})
async def create_another__user(user: UserIn):
    return user


@app.post("/create-one-more/", response_model=UserIn, response_model_include={"username", "email"})
async def create_another__user(user: UserIn):
    return user


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Extra / Multiple Models


Koska samalle asialle voi tarvii useamman modelin:
- käyttis: 1. joka tulee ineen, 2. joka lähtee apilta, 3. joka tallennetaan kantaan

perussetti: https://fastapi.tiangolo.com/tutorial/extra-models/#multiple-models
- alla parempi version josta poistettu duplikointi

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None


class UserRequest(UserBase):
    password: str


class UserResponse(UserBase):
    pass  # = sama kuin UserBase


class UserInDb(UserBase):
    hashed_password: str


def fake_password_hasher(password: str):
    return "supersecret " + password + "!!!"


def fake_save_user(user_request: UserRequest):
    hash = fake_password_hasher(user_request.password)
    user_in_db = UserInDb(**user_request.dict(), hashed_password=hash)
    print("User saved! ..not really")
    return user_in_db


@app.post("/create-fake-user", response_model=UserResponse)
async def create_fake_user(user_request: UserRequest):
    user_saved = fake_save_user(user_request)
    return user_saved

"""
    **user_request.dict() -- muuntaa dict:n modelin datasta (tekee vähän kuin jsonin)

    esim:
    user_in = UserIn(username="john", password="secret", email="john.doe@example.com")
    user_dict = user_in.dict()

    print(user_dict)
    -->
    {
    'username': 'john',
    'password': 'secret',
    'email': 'john.doe@example.com',
    'full_name': None,
    }

   ----------------------- Unwrapping a dict ------------------------------

   Jos otetaan dict, ja passataan se funktioon **-merkkien kera, python "unwrappaa" sen, ja passaa suoraan key-value parit funktion parametreina 

   UserInDb(**user_in.dict(), hashed_password=hash)

   on sama kuin:
   
   UserInDB(
        username="john",
        password="secret",
        email="john.doe@example.com",
        full_name=None,
        hashed_password=saljfklashfka
    )

"""


"""
Union or anyOf

    - reponssin voi määritää olemaan jompaa kumpaa tyyppiä --> anyOf 
"""


class Vegetable(BaseModel):
    description: str
    type: str


class Potato(Vegetable):
    type = "potato"
    shape: str


class Carrot(Vegetable):
    type = "carrot"


vegetables = {
    "vegetable1": {"description": "I prefer mine smashed", "type": "potato", "shape": "round"},
    "vegetable2": {"description": "It is orange", "type": "carrot"},
}


# tässä pakko käyttää unionion vaikka olisinkin python > 3.10
@app.get("/vegetables/{veg_id}", response_model=Union[Potato, Carrot])
# /vegetables/vegetable1
async def get_veggies(veg_id: str):
    return vegetables[veg_id]


"""
    List of models

    - eli siis palauta modelin mukaisia objekteja
    - jos jotain extraa, se ei palaudu fronttiin

"""

veggies = [
    {"description": "I prefer mine smashed", "type": "potato"},
    {"description": "It is orange", "type": "carrot"}
]


@app.get("/all-veggies/", response_model=list[Vegetable])
async def all_veggies():
    return veggies

"""
Response with arbitrary dict
.. eli lennosta muoto, jossa määritellään key:n ja value:n tyyppi
"""


@app.get("/keyword-weights/", response_model=dict[str, float])
async def read_keyword_weights():
    return {"foo": 2.3, "bar": 3.4}


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Response status codes 
- tulee defaulttinakin mutta välillä tarvetta vekslaa
- joko suoraan numeroilla tai "shortcuttien" kautta

(ekassa muistin virkistykseksi req bodyllä ja toka query paramina)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class PseodoMeat(BaseModel):
    name: str


@app.post("/makkara/", status_code=201)
async def create_makkara(req: PseodoMeat):
    return {"makkara": req.name}


@app.post("/lenkki/", status_code=status.HTTP_201_CREATED)
async def create_lenkki(name: str):
    return {"lenkki": name}


"""
skipattu:
- form data
- request files
- request forms and files
"""


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Handling Errors

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

"""
- HTTPException 
"""

beers = {"beer1": {"label": "Rainbow Lager", "nickname": "Denakupari"}}


@app.get("/beers/{beer_id}")
# /beers/beer1
async def get_beer(beer_id: str):
    if beer_id not in beers:
        raise HTTPException(status_code=404, detail="Beer not found :(")
    return {"beer": beers[beer_id]}

"""
- add custom headers
"""

watches = {"Rolex": "Golden timepiece"}


@app.get("/watches/{watch_id}")
async def get_rolex(watch_id: str):
    if watch_id not in watches:
        raise HTTPException(
            status_code=404,
            detail="No rolex for you :(",
            headers={"X-Error": "Rolex error"}
        )
    return {"watch": watches[watch_id]}

"""
- install custom exception handlers

    - Customi exception handlerit starlettelta: https://www.starlette.io/exceptions/
    - Esim UnicornException 🐎
"""


class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name


@app.exception_handler(UnicornException)
async def unicorn_handler(request: Request, exc: UnicornException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops, {exc.name} did a poopoo"}
    )


@app.get("/unicorn/{name}")
async def read_unicorn(name: str):
    if name == 'yolo':
        raise UnicornException(name=name)
    return {"unicorn": name}


"""
- Override the default exception handlers

    - request validation exceptions (RequestValidationError) = epävalidia request dataa 
        - overridaus: importtaa RequestValidation error ja käytä @app.exception_handler(RequestValidationError) funktion dekoraattorina
        - saa automaagisesti paramsit request ja exc
        - Doksuissa kans PlainTextResponse, jonka hyötyä en ymmärrä :-D 
        https://fastapi.tiangolo.com/tutorial/handling-errors/?h=#override-request-validation-exceptions
"""


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"message": "Custom ERRRRORORORORO", "details": exc.errors()})


@app.get("/custom-exception/{item_id}")
async def read_something(item_id: int):
    return {"item_id": item_id}


"""
    - Saman voi tehdä muille, esim. HTTPException & RequestValidationError
    - Jälkimmäiseen voi tyrkätä mukaan errorin aihettaneen bodyn (!)
    - Tässä HTTPException error on Starlettelta, josta tulee suurin osa mahdollisista responsseista (Vois käyttää myös fastapi.responsea, mutta tässä niinkuin esiminä starlette) 
        - Erorna näissä kahdessa on se, että FastApin HTTPExceptioniin voi lisätä headereitä. Suositus käyttää Starlettea, koska jos joku Starletten koodista tai plugareista heittää errorit, niin custom handler pääsee siihen väliin 
"""


# @app.exception_handler(StarletteHTTPException)
# async def http_exception_handler(request, exc):
#     return JSONResponse(status_code=exc.status_code, content={"message": "Custom message", "info": exc.detail})


@app.get("/http-exception/{some_id}")
async def error_route(some_id: int):
    if some_id == 3:
        raise HTTPException(status_code=418, detail="Nope! I don't like 3.")
    return {"some_id": some_id}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body})
    )


class Something(BaseModel):
    title: str
    size: int


@app.post("/req-validation-error")
async def create_something(something: Something):
    return something


"""
    Re-use FastApi's exception handlers

    - Jos haluta käyttää FastApin defaultteja (Siis vissiin yliajaa Starletten heittämät errorit FastApin handlereilla, joissa siis etuna mm. että niihin voi työntää headerit)
    - from fastapi.exception_handlers import ...
"""


@app.exception_handler(StarletteHTTPException)
async def another_http_exception_handler(request, exc):
    print(f"OMG, an ERRRORRROR: {repr(exc)}")
    return await http_exception_handler(request, exc)


@app.get("/one-more-http-error/{item_id}")
async def another_http_error(item_id: int):
    print("HELLO")
    if item_id == 3:
        raise HTTPException(status_code=418, detail="3 again :(")
    return {"item_id": item_id}


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Path Operation Configuration 

(Siis tämä kohta koodissa: @app.post(... status_code=status.HTTP_201_CREATED))

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


"""""
 Response status code
 - eli määritä status code (siis kun onnistunut pyyntö)
"""""


@app.post("/sausage", response_model=PseodoMeat,  status_code=status.HTTP_201_CREATED)
async def create_sausage(sausage: PseodoMeat):
    return sausage

"""
 Tags + Tags with Enums + Summary and Description + Description from docstring + response description

 - eli voi lisätä tägejä (list str). Käyttötarkoitus on dokumentaatiot, jossa siitä tulee kuin otsikko reittien ylle
 - Enumit helpottaa isossa applikaatiossa näiden hallintaa
 - Summary ja description .. 
 - docstring userissa
 - tsekkaa http://localhost:8000/docs
 - myös deprecated=true --> näyttää routen harmaana doksuissa, mutta reitti edelleen toimii
"""


class Tags(Enum):
    sausages = "sausages"
    users = "users"


@app.get("/sausage-route", tags=[Tags.sausages], summary="Returns sausages", description="From this route, you will get some sausages!")
async def get_some_sausages():
    return ["HK Blue", "Lenkki"]


@app.get("/sausage-route-2", tags=[Tags.sausages], summary="Returns more sausages", description="Didn't get enough of sausages, huh?")
async def get_more_sausages():
    return ["HK Blue", "Lenkki"]


@app.get("/user-route/", tags=[Tags.users], response_description="Describe the response here :)", deprecated=True)
async def get_some_users():
    """
    Get user names (Or for a post route you can list required attributes)
    - **name**: there will be just names so the one below is just an example
    - **fake attribute**: This doesnt exist :(
    """
    return ["Rick", "Morty"]


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

JSON Compatible Encoder

    - jsonable_encoder() -- eli kun konvertoidaan esim Pydantic model johonkin JSON yhteensopivaan muotoon (dict, list, etc.)

    - Alla syntyy dict, jossa datetime on konvertoitu stringiksi. Lopputulos ei siis ole json stringi, mutta se on json yhteensopiva eli sitä voi käsitellä esim. json.dumbilla (eli siis tehdä jsoneita)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class Sport(BaseModel):
    name: str
    players: int
    timestamp: datetime
    description: str | None = None


fake_db = {}


@app.put("/sport-route/{id}")
def update_sport(id: str, sport: Sport):
    json_compatible_data = jsonable_encoder(sport)
    fake_db[id] = json_compatible_data
