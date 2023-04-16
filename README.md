# ManiScouting

Aquest projecte pretén crear una eina per a trobar les millors rutes i combinacions per a veure els millors partits de futbol català.

El projecte tindrà tres eixos principals el scraping de la web de la federació, la gestió de rutes i la presentació dels resultats en format web.

## Scraping de la federació

La idea és extreure tant calendaris, com resultats i informació dels equips. En primer lloc els calendaris són un bàsic que ha de servir per a situar els partits en el temps, per a situar-los en l'espai la idea és extreure informació dels estadis dels equips sabent on es juga amb el calendari. Per últim els resultats dels diferents partits serviran juntament amb la classificació per a ponderar quins són els futurs partits més interessants. De cara a futur podria ser interessant també obtenir informació de jugadors en particular per a que puguin aportar en la importància dels partits.

La idea inicial és utilitzar [`scrapy`](https://docs.scrapy.org/en/latest/) per a scrapejar directament la web de la [Federació Catalana de Futbol](https://www.fcf.cat) o, com a alternativa, fer servir la api de [resultados de fútbol](https://www.resultados-futbol.com/api/documentacion).

## Gestió de rutes

De cara a traçar les millors rutes necessitem estimacions de quant es tarda d'un estadi a un altre. D'aquesta manera podrem constuïr un graf on els pesos dels nodes seran les importàncies dels partits mencionades abans i les arestes seran tots aquells desplaçaments viables i el seu pes serà el temps entre partits.

Per a aconseguir la informació del desplaçaments es farà servir la api de [Openrouteservice](https://openrouteservice.org).

## :construction: Web :construction:

Aquesta part no està planejada ja que dependrà de la implementació de les dues primeres.
