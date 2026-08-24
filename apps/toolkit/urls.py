from django.urls import path

from .views import HealthView, RewriteView, SummarizeView, TranslateView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("summarize/", SummarizeView.as_view(), name="summarize"),
    path("rewrite/", RewriteView.as_view(), name="rewrite"),
    path("translate/", TranslateView.as_view(), name="translate"),
]
