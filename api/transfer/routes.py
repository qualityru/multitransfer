import asyncio
import json
import uuid
from typing import Dict, List

import aiohttp
from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from fp.fp import FreeProxy
from loguru import logger

from .schemas import Country

router = APIRouter(prefix="/transfer", tags=["Transfer"])

RU_CAPTCHA_KEY = "d4ef454fc420a794fa210c51012d90c2"


def load_countries_from_json(file_path: str = "multitransfer_data.json") -> List[Dict]:
    """Загружает список стран из JSON файла"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        countries = data.get("pageProps", {}).get("countries", [])
        country_list = []

        for country in countries:
            country_list.append(
                {
                    "code": country.get("alfa3Code"),
                    "name": country.get("nameCyrillic") or country.get("nameLat"),
                    "currency": country.get("defaultCurrency"),
                    "currencies": [
                        c.get("currencyCode") for c in country.get("currencies", [])
                    ],
                }
            )

        return country_list
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return []


COUNTRIES_DATA = load_countries_from_json()
COUNTRIES_DICT = {c["code"]: c for c in COUNTRIES_DATA}
COUNTRY_CODES = [c["code"] for c in COUNTRIES_DATA]


@router.get("/countries_and_currencies", response_model=List[Country])
async def get_countries():
    """Получить список всех доступных стран"""
    return [
        Country(
            country_code=c["code"],
            country=c["name"],
            currency=c["currency"],
        )
        for c in COUNTRIES_DATA
        if "USD" not in c["currency"] and "EUR" not in c["currency"]
    ]


async def solve_yandex_captcha(sitekey: str, pageurl: str) -> str:
    async with aiohttp.ClientSession() as session:
        proxy = FreeProxy(timeout=1, anonym=True).get()
        logger.debug(f"Using proxy for RuCaptcha: {proxy}")
        send_payload = {
            "key": RU_CAPTCHA_KEY,
            "method": "yandex",
            "sitekey": sitekey,
            "pageurl": pageurl,
            "invisible": 0,  # Для Yandex SmartCaptcha ставим 0 или 1 в зависимости от типа
            "enterprise": 0,  # Для SmartCaptcha должно быть 0
            "version": "ysc1",  # Указываем версию каптчи
            "json": 1,
        }

        async with session.post(
            "http://2captcha.com/in.php", data=send_payload
        ) as resp:
            data = await resp.json()
            logger.debug(f"RuCaptcha create task response: {data}")

        if data.get("status") != 1:
            error_text = data.get("request", "Unknown error")
            raise HTTPException(500, f"RuCaptcha error: {error_text}")

        task_id = data["request"]

        for i in range(30):
            await asyncio.sleep(2.5)

            async with session.get(
                "http://2captcha.com/res.php",
                params={
                    "key": RU_CAPTCHA_KEY,
                    "action": "get",
                    "id": task_id,
                    "json": 1,
                },
                proxy=proxy,
            ) as resp:
                result = await resp.json()
                logger.debug(f"RuCaptcha check attempt {i + 1}: {result}")

            if result.get("status") == 1:
                return result["request"]
            elif result.get("request") == "CAPCHA_NOT_READY":
                continue
            else:
                error_text = result.get("request", "Unknown error")
                raise HTTPException(500, f"RuCaptcha solving error: {error_text}")

        raise HTTPException(500, "Captcha solving timeout (150 seconds)")


@router.post("/create")
async def create_transfer(
    country_code: str = Query("TJK"),
    amount: float = Query(10000, gt=0),
    currency_to: str = Query("TJS"),
    beneficiary_last_name: str = Query("Petrov"),
    beneficiary_first_name: str = Query("Ivan"),
    account_number: str = Query("2200700164833153"),
    sender_last_name: str = Query("Петров"),
    sender_first_name: str = Query("Иван"),
    sender_middle_name: str = Query("Иванович"),
    sender_phone: str = Query("79281234567"),
    sender_birth_date: str = Query("1990-02-01T12:00:00"),
    doc_type: str = Query("21"),
    doc_number: str = Query("136012"),
    doc_series: str = Query("1232"),
    doc_issue_date: str = Query("2011-11-12T12:00:00"),
    # doc_country_code: str = Query("RUS"),
):
    BASE_HEADERS = {
        "Content-Type": "application/json",
        "client-id": "multitransfer-web-id",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        ),
    }

    def generate_headers(extra: dict | None = None):
        headers = {
            **BASE_HEADERS,
            "fhprequestid": str(uuid.uuid4()),
            "fhpsessionid": str(uuid.uuid4()),
            "x-request-id": str(uuid.uuid4()),
        }
        if extra:
            headers.update(extra)
        return headers

    async def post_with_retries(
        session, url: str, payload: dict, headers: dict, retries: int = 3
    ):
        last_error = None

        for attempt in range(1, retries + 1):
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status in (200, 201):
                        return await resp.json()

                    logger.error(f"[{attempt}/3] {url} [{resp.status}]: {text}")
                    last_error = HTTPException(status_code=resp.status, detail=text)

            except Exception as e:
                logger.error(f"[{attempt}/3] Exception on POST to {url}: {e}")
                last_error = e

            # Подождём немного перед новой попыткой
            await asyncio.sleep(2.5)

        # Все попытки исчерпаны
        if isinstance(last_error, HTTPException):
            raise last_error
        raise HTTPException(status_code=500, detail=str(last_error))

    # Оставшийся код не меняем
    async with aiohttp.ClientSession() as session:
        URL_COMMISSIONS = "https://api.multitransfer.ru/anonymous/multi/multitransfer-fee-calc/v3/commissions"
        commission_payload = {
            "countryCode": country_code,
            "range": "ALL_PLUS_LIMITS",
            "money": {
                "acceptedMoney": {"amount": amount, "currencyCode": "RUB"},
                "withdrawMoney": {"currencyCode": currency_to},
            },
        }

        commissions_data = await post_with_retries(
            session, URL_COMMISSIONS, commission_payload, generate_headers()
        )

        commission_id = commissions_data["fees"][0]["commissions"][0]["commissionId"]
        logger.debug(f"Using commission ID: {commission_id}")

        # Captcha
        SITEKEY = "ysc1_DAo8nFPdNCMHkAwYxIUJFxW5IIJd3ITGArZehXxO9a0ea6f8"
        PAGE_URL = "https://multitransfer.ru/transfer/tajikistan/sender-details"
        token = await solve_yandex_captcha(SITEKEY, PAGE_URL)
        # token = await solve_yandex_captcha_capmonster(SITEKEY, PAGE_URL)

        # Create transfer
        URL_CREATE = "https://api.multitransfer.ru/anonymous/multi/multitransfer-transfer-create/v3/anonymous/transfers/create"
        create_payload = {
            "beneficiary": {
                "lastName": beneficiary_last_name,
                "firstName": beneficiary_first_name,
            },
            "transfer": {
                "beneficiaryAccountNumber": account_number,
                "commissionId": commission_id,
                "paymentInstrument": {"type": "ANONYMOUS_CARD"},
            },
            "sender": {
                "lastName": sender_last_name,
                "firstName": sender_first_name,
                "middleName": sender_middle_name,
                "birthDate": sender_birth_date,
                "phoneNumber": sender_phone,
                "documents": [
                    {
                        "type": doc_type,
                        "number": doc_number,
                        "series": doc_series,
                        "issueDate": doc_issue_date,
                        # "countryCode": doc_country_code,
                        "countryCode": "RUS",
                    }
                ],
            },
        }

        create_headers = generate_headers({"fhptokenid": token})
        create_response = await post_with_retries(
            session, URL_CREATE, create_payload, create_headers
        )

        transfer_id = create_response["transferId"]
        logger.debug(f"Created transfer ID: {transfer_id}")

        # Confirm transfer
        URL_CONFIRM = "https://api.multitransfer.ru/anonymous/multi/multitransfer-qr-processing/v3/anonymous/confirm"
        confirm_payload = {
            "transactionId": transfer_id,
            "recordType": "transfer",
        }

        confirm_data = await post_with_retries(
            session, URL_CONFIRM, confirm_payload, generate_headers()
        )

        return confirm_data


# @router.post("/commissions")
# async def get_commissions(
#     country_code: str = Query("TJK", description="3-letter ISO country code"),
#     amount: float = Query(10000, gt=0, description="Amount to send"),
#     # currency_from: str = Query("RUB", description="Currency code to send from"),
#     currency_to: str = Query("TJS", description="Currency code to receive"),
# ):
#     URL = "https://api.multitransfer.ru/anonymous/multi/multitransfer-fee-calc/v3/commissions"
#     PAYLOAD = {
#         "countryCode": country_code,
#         "range": "ALL_PLUS_LIMITS",
#         "money": {
#             "acceptedMoney": {"amount": amount, "currencyCode": "RUB"},
#             "withdrawMoney": {"currencyCode": currency_to},
#         },
#     }

#     headers = {
#         "Content-Type": "application/json",
#         "fhprequestid": str(uuid.uuid4()),
#         "fhpsessionid": str(uuid.uuid4()),
#         "x-request-id": str(uuid.uuid4()),
#         "client-id": "multitransfer-web-id",
#         "Accept": "application/json, text/plain, */*",
#     }

#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.post(URL, json=PAYLOAD, headers=headers) as resp:
#                 text = await resp.text()
#                 if resp.status != 200:
#                     logger.error(
#                         f"Server returned status {resp.status}. Response body:\n{text}"
#                     )
#                     raise HTTPException(status_code=resp.status, detail=text)

#                 try:
#                     data = await resp.json()
#                     return data
#                 except Exception as e:
#                     logger.error(f"JSON parse error: {e}")
#                     raise HTTPException(
#                         status_code=500, detail="Invalid JSON response from server"
#                     )
#         except Exception as e:
#             logger.error(f"Unexpected error: {e}")
#             raise HTTPException(status_code=500, detail=str(e))


# @router.post("/create")
# async def create_transfer(
#     beneficiary_last_name: str = Query("Tarasov"),
#     beneficiary_first_name: str = Query("Alexandr"),
#     account_number: str = Query("2200700164833153"),
#     commission_id: str = Query("610faee9-a375-4ab8-8433-e6a44bc50f6b"),
#     sender_last_name: str = Query("ываываы"),
#     sender_first_name: str = Query("ываыва"),
#     sender_middle_name: str = Query("ыфваыва"),
#     sender_phone: str = Query("79180247002"),
#     sender_birth_date: str = Query("1990-02-01T12:00:00"),
#     doc_type: str = Query("21"),
#     doc_number: str = Query("135012"),
#     doc_series: str = Query("1232"),
#     doc_issue_date: str = Query("2011-11-12T12:00:00"),
#     doc_country_code: str = Query("RUS"),
# ):
#     import uuid

#     SITEKEY = "ysc1_DAo8nFPdNCMHkAwYxIUJFxW5IIJd3ITGArZehXxO9a0ea6f8"
#     PAGE_URL = "https://multitransfer.ru/transfer/tajikistan/sender-details"

#     token = await solve_yandex_captcha(SITEKEY, PAGE_URL)

#     payload = {
#         "beneficiary": {
#             "lastName": beneficiary_last_name,
#             "firstName": beneficiary_first_name,
#         },
#         "transfer": {
#             "beneficiaryAccountNumber": account_number,
#             "commissionId": commission_id,
#             "paymentInstrument": {"type": "ANONYMOUS_CARD"},
#         },
#         "sender": {
#             "lastName": sender_last_name,
#             "firstName": sender_first_name,
#             "middleName": sender_middle_name,
#             "birthDate": sender_birth_date,
#             "phoneNumber": sender_phone,
#             "documents": [
#                 {
#                     "type": doc_type,
#                     "number": doc_number,
#                     "series": doc_series,
#                     "issueDate": doc_issue_date,
#                     "countryCode": doc_country_code,
#                 }
#             ],
#         },
#     }

#     headers = {
#         "Content-Type": "application/json",
#         "fhprequestid": str(uuid.uuid4()),
#         "fhpsessionid": str(uuid.uuid4()),
#         "x-request-id": str(uuid.uuid4()),
#         "fhptokenid": token,
#         "client-id": "multitransfer-web-id",
#         "Accept": "application/json, text/plain, */*",
#         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
#     }

#     URL_CREATE = "https://api.multitransfer.ru/anonymous/multi/multitransfer-transfer-create/v3/anonymous/transfers/create"
#     URL_CONFIRM = "https://api.multitransfer.ru/anonymous/multi/multitransfer-qr-processing/v3/anonymous/confirm"

#     async with aiohttp.ClientSession() as session:
#         logger.debug("Creating transfer...")
#         async with session.post(URL_CREATE, json=payload, headers=headers) as resp:
#             create_response_text = await resp.text()

#             if resp.status != 201:
#                 raise HTTPException(
#                     status_code=resp.status, detail=create_response_text
#                 )

#             create_response = await resp.json()

#         transfer_id = create_response["transferId"]
#         logger.debug(f"Created transfer with ID: {transfer_id}")

#         confirm_payload = {"transactionId": transfer_id, "recordType": "transfer"}

#         headers = {
#             "Content-Type": "application/json",
#             "fhprequestid": str(uuid.uuid4()),
#             "fhpsessionid": str(uuid.uuid4()),
#             "x-request-id": str(uuid.uuid4()),
#             "client-id": "multitransfer-web-id",
#             "Accept": "application/json, text/plain, */*",
#             "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
#         }

#         logger.debug("Confirming transfer...")
#         async with session.post(
#             URL_CONFIRM, json=confirm_payload, headers=headers
#         ) as resp_confirm:
#             confirm_response_text = await resp_confirm.text()

#             if resp_confirm.status != 200:
#                 raise HTTPException(
#                     status_code=resp_confirm.status, detail=confirm_response_text
#                 )

#             confirm_response = await resp_confirm.json()
#             return confirm_response
