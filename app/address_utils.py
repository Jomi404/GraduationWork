import requests

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
YANDEX_API_KEY = settings.yandex_api_key


def geocode_address(address):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": address,
        "format": "json",
        "lang": "ru_RU",
        "results": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        feature_member = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if feature_member:
            addresses = []
            for feature in feature_member:
                geo_object = feature["GeoObject"]
                text = geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
                address_details = geo_object["metaDataProperty"]["GeocoderMetaData"].get("AddressDetails", {})
                country = address_details.get("Country", {})
                admin_area = country.get("AdministrativeArea", {})
                locality = admin_area.get("Locality", {})
                thoroughfare = locality.get("Thoroughfare", {})
                premise = thoroughfare.get("Premise", {})

                if "ThoroughfareName" in thoroughfare and "PremiseNumber" in premise:
                    addresses.append(text)
                else:
                    addresses.append(text)
            return addresses
        else:
            return []
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            logger.error("Ошибка: Неверный или недействительный API-ключ. Проверьте ключ в личном кабинете Yandex API.")
        else:
            logger.error(f"HTTP-ошибка: {http_err}")
        return []
    except Exception as e:
        logger.debug(f"Произошла ошибка: {e}")
        return []


def reverse_geocode(lat, lon):
    url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": f"{lon},{lat}",
        "format": "json",
        "lang": "ru_RU",
        "results": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        feature_member = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if feature_member:
            geo_object = feature_member[0]["GeoObject"]
            address_details = geo_object["metaDataProperty"]["GeocoderMetaData"].get("AddressDetails", {})
            if address_details:
                country = address_details.get("Country", {})
                admin_area = country.get("AdministrativeArea", {})
                locality = admin_area.get("Locality", {})
                thoroughfare = locality.get("Thoroughfare", {})
                premise = thoroughfare.get("Premise", {})

                city = locality.get("LocalityName", admin_area.get("AdministrativeAreaName", ""))
                street = thoroughfare.get("ThoroughfareName", "")
                house = premise.get("PremiseNumber", "")

                if city and street and house:
                    return f"{city}, {street}, {house}"
            return geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
        else:
            return None
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 403:
            logger.error("Ошибка: Неверный или недействительный API-ключ. Проверьте ключ в личном кабинете Yandex API.")
        else:
            logger.error(f"HTTP-ошибка: {http_err}")
        return None
    except Exception as e:
        logger.debug(f"Произошла ошибка: {e}")
        return None


def validate_address(text):
    parts = [part.strip() for part in text.split(',')]
    if len(parts) < 3:
        return False
    house_part = parts[2]
    return any(char.isdigit() for char in house_part)
