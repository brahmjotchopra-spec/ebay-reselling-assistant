import csv
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import ebay_bot as bot
import ebay_client as client


DATE = "2026-11-07"


def approved():
    return {"sku": "TEST-1", "approved_for_unpublished_offer": True, "condition": "NEW",
            "category_id": "262204", "price_gbp": "11.49", "title": "Sample",
            "description": "Sample description", "commercial_review": {
                "verified": True, "checked_on": DATE, "stock": 1, "wholesale_inc_vat": "4.79",
                "delivery_inc_vat": "0", "supplier_payment_fee": "0.41", "reserve_gbp": "0.58",
                "insertion_ex_vat": "0.30", "per_order_ex_vat": "0.40", "ebay_percent": "9.85",
                "fee_vat_percent": "20", "supplier_url": "https://example.com/supplier",
                "delivery_terms": "UK mainland", "demand_url": "https://example.com/comparable"}}


class ReviewTests(unittest.TestCase):
    def test_margin_and_cutoff(self):
        row = approved()
        self.assertEqual(bot.unit_margin(Decimal("11.49"), row["commercial_review"]),
                         (Decimal("5.20"), Decimal("2.20"), Decimal("3.51")))
        row["commercial_review"]["reserve_gbp"] = "0.59"
        self.assertEqual(bot.prepare([row], DATE), ([row], []))
        row["commercial_review"]["reserve_gbp"] = "0.60"
        self.assertFalse(bot.prepare([row], DATE)[0])

    def test_approval_is_boolean_and_stock_must_be_current(self):
        for changes in [{"verified": False}, {"stock": 0}, {"checked_on": "2026-11-06"},
                        {"delivery_terms": ""}]:
            row = approved()
            row["commercial_review"].update(changes)
            self.assertFalse(bot.prepare([row], DATE)[0])
        row["approved_for_unpublished_offer"] = "true"
        self.assertEqual(bot.review_item(row, DATE), "no draft approval")

    def test_duplicate_and_total_budget(self):
        with self.assertRaisesRegex(client.DraftError, "duplicate"):
            bot.prepare([approved(), approved()], DATE)
        rows = [dict(approved(), sku=f"TEST-{n}") for n in range(10)]
        with self.assertRaisesRegex(client.DraftError, "budget"):
            bot.prepare(rows, DATE)

    def test_decimal_inputs(self):
        for price in ("NaN", "1E99", "-1", "12.222", True):
            with self.assertRaises(client.DraftError):
                bot.prepare([dict(approved(), price_gbp=price)], DATE)

    def test_csv_contains_only_drafts_and_no_stock_promise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.csv"
            bot.write_csv(path, [approved()])
            with path.open(encoding="utf-8-sig", newline="") as source:
                _, header, row = csv.reader(source)
            self.assertEqual(header, bot.CSV_HEADER)
            self.assertEqual(row[:3], ["Draft", "DRAFT-TEST-1", "262204"])
            self.assertEqual(row[6], "")
            with self.assertRaises(FileExistsError):
                bot.write_csv(path, [approved()])

    def test_preview_and_empty_apply_never_authenticate(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(bot, "get_token") as token:
            path = Path(tmp) / "empty.json"
            path.write_text("[]")
            for flag in ([], ["--create-unpublished"]):
                with patch("sys.argv", ["cli", "--file", str(path), *flag]), redirect_stdout(io.StringIO()):
                    self.assertEqual(bot.main(), 0)
            token.assert_not_called()


class OfferTests(unittest.TestCase):
    def setUp(self):
        self.inventory, self.offer = bot.payloads(approved())
        self.remote_item = dict(self.inventory, sku=self.offer["sku"])
        self.remote_offer = dict(self.offer, offerId="123", status="UNPUBLISHED")
        self.api = Mock()
        self.api.item.return_value = None
        self.api.offers.return_value = []
        self.api.create_offer.return_value = "123"
        self.api.offer.return_value = self.remote_offer

    def ensure(self):
        return bot.ensure_draft(self.api, self.inventory, self.offer)

    def test_create_then_retry_is_read_only(self):
        self.assertEqual(self.ensure(), ("created and verified", "123"))
        self.api.create_item.assert_called_once()
        self.api.item.return_value = self.remote_item
        self.api.offers.return_value = [self.remote_offer]
        self.assertEqual(self.ensure(), ("already verified", "123"))
        self.api.create_item.assert_called_once()
        self.api.create_offer.assert_called_once()

    def test_recover_after_interrupted_post(self):
        self.api.create_offer.side_effect = client.DraftError("timeout")
        with self.assertRaises(client.DraftError):
            self.ensure()
        self.api.item.return_value = self.remote_item
        self.api.create_offer.side_effect = None
        self.assertEqual(self.ensure()[1], "123")
        self.api.create_item.assert_called_once()

    def test_foreign_inventory_or_published_offer_is_untouched(self):
        changed = deepcopy(self.remote_item)
        changed["product"]["title"] = "Existing live title"
        self.api.item.return_value = changed
        with self.assertRaises(client.DraftError):
            self.ensure()
        self.api.item.return_value = self.remote_item
        for status in ("PUBLISHED", None):
            self.api.offers.return_value = [dict(self.remote_offer, status=status)]
            with self.assertRaises(client.DraftError):
                self.ensure()
        self.api.create_item.assert_not_called()
        self.api.create_offer.assert_not_called()

    def test_offer_mismatch_not_reported_as_success(self):
        self.api.offer.return_value = dict(self.remote_offer, categoryId="999")
        with self.assertRaisesRegex(client.DraftError, "differs"):
            self.ensure()

    def test_unknown_api_error_is_not_treated_as_missing(self):
        api = client.Inventory("sentinel")
        with patch.object(api, "_request", side_effect=client.ApiError(403, {25713})):
            with self.assertRaises(client.ApiError):
                api.offers("test")
        with patch.object(api, "_request", side_effect=client.ApiError(404, {25713})):
            self.assertEqual(api.offers("test"), [])


class CredentialTests(unittest.TestCase):
    def test_check_never_echoes_token_or_inventory(self):
        secret = "sensitive-test-token"
        output = io.StringIO()
        with patch.dict(os.environ, {client.ACCESS_KEY: secret}, clear=True), \
                patch("sys.argv", ["cli", "--check-credentials"]), \
                patch.object(client, "request_json", return_value={"inventoryItems": ["confidential"]}) as req, \
                redirect_stdout(output):
            self.assertEqual(bot.main(), 0)
        self.assertEqual(req.call_args.args[0].get_method(), "GET")
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn("confidential", output.getvalue())

    def test_missing_and_partial_secrets_do_not_contact_ebay(self):
        with patch.dict(os.environ, {"EBAY_CLIENT_ID": "example"}, clear=True), \
                patch.object(client, "request_json") as req, patch("sys.argv", ["cli", "--check-credentials"]), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(bot.main(), 1)
            req.assert_not_called()

    def test_refresh_requests_only_inventory_scope(self):
        values = dict(zip(client.REFRESH_KEYS, ["app", "secret", "refresh"]))
        with patch.dict(os.environ, values, clear=True), \
                patch.object(client, "request_json", return_value={"access_token": "issued"}) as req:
            self.assertEqual(client.get_token(), "issued")
        self.assertIn(b"sell.inventory", req.call_args.args[0].data)
        self.assertNotIn(b"sell.account", req.call_args.args[0].data)
