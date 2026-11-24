from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("remisiones", views.RemisionViewSet, basename="remision")
router.register("proyectos", views.ProyectoViewSet, basename="proyecto")
router.register("empleados", views.EmpleadoViewSet, basename="empleado")

urlpatterns = [
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("resumen/", views.resumen),
    path("verificar/<uuid:pk>/", views.verificar),
    path("herramientas/pendientes/", views.HerramientasPendientesView.as_view()),
    path("herramientas/pendientes/excel/", views.HerramientasPendientesExcelView.as_view()),
    path("items/<int:pk>/devolver/", views.DevolverItemView.as_view()),
] + router.urls
