import uvicorn
from fastapi import FastAPI, HTTPException
from src.common.exception import global_err_handler, http_err_handler
from src.config.settings import settings
from src.modules.users.user_controller import router as user_router

app = FastAPI(title=settings.app_name)

app.include_router(user_router)

def dev():
    uvicorn.run("src.main:app", reload=True, host="0.0.0.0", port=8106)

def prod():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, workers=4, log_level="warning")

app.add_exception_handler(HTTPException, http_err_handler)
app.add_exception_handler(Exception, global_err_handler)