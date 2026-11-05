from ninja import NinjaAPI

from apps.companies.api import router as companies_router
from apps.core.api import router as core_router

api = NinjaAPI(title="Apulia Intelligence API", version="1.0.0")
api.add_router("/", core_router)
api.add_router("/", companies_router)
