from django.contrib import admin

from .models import Devolucion, Empleado, Firma, ItemRemision, Proyecto, Remision


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "cedula", "activo"]
    search_fields = ["nombre", "cedula"]


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]


class ItemInline(admin.TabularInline):
    model = ItemRemision
    extra = 0
    readonly_fields = ["material", "cantidad", "observacion", "devolver_antes_de"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Remision)
class RemisionAdmin(admin.ModelAdmin):
    list_display = ["numero_formato", "proyecto", "recibida_por", "entregada_por", "estado", "creada_en"]
    list_filter = ["estado", "proyecto"]
    search_fields = ["numero", "proyecto__nombre", "recibida_por__nombre"]
    readonly_fields = [f.name for f in Remision._meta.fields]
    inlines = [ItemInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Firma)
admin.site.register(Devolucion)
