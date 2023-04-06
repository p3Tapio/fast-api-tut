from enum import Enum
import random
from string import Template
from fastapi import FastAPI,  status
from fastapi.responses import JSONResponse
from typing import Union
from pydantic import BaseModel

app = FastAPI()

# alkuun käytetty Union[] on python < 3.10 version takia, myöhempi | toimii > 3.10:ssä


@app.get("/")
async def root():
    return {"message": "Hello World"}


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


"""""""""""""""""""""
REQUEST BODY

Validointi-ilon lisäksi, class / Pydantic BaseModel niin VSC osaa ehdottaa attribuutit 
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
