from django.contrib import admin

from .models import Consecutivo, Empleado, ItemRemision, Proyecto, Remision

admin.site.register(Consecutivo)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "cedula", "activo"]
    search_fields = ["nombre", "cedula"]


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]


@admin.register(Remision)
class RemisionAdmin(admin.ModelAdmin):
    list_display = ["numero", "proyecto", "recibida_por", "estado", "creada_en"]
    list_filter = ["estado", "proyecto"]
    readonly_fields = ["numero", "estado", "firmada_en"]

    def has_change_permission(self, request, obj=None):
        if obj and obj.estado != Remision.Estado.BORRADOR:
            return False  # solo se editan borradores
        return super().has_change_permission(request, obj)


@admin.register(ItemRemision)
class ItemRemisionAdmin(admin.ModelAdmin):
    list_display = ["remision", "material", "cantidad"]
    autocomplete_fields = ["material"]