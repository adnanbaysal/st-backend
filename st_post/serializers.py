from rest_framework import serializers

from .models import Post, PostLike


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")


class PostLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLike
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at")
