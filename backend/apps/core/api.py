from django.conf import settings
from ninja import Router, Schema

router = Router(tags=["core"])


class HealthOut(Schema):
    status: str
    version: str


@router.get("/health", response=HealthOut, auth=None)
def health(request):
    return {"status": "ok", "version": settings.APP_VERSION}
