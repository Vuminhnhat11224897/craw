from pydantic import BaseModel, ConfigDict, Field


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2000)
    download_images: bool = False
