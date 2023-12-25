"""
Not really a model in ORM sense, rather a class to perform some common tasks
"""

import pymongo
from ..utils import Singleton


class MongoBackend(metaclass=Singleton):
    def __init__(self) -> None:
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.db = self.client.wordnet
        self.collection = self.db["tasks"]
