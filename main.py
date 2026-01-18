from fastapi import FastAPI
import uvicorn
import routers.api as api
import routers.search as search
import routers.menu as menu
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# css, js용
app.mount("/static", StaticFiles(directory="static"), name="static")

# router 추가
app.include_router(api.router)
app.include_router(search.router)
app.include_router(menu.router)


# run server by 'python main.py' in windows
if __name__ == '__main__':
    #uvicorn.run('main:app', reload=True)
    uvicorn.run('main:app', host="0.0.0.0", port=80, reload=True)