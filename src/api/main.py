from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from src.api.auth.routers import router as auth_router
from src.api.feedback.routers import router as feedback_router
from src.api.rag.routers import router as rag_router  # ekledik!

app = FastAPI()

app.include_router(auth_router, prefix="/auth")
app.include_router(feedback_router, prefix="/feedback")
app.include_router(rag_router)

# 🔐 Swagger'da Bearer Auth desteği için:
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LexAI API",
        version="1.0.0",
        description="JWT authenticated API",
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
            method.setdefault("security", []).append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
