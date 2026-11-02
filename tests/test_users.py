"""Tests for administrator user-management endpoints."""
import pytest

pytestmark = pytest.mark.django_db


class TestAdminUserManagement:
    def test_user_directory_requires_admin(self, client, auth_client):
        assert client.get("/api/v1/users/").status_code == 401
        assert auth_client.get("/api/v1/users/").status_code == 403

    def test_admin_lists_users_without_password_hashes(
        self, admin_client, test_user, test_seller, test_admin
    ):
        response = admin_client.get("/api/v1/users/?page=1&page_size=10")

        assert response.status_code == 200
        assert response.data["meta"]["total"] == 3
        assert {user["id"] for user in response.data["data"]} == {
            test_user["id"], test_seller["id"], test_admin["id"]
        }
        assert all("password_hash" not in user for user in response.data["data"])

    def test_admin_filters_users(self, admin_client, test_user, test_seller):
        response = admin_client.get("/api/v1/users/?role=seller")

        assert response.status_code == 200
        assert [user["id"] for user in response.data["data"]] == [
            test_seller["id"]
        ]
        assert test_user["id"] not in [
            user["id"] for user in response.data["data"]
        ]

    def test_admin_gets_and_updates_user(self, admin_client, test_user):
        detail = admin_client.get(f"/api/v1/users/{test_user['id']}/")
        assert detail.status_code == 200
        assert detail.data["data"]["email"] == "testuser@shopflow.test"
        assert "password_hash" not in detail.data["data"]

        response = admin_client.patch(
            f"/api/v1/users/{test_user['id']}/",
            {"first_name": "Changed", "role": "seller"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["data"]["first_name"] == "Changed"
        assert response.data["data"]["role"] == "seller"

    def test_admin_rejects_duplicate_email(self, admin_client, test_user, test_seller):
        response = admin_client.patch(
            f"/api/v1/users/{test_user['id']}/",
            {"email": test_seller["email"]},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "DUPLICATE_EMAIL"

    def test_admin_cannot_remove_own_access(self, admin_client, test_admin):
        response = admin_client.patch(
            f"/api/v1/users/{test_admin['id']}/",
            {"status": "suspended"},
            format="json",
        )
        assert response.status_code == 400

        response = admin_client.delete(f"/api/v1/users/{test_admin['id']}/")
        assert response.status_code == 400

    def test_delete_deactivates_user_without_removing_record(
        self, admin_client, test_user, db_cursor
    ):
        response = admin_client.delete(f"/api/v1/users/{test_user['id']}/")

        assert response.status_code == 200
        assert response.data["data"]["status"] == "deleted"
        db_cursor.execute(
            "SELECT status FROM users WHERE id = %s", [test_user["id"]]
        )
        assert db_cursor.fetchone()[0] == "deleted"
