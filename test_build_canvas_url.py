from unittest import TestCase
from utils import build_canvas_url


class TestBuild_canvas_url(TestCase):
    def test_build_canvas_url(self):
        api_subdirectories = ["courses", 49815, "users"]
        params = {"page_num": 1, "include[]": "test_student"}
        url = build_canvas_url(api_subdirectories, params)

        valid_urls = ["https://canvas.northwestern.edu/api/v1/courses/49815/users?include[]=test_student&page_num=1",
                      "https://canvas.northwestern.edu/api/v1/courses/49815/users?page_num=1&include[]=test_student"]
        #self.assertEqual(url, expected_url)
        self.assertIn(url, valid_urls)
