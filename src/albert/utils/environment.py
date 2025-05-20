from enum import Enum


class AlbertEnvironment(str, Enum):
    DEV = "dev"
    SANDBOX = "sandbox"
    APP = "app"

    @property
    def domain(self) -> str:
        match self:
            case AlbertEnvironment.DEV:
                return "dev.albertinventdev.com"
            case AlbertEnvironment.SANDBOX:
                return "sandbox.albertinvent.com"
            case AlbertEnvironment.APP:
                return "app.albertinvent.com"

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}"
