from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('reports.urls', 'reports'), namespace='reports')),  # Dashboard/Reports root view
    path('rooms/', include(('rooms.urls', 'rooms'), namespace='rooms')),
    path('residents/', include(('residents.urls', 'residents'), namespace='residents')),
    path('billing/', include(('billing.urls', 'billing'), namespace='billing')),
    path('reports/', include(('reports.urls', 'reports'), namespace='reports_page')),
]