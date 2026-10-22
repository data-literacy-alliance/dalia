from django.urls import path, re_path
from website import views

urlpatterns = [
    path("", views.root_redirect),
    re_path(r"^(?P<lang>en|de)(?:/(?P<path>.*?))?/?$", views.page_view),
]
