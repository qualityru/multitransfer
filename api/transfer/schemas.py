from pydantic import BaseModel


class Country(BaseModel):
    country_code: str
    country: str
    currency: str
