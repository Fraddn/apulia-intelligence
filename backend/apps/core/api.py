import os

from ninja import Router, Schema

router = Router(tags=["core"])


class HealthOut(Schema):
    status: str
    version: str


@router.get("/health", response=HealthOut, auth=None)
def health(request):
    return {"status": "ok", "version": os.environ.get("APP_VERSION", "dev")}
