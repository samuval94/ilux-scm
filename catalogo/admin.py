from django.contrib import admin

from .models import Grupo, Material


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "grupo", "unidad", "tipo", "activo"]
    list_filter = ["tipo", "unidad", "activo", "grupo"]
    search_fields = ["codigo", "nombre"]