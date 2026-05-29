from django.urls import path
from pages.views import PageDetailView

app_name = 'pages'

urlpatterns = [
    path('<slug:slug>/<str:lang>/', PageDetailView.as_view(), name='page-detail'),
]
