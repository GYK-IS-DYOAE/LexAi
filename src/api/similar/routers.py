from fastapi import APIRouter, Depends, HTTPException, status
from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.models.similar.similar_schemas import SimilarRequest, SimilarResponse
from src.models.similar.similar_service import find_similar_and_laws

router = APIRouter(
    prefix="/similar",
    tags=["Similar Cases"]
)


@router.post("/analyze", response_model=SimilarResponse, summary="Find similar cases and related laws")
def analyze_similar_cases(
    request: SimilarRequest,
    user: User = Depends(get_current_user)  # token doğrulama
):
    """
    Kullanıcının metnine göre hibrit arama yapar ve
    benzer davaları + ilgili kanun maddelerini döner.
    """
    try:
        response = find_similar_and_laws(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hibrit arama sırasında hata oluştu: {str(e)}"
        )
