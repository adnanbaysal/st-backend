from rest_framework import routers

from .api import PostLikeViewSet, PostViewSet

router = routers.DefaultRouter()

router.register("create", PostViewSet, basename="st_post")
router.register("like", PostLikeViewSet, basename="st_post_like")

urlpatterns = router.urls
