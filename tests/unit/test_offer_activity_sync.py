import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from config import Config
from db_conn import MongoManager


class TestOfferActivitySync(unittest.TestCase):
  def setUp(self):
    self.manager = object.__new__(MongoManager)
    self.history = MagicMock()
    self.structured = MagicMock()
    self.mapped = MagicMock()
    self.manager.db = {
      "offers": self.history,
      "offers_structured": self.structured,
      "offers_mapped": self.mapped,
    }

    self.history.update_many.side_effect = [
      SimpleNamespace(modified_count=2),
      SimpleNamespace(modified_count=5),
    ]
    for collection in (self.structured, self.mapped):
      collection.update_many.return_value = SimpleNamespace(modified_count=2)
      collection.delete_many.return_value = SimpleNamespace(deleted_count=5)

  @patch.object(Config, "SCRAPER_ACTIVITY_SYNC_MIN_URLS", 2)
  def test_archives_inactive_offers_only_in_history_collection(self):
    synced = self.manager.sync_offer_activity(
      [" offer-2 ", "offer-1", "offer-1"],
      "offers",
      ["offers_structured", "offers_mapped"],
    )

    self.assertTrue(synced)
    self.assertEqual(self.history.update_many.call_count, 2)
    self.history.delete_many.assert_not_called()

    active_query = self.history.update_many.call_args_list[0].args[0]
    inactive_query = self.history.update_many.call_args_list[1].args[0]
    inactive_update = self.history.update_many.call_args_list[1].args[1]
    self.assertEqual(active_query, {"url": {"$in": ["offer-1", "offer-2"]}})
    self.assertEqual(inactive_query, {"url": {"$nin": ["offer-1", "offer-2"]}})
    self.assertFalse(inactive_update["$set"]["is_active"])

    for collection in (self.structured, self.mapped):
      collection.update_many.assert_called_once()
      collection.delete_many.assert_called_once_with(
        {"url": {"$nin": ["offer-1", "offer-2"]}}
      )

  @patch.object(Config, "SCRAPER_ACTIVITY_SYNC_MIN_URLS", 3)
  def test_small_scrape_does_not_archive_or_delete_anything(self):
    synced = self.manager.sync_offer_activity(
      ["offer-1"],
      "offers",
      ["offers_structured", "offers_mapped"],
    )

    self.assertFalse(synced)
    for collection in (self.history, self.structured, self.mapped):
      collection.update_many.assert_not_called()
      collection.delete_many.assert_not_called()

  def test_inactive_offer_cannot_be_inserted_in_derived_collection(self):
    mapped_collection = MagicMock()
    self.manager.db = {Config.MAPPED_COLL: mapped_collection}

    self.manager.upsert_bulk_offers(
      Config.MAPPED_COLL,
      [{"url": "inactive-offer", "is_active": False}],
      "mapped",
    )

    mapped_collection.bulk_write.assert_not_called()


if __name__ == "__main__":
  unittest.main()
