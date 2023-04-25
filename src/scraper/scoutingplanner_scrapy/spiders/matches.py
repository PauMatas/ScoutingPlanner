from os.path import join, dirname, abspath
import sys
sys.path.append(join(dirname(abspath(__file__)), '../../../../'))

from scrapy.spiders import Spider

from src.scraper.scoutingplanner_scrapy.items import Match
from src.scraper.scoutingplanner_scrapy.utils import *

class MatchesSpider(Spider):
    name = 'matches'
    start_urls = ['https://www.fcf.cat/resultats/2223/futbol-11/divisio-honor-cadet/grup-1',
                  'https://www.fcf.cat/resultats/2223/futbol-11/divisio-honor-juvenil/grup-3',
                  'https://www.fcf.cat/resultats/2223/futbol-11/tercera-federacio/grup-v',
                  'https://www.fcf.cat/resultats/2223/futbol-11/segona-federacio/grup-3',
                  'https://www.fcf.cat/resultats/2223/futbol-11/primera-federacio/grup-2']
    items = []

    def parse(self, response, **kwargs):
        season = response.xpath('//div[@class="col-md-12 p-0 p-impr d-n_impr"]/p[@class="bigtitle fs-18_ml p-10 m-0 mt-30"]/span[@class="apex"]/text()').get()
        competition = response.xpath('//select[@id="select_competi"]/option[@selected]/text()').get()
        group = response.xpath('//select[@id="select_grupo"]/option[@selected]/text()').get()
        matchday = int(response.xpath('//select[@id="select_jornada"]/option[@selected]/text()').get()[-2:])

        for match in response.xpath('//table[@class="uppercase w-100 fs-12_tp fs-11_ml table_resultats"]'):
            match_dict = {
                'season': season,
                'competition': competition,
                'group': group,
                'matchday': matchday
            }
            match_dict['finished'] = bool(match.xpath('.//td[@class="p-5 resultats-w-resultat tc"]/a/div[@class="tc fs-9 white bg-darkgrey mb-2 lh-data"]/text()').get())

            if match_dict['finished']:
                # Result
                result = match.xpath('.//td[@class="p-5 resultats-w-resultat tc"]/a/div[@class="tc fs-17 white bg-darkgrey p-r"]/text()').get()
                if result is not None:
                    match_dict['home_goals'], match_dict['away_goals'] = parse_result(result)
            else:
                # Temporal data
                date = match.xpath('normalize-space(.//td[@class="p-5 resultats-w-resultat tc"]/a/div[@class="tc fs-9 white bg-grey mb-2 lh-data"]/text())').get()
                time = match.xpath('normalize-space(.//td[@class="p-5 resultats-w-resultat tc"]/a/div[@class="tc fs-17 white bg-grey"]/text())').get()
                if date is not None and time is not None:
                    parsed_timestamp = parse_timestamp(date, time)
                    if parsed_timestamp is not None: # Parsing has been successful
                        match_dict['timestamp'] = parsed_timestamp

            # Teams
            match_dict['home_team'] = match.xpath('.//td[@class="p-5 resultats-w-equip tr"]/a/text()').get()
            match_dict['away_team'] = match.xpath('.//td[@class="p-5 resultats-w-equip tl"]/a/text()').get()
            
            # Location data
            stadium = match.xpath('.//td[@class="p-5 resultats-w-text2 tr fs-9 lh-20 d-n_ml"]/a/text()').get()
            if stadium is not None:
                match_dict['stadium'] = stadium
            google_maps_link = match.xpath('.//td[@class="p-0 resultats-w-text1 tc fs-9 capitalize ml-20 d-n_ml"]/a/@href').get()
            if google_maps_link is not None:
                match_dict['latlon'] = parse_google_maps_link(google_maps_link)

            self.items.append(match_dict)
            yield Match(**match_dict)