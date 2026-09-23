from pydantic import BaseModel, ConfigDict, Field, model_validator


class CrawlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2000)
    save_to_db: bool = False
    download_images: bool = False

    @model_validator(mode="after")
    def validate_download(self):
        if self.download_images and not self.save_to_db:
            raise ValueError("download_images=true requires save_to_db=true")
        return self
