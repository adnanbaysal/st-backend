from http import HTTPStatus

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from ..api import PostLikeViewSet, PostViewSet
from ..models import Post, PostLike


@pytest.fixture
def db_user_1():
    return User.objects.create_user(
        username="user1@domain.com", password="password", id=1
    )


@pytest.mark.django_db
class TestPostViewSet:
    factory = APIRequestFactory()

    def test_create_post(self, db_user_1):
        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.post(
            "api/v1/post", data={"text": "hello world"}, format="json"
        )
        force_authenticate(request, db_user_1, access_token)

        view = PostViewSet.as_view({"post": "create"})

        response = view(request)
        assert response.status_code == HTTPStatus.CREATED.value
        assert response.data["text"] == "hello world"
        assert response.data["user"] == db_user_1.id

    def test_list_post(self, db_user_1):
        for i in range(3):
            Post.objects.create(user=db_user_1, text=f"hello {i}")

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.get("api/v1/post")
        force_authenticate(request, db_user_1, access_token)

        view = PostViewSet.as_view({"get": "list"})

        response = view(request)

        assert response.status_code == HTTPStatus.OK.value
        assert response.data["count"] == 3

        for i, result in enumerate(response.data["results"]):
            assert result["text"] == f"hello {i}"
            assert result["user"] == db_user_1.id

    def test_retrieve_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.get("api/v1/post")
        force_authenticate(request, db_user_1, access_token)

        view = PostViewSet.as_view({"get": "retrieve"})

        response = view(request, pk=post.id)

        assert response.status_code == HTTPStatus.OK.value
        assert response.data["text"] == "hello"
        assert response.data["user"] == db_user_1.id

    def test_patch_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.patch(
            "api/v1/post", data={"text": "world"}, format="json"
        )
        force_authenticate(request, db_user_1, access_token)

        view = PostViewSet.as_view({"patch": "partial_update"})

        response = view(request, pk=post.id)

        assert response.status_code == HTTPStatus.OK.value
        assert response.data["text"] == "world"
        assert response.data["user"] == db_user_1.id

    def test_delete_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.delete("api/v1/post")
        force_authenticate(request, db_user_1, access_token)

        view = PostViewSet.as_view({"delete": "destroy"})

        response = view(request, pk=post.id)

        assert response.status_code == HTTPStatus.NO_CONTENT.value
        assert len(Post.objects.all()) == 0

    def test_cannot_delete_others_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        db_user_2 = User.objects.create_user(
            username="user2@domain.com", password="password", id=2
        )

        access_token = RefreshToken.for_user(db_user_2).access_token
        request = self.factory.delete("api/v1/post")
        force_authenticate(request, db_user_2, access_token)

        view = PostViewSet.as_view({"delete": "destroy"})

        response = view(request, pk=post.id)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert "cannot_delete_other_users_posts" in str(response.data["error"])

    def test_cannot_update_others_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        db_user_2 = User.objects.create_user(
            username="user2@domain.com", password="password", id=2
        )

        access_token = RefreshToken.for_user(db_user_2).access_token
        request = self.factory.patch("api/v1/post")
        force_authenticate(request, db_user_2, access_token)

        view = PostViewSet.as_view({"patch": "partial_update"})

        response = view(request, pk=post.id)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert "cannot_update_other_users_posts" in str(response.data["error"])


@pytest.mark.django_db
class TestPostLikeViewSet:
    factory = APIRequestFactory()

    def test_create_like(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.post(
            "api/v1/like", data={"post": post.id}, format="json"
        )
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"post": "create"})

        response = view(request)
        assert response.status_code == HTTPStatus.CREATED.value
        assert response.data["post"] == post.id
        assert response.data["user"] == db_user_1.id

    def test_one_user_cannot_create_multiple_like_on_the_same_post(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        PostLike.objects.create(user=db_user_1, post=post)

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.post(
            "api/v1/like", data={"post": post.id}, format="json"
        )
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"post": "create"})

        response = view(request)
        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert "user_already_liked_the_post" in str(response.data["error"])

    def test_list_like(self, db_user_1):
        posts = []
        for i in range(3):
            posts.append(Post.objects.create(user=db_user_1, text=f"hello {i}"))
            PostLike.objects.create(user=db_user_1, post=posts[-1])

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.get("api/v1/like")
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"get": "list"})

        response = view(request)

        assert response.status_code == HTTPStatus.OK.value
        assert response.data["count"] == 3

        for i, result in enumerate(response.data["results"]):
            assert result["post"] == posts[i].id
            assert result["user"] == db_user_1.id

    def test_retrieve_like(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        post_like = PostLike.objects.create(user=db_user_1, post=post)

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.get("api/v1/like")
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"get": "retrieve"})

        response = view(request, pk=post_like.id)

        assert response.status_code == HTTPStatus.OK.value
        assert response.data["post"] == post.id
        assert response.data["user"] == db_user_1.id

    def test_patch_like_not_allowed(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        post_2 = Post.objects.create(user=db_user_1, text="world")
        post_like = PostLike.objects.create(user=db_user_1, post=post)

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.patch(
            "api/v1/like", data={"post": post_2.id}, format="json"
        )
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"patch": "partial_update"})

        response = view(request, pk=post_like.id)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert "like_update_not_allowed" in str(response.data["error"])

    def test_delete_like(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        post_like = PostLike.objects.create(user=db_user_1, post=post)

        access_token = RefreshToken.for_user(db_user_1).access_token
        request = self.factory.delete("api/v1/like")
        force_authenticate(request, db_user_1, access_token)

        view = PostLikeViewSet.as_view({"delete": "destroy"})

        response = view(request, pk=post_like.id)

        assert response.status_code == HTTPStatus.NO_CONTENT.value
        assert len(PostLike.objects.all()) == 0

    def test_cannot_delete_others_like(self, db_user_1):
        post = Post.objects.create(user=db_user_1, text="hello")
        post_like = PostLike.objects.create(user=db_user_1, post=post)
        db_user_2 = User.objects.create_user(
            username="user2@domain.com", password="password", id=2
        )

        access_token = RefreshToken.for_user(db_user_2).access_token
        request = self.factory.delete("api/v1/like")
        force_authenticate(request, db_user_2, access_token)

        view = PostLikeViewSet.as_view({"delete": "destroy"})

        response = view(request, pk=post_like.id)

        assert response.status_code == HTTPStatus.BAD_REQUEST.value
        assert "cannot_delete_other_users_likes" in str(response.data["error"])
