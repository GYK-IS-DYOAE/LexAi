import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from src.api.conversation.routers import router as conversation_router



from src.api.auth.routers import router as auth_router
from src.api.feedback.routers import router as feedback_router
from src.api.rag.routers import router as rag_router
from src.api.similar.routers import router as similar_router

app = FastAPI(title="LexAI API", version="1.0.0", description="JWT Authenticated API")

# ✅ CORS MIDDLEWARE (Frontend erişimi için)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Router'lar
app.include_router(auth_router)
app.include_router(feedback_router)
app.include_router(rag_router)
app.include_router(similar_router)
app.include_router(conversation_router)

# ✅ Custom OpenAPI (Swagger için JWT butonu)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
