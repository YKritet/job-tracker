from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class JobResult:
    title: str
    company: str
    location: str
    url: str
    platform: str
    contract: str = ""

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, JobResult) and self.url == other.url


class BaseSearcher(ABC):
    @abstractmethod
    def search(self, keywords: str, location: str, count: int = 50) -> list[JobResult]:
        ...
