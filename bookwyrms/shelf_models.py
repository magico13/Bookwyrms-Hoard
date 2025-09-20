"""
Models for bookshelf and location management.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .models import BookInfo


@dataclass
class ShelfLocation:
    """Represents a specific location on a bookshelf."""
    location: str  # e.g., "Library"
    bookshelf_name: str  # e.g., "Large bookshelf"
    column: int
    row: int
    
    def __str__(self) -> str:
        """Human-readable location string."""
        return f"{self.location}/{self.bookshelf_name}/C{self.column}R{self.row}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "location": self.location,
            "bookshelf_name": self.bookshelf_name,
            "column": self.column,
            "row": self.row
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShelfLocation':
        """Create from dictionary."""
        return cls(
            location=data["location"],
            bookshelf_name=data["bookshelf_name"],
            column=data["column"],
            row=data["row"]
        )


@dataclass
class Bookshelf:
    """Represents a physical bookshelf with dimensions."""
    location: str  # e.g., "Library"
    name: str  # e.g., "Large bookshelf"
    rows: int
    columns: int
    description: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate dimensions."""
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("Rows and columns must be positive integers")
    
    def __str__(self) -> str:
        """Human-readable bookshelf description."""
        size_desc = f"{self.columns}×{self.rows}"
        if self.description:
            return f"{self.name} in {self.location} ({size_desc}) - {self.description}"
        return f"{self.name} in {self.location} ({size_desc})"
    
    def get_shelf_location(self, column: int, row: int) -> ShelfLocation:
        """Get a ShelfLocation for this bookshelf."""
        if not (0 <= column < self.columns):
            raise ValueError(f"Column must be between 0 and {self.columns - 1}")
        if not (0 <= row < self.rows):
            raise ValueError(f"Row must be between 0 and {self.rows - 1}")
        
        return ShelfLocation(
            location=self.location,
            bookshelf_name=self.name,
            column=column,
            row=row
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "location": self.location,
            "name": self.name,
            "rows": self.rows,
            "columns": self.columns,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bookshelf':
        """Create from dictionary."""
        return cls(
            location=data["location"],
            name=data["name"],
            rows=data["rows"],
            columns=data["columns"],
            description=data.get("description")
        )


@dataclass
class BookRecord:
    """Represents a book with location information."""
    book_info: BookInfo
    home_location: Optional[ShelfLocation] = None
    checked_out_to: Optional[str] = None
    checked_out_date: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def is_checked_out(self) -> bool:
        """Check if book is currently checked out."""
        return self.checked_out_to is not None
    
    @property
    def current_location_str(self) -> str:
        """Get current location as string."""
        if self.is_checked_out:
            return f"Checked out to {self.checked_out_to}"
        elif self.home_location:
            return str(self.home_location)
        else:
            return "Location unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "book_info": self.book_info.to_dict(),
            "home_location": self.home_location.to_dict() if self.home_location else None,
            "checked_out_to": self.checked_out_to,
            "checked_out_date": self.checked_out_date,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookRecord':
        """Create from dictionary."""
        return cls(
            book_info=BookInfo(**data["book_info"]),
            home_location=ShelfLocation.from_dict(data["home_location"]) if data.get("home_location") else None,
            checked_out_to=data.get("checked_out_to"),
            checked_out_date=data.get("checked_out_date"),
            notes=data.get("notes")
        )