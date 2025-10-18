from fastapi import APIRouter, Depends, HTTPException, status
from src.api.auth.security import get_current_user
from src.models.auth.user_model import User
from src.models.similar.similar_schemas import SimilarRequest, SimilarResponse
from src.models.similar.similar_service import find_similar_and_laws

router = APIRouter(
    prefix="/similar",
    tags=["Similar Cases"]
)


@router.post(
    "/analyze",
    response_model=SimilarResponse,
    summary="Benzer davaları ve ilgili kanun maddelerini getir"
)
def analyze_similar_cases(
    request: SimilarRequest,
    user: User = Depends(get_current_user)
):
    """
    🔹 Kullanıcının girdiği metne göre hibrit arama (Qdrant + OpenSearch) yapar.
    🔹 En benzer davaları `karar_metni_meta` (tam karar metni) ile birlikte döner.
    🔹 Ayrıca bu davalardan çıkan kanun atıflarını derleyip `related_laws` içinde döner.

    ---
    Args:
        request (SimilarRequest): Arama sorgusu, topn, vs.
        user (User): JWT’den gelen aktif kullanıcı

    Returns:
        SimilarResponse: Benzer dava listesi + ilgili kanunlar
    """
    try:
        response = find_similar_and_laws(request)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Benzer dava bulunamadı."
            )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hibrit arama sırasında hata oluştu: {str(e)}"
        )
