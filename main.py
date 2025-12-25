from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from database.connection import init_db
from routes.users import user_router
from routes.events import event_router

app = FastAPI(
    title="Soulmate API",
    description="API for Soulmate - Find Your Match application",
    version="1.0.0"
)


@app.on_event("startup")
def startup_event():
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return FileResponse("static/index.html")

app.include_router(user_router)
app.include_router(event_router, prefix="/event")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )