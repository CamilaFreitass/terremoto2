from fastapi import FastAPI, HTTPException
import requests
import json
import googlemaps
from haversine import haversine
from decouple import config
from unidecode import unidecode
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse

app = FastAPI()

DEBUG = config('DEBUG', cast=bool, default=False)

key = config('key')

def is_valid_data(data_str):
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def verificar_limite_de_tempo(data_inicial, data_final):
    limite_de_anos = 2
    diferenca = data_final - data_inicial
    dois_anos = timedelta(days=limite_de_anos * 365.25)
    if diferenca <= dois_anos:
        return True
    else:
        return False


@app.get('/', include_in_schema=False)
def index():
    return RedirectResponse("/docs", status_code=308)


@app.get('/consulta')
def consulta(cidade_base: str, data_inicio: str, data_fim: str):
    if not is_valid_data(data_inicio) or not is_valid_data(data_fim):
        raise HTTPException(status_code=400, detail="Formato da data inválido. Um exemplo de formato válido é '2022-04-02' (ano-mês-dia).")
    else:
        data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        if not verificar_limite_de_tempo(data_inicio, data_fim) == True:
            raise HTTPException(status_code=400,
                                detail="Intervalo de tempo muito grande entre 'data_inicio' e 'data_fim'. Intervalo máximo de 2 anos")
        else:
            cidade_base = unidecode(cidade_base).lower()

            response = requests.get(
                f'https://earthquake.usgs.gov/fdsnws/event/1/query.geojson?starttime={data_inicio}&endtime={data_fim}&minmagnitude=5&orderby=time')
            dados = json.loads(response.content)

            gmaps = googlemaps.Client(key=key)

            geocode_result = gmaps.geocode(cidade_base)

            if geocode_result:
                busca = geocode_result[0]['geometry']['location']

                latitude = busca['lat']

                longitude = busca['lng']

                local = [latitude, longitude]

                menor_distancia = 40075.0000

                magnitude = 5

                localizacao = None

                data_evento = None

                for item in dados['features']:
                    distancia = haversine(item['geometry']['coordinates'][-2::-1], local)
                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        magnitude = item['properties']['mag']
                        localizacao = item['properties']['place']
                        resposta = requests.get(item['properties']['detail'])
                        date = json.loads(resposta.content)
                        data_evento = date['properties']['products']['origin'][0]['properties']['eventtime'][0:10]

                data_evento = datetime.strptime(data_evento, "%Y-%m-%d").date()

                dados2 = (cidade_base, data_inicio, data_fim, magnitude, menor_distancia, localizacao, data_evento)

                return dados2

            else:
                raise HTTPException(status_code=400, detail="Cidade inválida. Digite uma cidade válida!")

