import unittest

import requests


class APITestMethods(unittest.TestCase):
  def setUp(self):
    self.host = "http://127.0.0.1:8000"
    data = requests.post(self.host + "/api/token/", json={"username": "ultmaster", "password": "LkEMLc0nc8Hf"}).json()
    self.authorization = {"Authorization": "Bearer " + data["access"]}

  def test_status_hidden(self):
    data = requests.get(self.host + "/api/status/hidden/?limit=10&offset=10", headers=self.authorization).json()
    print(data)

  def test_problem(self):
    pass

if __name__ == '__main__':
  unittest.main()
