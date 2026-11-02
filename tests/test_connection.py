"""Database connection and query helper tests."""
import pytest
from decimal import Decimal
from datetime import datetime
from database.query_helpers import (
    fetch_one, fetch_all, fetch_scalar, insert_one,
    update_or_delete, serialize_value, safe_sort_fragment, fetch_paginated,
)


class TestFetchOne:
    def test_returns_dict_when_row_exists(self, db_cursor, test_user):
        result = fetch_one("SELECT id, email FROM users WHERE id = %s", [test_user["id"]])
        assert result is not None; assert isinstance(result, dict)
        assert result["id"] == test_user["id"]; assert result["email"] == "testuser@shopflow.test"

    def test_returns_none_when_no_row(self):
        assert fetch_one("SELECT id FROM users WHERE id = %s", [99999]) is None


class TestFetchAll:
    def test_returns_list_of_dicts(self, db_cursor, test_user, test_seller):
        results = fetch_all("SELECT id, email FROM users ORDER BY id")
        assert len(results) >= 2; assert all(isinstance(r, dict) for r in results)

    def test_returns_empty_list_when_no_rows(self):
        assert fetch_all("SELECT id FROM users WHERE id = %s", [99999]) == []


class TestFetchScalar:
    def test_returns_single_value(self, test_user):
        assert fetch_scalar("SELECT COUNT(*) FROM users WHERE id = %s", [test_user["id"]]) == 1

    def test_returns_none_when_no_rows(self):
        assert fetch_scalar("SELECT id FROM users WHERE id = %s", [99999]) is None


class TestInsertOne:
    def test_returns_new_id(self, db_cursor, test_user):
        addr_id = insert_one(
            "INSERT INTO addresses (user_id, label, street_line1, city, state, postal_code, country, is_default) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [test_user["id"], "Home", "123 Main St", "Austin", "TX", "78701", "US", True],
        )
        assert isinstance(addr_id, int); assert addr_id > 0


class TestUpdateOrDelete:
    def test_update_returns_affected_count(self, test_user):
        assert update_or_delete("UPDATE users SET first_name = %s WHERE id = %s", ["Updated", test_user["id"]]) == 1

    def test_update_returns_zero_when_no_match(self):
        assert update_or_delete("UPDATE users SET first_name = %s WHERE id = %s", ["X", 99999]) == 0


class TestSerializeValue:
    def test_decimal_becomes_string(self): assert serialize_value(Decimal("19.99")) == "19.99"
    def test_none_stays_none(self): assert serialize_value(None) is None
    def test_datetime_becomes_iso(self):
        assert serialize_value(datetime(2025, 1, 15, 10, 30, 0)) == "2025-01-15T10:30:00"
    def test_int_stays_int(self): assert serialize_value(42) == 42


class TestSafeSortFragment:
    SORT_MAP = {"newest": "created_at DESC", "oldest": "created_at ASC", "name_asc": "name ASC"}
    def test_valid_sort_returns_fragment(self): assert safe_sort_fragment("newest", self.SORT_MAP) == "created_at DESC"
    def test_invalid_sort_returns_default(self): assert safe_sort_fragment("price_hack", self.SORT_MAP, default="newest") == "created_at DESC"
    def test_none_returns_default(self): assert safe_sort_fragment(None, self.SORT_MAP) == "id ASC"


class TestFetchPaginated:
    def test_returns_rows_and_total(self, db_cursor, test_user):
        for i in range(5):
            insert_one("INSERT INTO addresses (user_id, label, street_line1, city) VALUES (%s, %s, %s, %s)",
                       [test_user["id"], f"Addr{i}", f"{i} Main St", "City"])
        rows, total = fetch_paginated("SELECT id, label FROM addresses WHERE user_id = %s ORDER BY id",
                                      [test_user["id"]], page=1, page_size=3)
        assert len(rows) == 3; assert total == 5
