from typing import Optional
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return { "Hello" : "World" }


# run server by 'python main.py' in windows
if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)