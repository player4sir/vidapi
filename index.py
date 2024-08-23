from fastapi import FastAPI

app = FastAPI()

@app.get("/api/test")
async def test():
    return {"message": "API is working!"}

# 保留 handler 为 app，确保 Vercel 能正确处理
handler = app
