from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()


local_origin = ["http://localhost:3000/"]
dev_origin = ["https://www.dev.example.com"]
prod_origin = ["https//www.example.com"]

env = os.getenv('ENV', 'local') 
origins = local_origin

if env == 'prod':
    origins = prod_origin
elif env == 'dev':
    origins = dev_origin

print("ENV:", env, "\nALLOWED ORIGINS: ", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # ["GET", "POST" ...]
    allow_headers=["*"]
)

@app.get("/")
async def main():
    return {"message": "Hello World"}

"""
ks: https://fastapi.tiangolo.com/tutorial/cors/
- esim. allow_origin_regex 
ym ym

"""
