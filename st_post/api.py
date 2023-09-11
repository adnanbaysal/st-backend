from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Post, PostLike
from .serializers import PostLikeSerializer, PostSerializer


class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if self.request.user != instance.user:
            raise ValidationError({"error": "cannot_delete_other_users_posts"})

        instance.delete()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if request.user != instance.user:
            raise ValidationError({"error": "cannot_update_other_users_posts"})

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class PostLikeViewSet(ModelViewSet):
    queryset = PostLike.objects.all()
    serializer_class = PostLikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination

    def create(self, request, *args, **kwargs):
        if PostLike.objects.filter(
            user=self.request.user, post_id=request.data["post"]
        ).exists():
            raise ValidationError({"error": "user_already_liked_the_post"})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if self.request.user != instance.user:
            raise ValidationError({"error": "cannot_delete_other_users_likes"})

        instance.delete()

    def perform_update(self, serializer):
        raise ValidationError({"error": "like_update_not_allowed"})
