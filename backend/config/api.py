from ninja import NinjaAPI
from ninja.security import django_auth

from apps.companies.api import router as companies_router
from apps.core.api import router as core_router
from apps.library.api import router as library_router

api = NinjaAPI(title="Apulia Intelligence API", version="1.0.0", auth=django_auth)
api.add_router("/", core_router)
api.add_router("/", companies_router)
api.add_router("/", library_router)
