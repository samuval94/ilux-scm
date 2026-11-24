from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GrupoListView, ImportarCatalogoView, MaterialViewSet

router = DefaultRouter()
router.register("materiales", MaterialViewSet, basename="material")

urlpatterns = [
    path("grupos/", GrupoListView.as_view()),
    path("catalogo/importar/", ImportarCatalogoView.as_view()),
] + router.urls
