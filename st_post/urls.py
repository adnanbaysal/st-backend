from rest_framework import routers

from .api import PostViewSet

router = routers.DefaultRouter()

router.register("", PostViewSet, basename="st_post")

urlpatterns = router.urls
