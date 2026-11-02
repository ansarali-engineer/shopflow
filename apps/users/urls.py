"""User URL routes."""
from django.urls import path
from apps.users.views import (
    admin_user_list, admin_user_detail,
    my_profile, update_my_profile, addresses, address_detail,
)

urlpatterns = [
    path("", admin_user_list),
    path("<int:user_id>/", admin_user_detail),
    path("me/", my_profile),
    path("me/update/", update_my_profile),
    path("me/addresses/", addresses),
    path("me/addresses/<int:address_id>/", address_detail),
]
