import asyncio
from datetime import datetime, timedelta
import json
import uuid
from typing import Dict, List

import aiohttp
from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from twocaptcha import TwoCaptcha
from loguru import logger

from .schemas import Country
from config import settings

router = APIRouter(prefix="/transfer", tags=["Transfer"])


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
CAPTCHA_TOKENS: dict[str, datetime] = {}
TOKEN_LIFETIME = timedelta(minutes=5)


@router.get("/countries_and_currencies", response_model=List[Country])
async def get_countries():
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
    solver = TwoCaptcha(apiKey=settings.RU_CAPTCHA_KEY, pollingInterval=5)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: solver.yandex_smart(
                sitekey=sitekey,
                url=pageurl,
                invisible=0,
                userAgent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
            )
        )
        return result.get("code")
    except Exception as e:
        raise HTTPException(500, f"Ошибка решателя: {e}")


def get_valid_token() -> str | None:
    now = datetime.utcnow()
    valid_tokens = {t: ts for t, ts in CAPTCHA_TOKENS.items() if now - ts <= TOKEN_LIFETIME}
    CAPTCHA_TOKENS.clear()
    CAPTCHA_TOKENS.update(valid_tokens)

    if not CAPTCHA_TOKENS:
        return None

    token, _ = CAPTCHA_TOKENS.popitem()
    return token


@router.post("/solve_captcha")
async def get_captcha_token():
    sitekey = "ysc1_DAo8nFPdNCMHkAwYxIUJFxW5IIJd3ITGArZehXxO9a0ea6f8"
    pageurl = "https://multitransfer.ru/transfer/tajikistan/sender-details&test=false&webview=false&hideChallengeContainer=false"

    async def solve_and_store():
        try:
            token = await solve_yandex_captcha(sitekey, pageurl)
            CAPTCHA_TOKENS[token] = datetime.utcnow()
            logger.debug(f"Captcha token added in background. Total tokens: {len(CAPTCHA_TOKENS)}")
        except Exception as e:
            logger.error(f"Failed to solve captcha in background: {e}")

    asyncio.create_task(solve_and_store())
    return {"message": "Captcha solving started in background", "queue_size": len(CAPTCHA_TOKENS)}


@router.post("/create")
async def create_transfer(
    country_code: str = Query("TJK"),
    amount: float = Query(10000, gt=0),
    currency_to: str = Query("TJS"),
    beneficiary_last_name: str = Query("Petrov"),
    beneficiary_first_name: str = Query("Ivan"),
    account_number: str = Query("2200700164833154"),
    sender_last_name: str = Query("Петров"),
    sender_first_name: str = Query("Иван"),
    sender_middle_name: str = Query("Иванович"),
    sender_phone: str = Query("79281234567"),
    sender_birth_date: str = Query("1990-02-01T12:00:00"),
    doc_type: str = Query("21"),
    doc_number: str = Query("136012"),
    doc_series: str = Query("1232"),
    doc_issue_date: str = Query("2011-11-12T12:00:00"),
):
    token = get_valid_token()
    if not token:
        raise HTTPException(400, "Нет доступных токенов капчи. Сначала вызовите /solve_captcha")

    logger.debug(f"Using captcha token. Remaining tokens: {len(CAPTCHA_TOKENS)}")

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

    async def post_with_retries(session, url: str, payload: dict, headers: dict, retries: int = 3):
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
            await asyncio.sleep(2.5)
        if isinstance(last_error, HTTPException):
            raise last_error
        raise HTTPException(status_code=500, detail=str(last_error))

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
        commissions_data = await post_with_retries(session, URL_COMMISSIONS, commission_payload, generate_headers())
        commission_id = commissions_data["fees"][0]["commissions"][0]["commissionId"]
        logger.debug(f"Using commission ID: {commission_id}")

        URL_CREATE = "https://api.multitransfer.ru/anonymous/multi/multitransfer-transfer-create/v3/anonymous/transfers/create"
        create_payload = {
            "beneficiary": {"lastName": beneficiary_last_name, "firstName": beneficiary_first_name},
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
                "documents": [{
                    "type": doc_type,
                    "number": doc_number,
                    "series": doc_series,
                    "issueDate": doc_issue_date,
                    "countryCode": "RUS",
                }],
            },
        }
        create_headers = generate_headers({"fhptokenid": token})
        create_response = await post_with_retries(session, URL_CREATE, create_payload, create_headers)
        transfer_id = create_response["transferId"]
        logger.debug(f"Created transfer ID: {transfer_id}")

        URL_CONFIRM = "https://api.multitransfer.ru/anonymous/multi/multitransfer-qr-processing/v3/anonymous/confirm"
        confirm_payload = {"transactionId": transfer_id, "recordType": "transfer"}
        confirm_data = await post_with_retries(session, URL_CONFIRM, confirm_payload, generate_headers())

        return confirm_data
