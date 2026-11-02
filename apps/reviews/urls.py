"""Review URL routes."""
from django.urls import path
from apps.reviews.views import create_review_view, product_reviews

urlpatterns = [
    path("", create_review_view),
    path("product/<int:product_id>/", product_reviews),
]
