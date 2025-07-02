from typing import Optional
import uvicorn
from fastapi import FastAPI, File, UploadFile
import routers.api as api

app = FastAPI()

# router 추가
app.include_router(api.router)

@app.get("/")
def read_root():
    return { "Hello" : "World" }


# run server by 'python main.py' in windows
if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)

# TODO: 현재 하는 것 https://fastapi.tiangolo.com/ko/tutorial/request-files/#file upload file 만들기