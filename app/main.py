from fastapi import FastAPI
from app.routers import auth, content
from app.redis_client import redis_client


app = FastAPI(title="Redis Auth System")


app.include_router(auth.router)
app.include_router(content.router)


@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()


@app.get("/")
async def root():
    return {"message": "Auth system is running"}