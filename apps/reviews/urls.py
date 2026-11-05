"""Review URL routes."""
from django.urls import path
from apps.reviews.views import create_review_view, product_reviews, moderate_review, all_reviews

urlpatterns = [
    path("", create_review_view),           # POST  (customer create) / GET (admin list)
    path("admin/", all_reviews),            # GET   admin all reviews
    path("product/<int:product_id>/", product_reviews),
    path("<int:review_id>/moderate/", moderate_review),  # PATCH admin moderate
]
