from fastapi import FastAPI
from typing import Dict
app = FastAPI()

@app.get("/welcome")
def welcome() -> Dict[str, str]:
    """summary

    Returns
    -------
    Dict[str, str]
        Welcome message to server
    """
    return {"message":"Hello World final"}