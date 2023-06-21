from fastapi import FastAPI, Request

import time

app = FastAPI()

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time) # tarvii X:n vissiin corssiin, muuten tsiigaa Starletten doksut 
    return response


"""
Yllä ottaa siis requestin ja välittää sen reitille, ottaa sitten kiinni response ja lisää process_time:n headeriksi

Monimutkaisempiin, ks: https://fastapi.tiangolo.com/advanced/middleware/ 

niiden lisääminen kait näin:

from fastapi import FastAPI
from unicorn import UnicornMiddleware

app = FastAPI()

app.add_middleware(UnicornMiddleware, some_config="rainbow")

"""
