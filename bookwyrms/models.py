"""
Data models for book information.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class BookInfo:
    """Represents complete information about a book."""
    isbn: str
    title: str
    authors: List[str]
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    genres: Optional[List[str]] = None
    page_count: Optional[int] = None
    cover_url: Optional[str] = None
    language: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable representation of the book."""
        authors_str = ", ".join(self.authors) if self.authors else "Unknown Author"
        result = f"{self.title} by {authors_str}"
        if self.published_date:
            result += f" ({self.published_date})"
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert BookInfo to dictionary."""
        return {
            "isbn": self.isbn,
            "title": self.title,
            "authors": self.authors,
            "publisher": self.publisher,
            "published_date": self.published_date,
            "description": self.description,
            "genres": self.genres or [],
            "page_count": self.page_count,
            "cover_url": self.cover_url,
            "language": self.language
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookInfo':
        """Create BookInfo from dictionary."""
        return cls(
            isbn=data["isbn"],
            title=data["title"],
            authors=data["authors"],
            publisher=data.get("publisher"),
            published_date=data.get("published_date"),
            description=data.get("description"),
            genres=data.get("genres"),
            page_count=data.get("page_count"),
            cover_url=data.get("cover_url"),
            language=data.get("language")
        )