from django.urls import path

from authentication.oauth import endpoints

app_name = "oauth"

urlpatterns = [
    path("authorize", endpoints.authorize, name="authorize"),
    path("token", endpoints.token, name="token"),
    path("register", endpoints.register, name="register"),
    path("introspect", endpoints.introspect, name="introspect"),
    path("revoke", endpoints.revoke, name="revoke"),
]
