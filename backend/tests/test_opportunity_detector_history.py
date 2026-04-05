"""Tests for the opportunity_detector history and follow endpoints.

Covers: save_opportunity_to_db persistence, GET /history (sorting, pagination,
filters by asset_type and days), PATCH /{id}/follow toggle, auth enforcement.

All DB tests use the shared in-memory SQLite session from conftest.py.
"""
from __future__ import annotations

import pytest


class TestSaveOpportunityToDB:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_persists_all_fields(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_handles_none_recommendation(self):
        pass


class TestHistoryEndpoint:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_returns_sorted_by_detected_at_desc(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_returns_total_count(self):
        pass


class TestHistoryFilters:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_filter_by_asset_type_acao(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_filter_by_asset_type_crypto(self):
        pass


class TestHistoryDaysFilter:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_days_7_excludes_old(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_days_default_30(self):
        pass


class TestFollowEndpoint:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_toggles_followed_flag(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_returns_404_for_nonexistent(self):
        pass


class TestAuthRequired:
    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_history_unauthenticated_returns_401(self):
        pass

    @pytest.mark.skip(reason="stub — implement in Task 7")
    def test_follow_unauthenticated_returns_401(self):
        pass
