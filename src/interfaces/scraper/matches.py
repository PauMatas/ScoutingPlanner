from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from src.scraper.scoutingplanner_scrapy.spiders import MatchesSpider

def run_matches_spider():
    process = CrawlerProcess(get_project_settings())
    process.crawl(MatchesSpider)
    process.start()

    # Return the extracted items
    return MatchesSpider.items