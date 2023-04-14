from enum import Enum
import random
from string import Template
from fastapi import FastAPI, status, Query, Path
from fastapi.responses import JSONResponse
from typing import Union
from pydantic import BaseModel
from typing import Annotated

app = FastAPI()

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
 - greater than or equal (ge=10)
 - greater than and less than or equal (ge=10, le=1000)
 - floats, greater than and less than:  Annotated[float, Path(gt=0, lt=10.5)]

"""


@app.get("/number-validation/{item_id}")
async def number_validated(item_id: Annotated[int, Path(ge=10, le=20)]):
    results = {"item_id": item_id}
    return results
