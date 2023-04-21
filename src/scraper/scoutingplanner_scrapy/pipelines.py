# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from pymongo import MongoClient
from itemadapter import ItemAdapter

class MatchesPipeline:

    def __init__(self, mongo_uri, mongo_db, mongo_certificate_path):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_certificate_path = mongo_certificate_path

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DB', 'matches'),
            mongo_certificate_path=crawler.settings.get('MONGO_CERTIFICATE_PATH')
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri,
                     tls=True,
                     tlsCertificateKeyFile=self.mongo_certificate_path)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[item.season].insert_one(ItemAdapter(item).asdict())
        return item
