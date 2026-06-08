import unittest

from scraper import normalize_url


class TestNormalizeUrl(unittest.TestCase):
  def test_url_with_query_params(self):
    url = "https://www.linkedin.com/jobs/view/data-engineer-deloitte-1234567890?trk=public_jobs"

    result = normalize_url(url)

    self.assertEqual(result, "https://www.linkedin.com/jobs/view/1234567890")

  def test_url_without_query_params(self):
    url = "https://www.linkedin.com/jobs/view/cloud-consultant-98765"

    result = normalize_url(url)

    self.assertEqual(result, "https://www.linkedin.com/jobs/view/98765")
