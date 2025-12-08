from pydantic import BaseModel, ConfigDict, Field


class Country(BaseModel):
    country_code: str
    country: str
    currency: str


class Commission(BaseModel):
    country_code: str
    country_name: str
    amount: float
    currency_from: str
    currency_to: str
    rate: float
    commission: float
    total: float
