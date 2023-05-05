from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status, Header
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

"""""""""""""""""""""""""""""
Dependencies 
    - dependency injection: "declare things that it requires to work... [and] FastAPI will take care of doing whatever is needed to provide your code with those needed dependencies"

- First Steps
    - Create a dependency, or "dependable" -- 
    - huom: Depends():lle voi antaa vain yhden parametrin 
    - Suoritetaan ennen varsinaisen path-funktion ajamista
     
"""""""""""""""""""""""""""""

app = FastAPI()


# async def common_parameters(q: str | None, skip: int = 0, limit: int = 10):
#     return {"q": q, "skip": skip, "limit": limit}

# app.get("/items/")
# async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
#     return commons

# @app.get("/users/")
# async def read_users(commons: Annotated[dict, Depends(common_parameters)]):
#     return commons

""""""""""
    - lyhyempi tapa: muuttujan kautta

    CommonsDep = Annotated[dict, Depends(common_parameters)]
    ...
    async def read_items(commons: CommonsDep):
    ...
    
    skip: async or not to async, integrated with OpenApi jne.
    https://fastapi.tiangolo.com/tutorial/dependencies/

"""""""""


"""""""""""""""""""""""""""""

Classes as Dependencies

     - yllä siis funktio, mutta voi olla mikä kutsuttava (callable) vain

"""""""""""""""""""""""""""""

fake_db = [{"name": "Fluffy"}, {"name": "MiukuMauku"}, {"name": "Kekkonen"}]


class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 10):
        self.q = q
        self.skip = skip
        self.limit = limit


@app.get("/cats/")
# lyhyempi tapa: (commons: Annotated[CommonQueryParams, Depends()]):
async def read_cats(commons: Annotated[CommonQueryParams, Depends(CommonQueryParams)]):
    response = {}

    if commons.q:
        response.update({"q": commons.q})

    items = fake_db[commons.skip: commons.skip + commons.limit]
    response.update({"items": items})
    return response


"""""""""""""""""""""""""""""""""""""""""""""""""""""

Sub-dependencies

 - can go as deep as you need .. 

 (Oma rävellys alla, originaaal: https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/#use-the-dependency)
"""""""""""""""""""""""""""""""""""""""""""""""""""""


def query_extractor(q: str | None = None):
    return q


def query_checker(q: Annotated[str, Depends(query_extractor)]):
    try:
        if q == None or len(q) == 0:
            raise Exception("Query param missing")
        if len(q) > 10:
            raise Exception("Query too long :(")
        return q

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f'Request failed. {e}'}
        )


@app.get("/something")
async def return_query(query: Annotated[str, Depends(query_checker)]):
    return {"query": query}


"""
Using the same dependency multiple times

Jos joku dependencyistä on käytössä samassa reitissä useamman kerran, koska esim. niillä on sama "sub-dependency", FastApi osaa käyttää sen vain kerran. Jos sen haluaa blokkaa, niin use_cache=False:
    async def needy_dependency(fresh_value: Annotated[str, Depends(get_value, use_cache=False)]):
"""

"""""""""""""""""""""""""""""""""""""""""""""""""""""

Dependencies in path operation decorators

... kun et tartte dependencystä paluuarvoa, tai se ei palauta sitä

... kun niitä on useampi: dependendencies:[...]

"""""""""""""""""""""""""""""""""""""""""""""""""""""


async def verify_token(x_token: Annotated[str, Header()]):
    if x_token != 'super-secret-token':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="X-Token header invalid")


async def verify_key(x_key: Annotated[str, Header()]):
    if x_key != 'super-secret-key':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="X-Key header invalid")


@app.get("/auth-route", dependencies=[Depends(verify_token), Depends(verify_key)])
async def secret_route():
    return [{"secret": "this is very secret"}]


"""""""""""""""""""""""""""""""""""""""""""""""""""""

Global Dependencies

- käytössä kaikissa routeissa (=path operations)

- yllä olevat käyttöön näin: app = FastAPI(dependencies=[Depends(verify_token), Depends(verify_key)])

- esim. yhteen filuun, niin APIRouterin kautta: https://fastapi.tiangolo.com/tutorial/bigger-applications/#another-module-with-apirouter

"""""""""""""""""""""""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""""""""""""""""

Dependencies with yield --------------

    - esim tietokanta sessioo varten 
    - Pelkästää ennen ja yieldin yhteydessä oleva koodi lähetetään ennen responsea
    - finally suoritetaan kun vastaus on lähetetty
    - kun try mukana, voit ottaa tietokanta errorit kiinni exceptillä, finally varmistaa että kävin miten vaan niin yhteys sulkeutuu
        - Paitsi: esim HTTPExceptionin palauttaminen ei onnistu, koska "exit code" yieldin kera suoritetaan vastauksen jälkeen, kun Exception handlerit on ajettu
        - ilmeisesti käyttötarkoitus on taustahommelit, kuten tietokantayhdeyden muodostus yms. 
    
    async def get_db():
        db = DBSession()
        try:
            yield db
        finally:
            db.close()


Sub-dependencies with yield ---------
ks: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#sub-dependencies-with-yield

+ normi-dependencyjä ja yieldin kanssa voi sekoitella jne. 
            
"""""""""""""""""""""""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""""""""""""""""

Context managers -----------------------------------------------
= Python objekteja joita voi käyttää with-taikasanan kanssa

esim file:

    with open("./somefile.txt") as f:
        contents = f.read()
        print(contents)

Using context managers in dependencies with yield ----------------

= luot luokan, jossa kaksi metodia __enter__() ja __exit__()

- voi käyttää dependencien sisällä yieldin kera with tai async with -määritysten kanssa:


            class MySuperContextManager:
                def __init__(self):
                    self.db = DBSession()

                def __enter__(self):
                    return self.db

                def __exit__(self, exc_type, exc_value, traceback):
                    self.db.close()


            async def get_db():
                with MySuperContextManager() as db:
                    yield db


"""""""""""""""""""""""""""""""""""""""""""""""""""""
