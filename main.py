from fastapi import FastAPI
import uvicorn
import routers.api as api
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# css, js용
app.mount("/static", StaticFiles(directory="static"), name="static")

# router 추가
app.include_router(api.router)

@app.get("/")
def read_root():
    return { "Hello" : "World" }


# run server by 'python main.py' in windows
if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)