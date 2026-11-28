from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class PredictResponse(BaseModel):
    id: int
    message: str
    intent: str


class ClassifyRequest(BaseModel):
    # remove espaços das pontas, então uma mensagem só com espaços cai no min_length
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=1000)


class ClassifyResponse(BaseModel):
    intent: str
    probability: float
