"""Document parser for various file formats"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import mimetypes
from abc import ABC, abstractmethod
import json

# Format-specific imports
import markdown
from bs4 import BeautifulSoup
import pypdf
import tiktoken


@dataclass
class ParsedDocument:
    """Represents a parsed document"""
    id: str
    source: str
    content: str
    format: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    parsed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def word_count(self) -> int:
        """Get word count of content"""
        return len(self.content.split())
    
    @property
    def char_count(self) -> int:
        """Get character count of content"""
        return len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "format": self.format,
            "metadata": self.metadata,
            "sections": self.sections,
            "parsed_at": self.parsed_at.isoformat(),
            "word_count": self.word_count,
            "char_count": self.char_count
        }


class BaseParser(ABC):
    """Abstract base class for document parsers"""
    
    @abstractmethod
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        """Check if parser can handle this source"""
        pass
    
    @abstractmethod
    def parse(self, source: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse the document"""
        pass


class TextParser(BaseParser):
    """Parser for plain text files"""
    
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        if mime_type:
            return mime_type.startswith("text/")
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.suffix in [".txt", ".log", ".csv", ".tsv"]
        
        return False
    
    def parse(self, source: Union[str, Path], encoding: str = "utf-8", **kwargs) -> ParsedDocument:
        """Parse text file"""
        if isinstance(source, str) and not Path(source).exists():
            # Treat as raw text
            content = source
            doc_source = "raw_text"
        else:
            # Read from file
            path = Path(source)
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            doc_source = str(path)
        
        # Simple section detection (paragraphs)
        sections = []
        paragraphs = content.split("\n\n")
        
        for i, para in enumerate(paragraphs):
            if para.strip():
                sections.append({
                    "index": i,
                    "type": "paragraph",
                    "content": para.strip(),
                    "start": content.find(para),
                    "end": content.find(para) + len(para)
                })
        
        return ParsedDocument(
            id=f"doc_{datetime.now().timestamp()}",
            source=doc_source,
            content=content,
            format="text",
            sections=sections,
            metadata={
                "encoding": encoding,
                "line_count": content.count("\n") + 1
            }
        )


class MarkdownParser(BaseParser):
    """Parser for Markdown documents"""
    
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        if mime_type:
            return mime_type in ["text/markdown", "text/x-markdown"]
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.suffix in [".md", ".markdown"]
        
        return False
    
    def parse(self, source: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse Markdown document"""
        if isinstance(source, str) and not Path(source).exists():
            # Treat as raw markdown
            content = source
            doc_source = "raw_markdown"
        else:
            # Read from file
            path = Path(source)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            doc_source = str(path)
        
        # Parse markdown to HTML
        md = markdown.Markdown(extensions=['extra', 'toc', 'meta'])
        html = md.convert(content)
        
        # Extract sections from HTML
        soup = BeautifulSoup(html, 'html.parser')
        sections = []
        
        # Extract headings and their content
        for i, heading in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
            section = {
                "index": i,
                "type": f"heading_{heading.name[1]}",
                "title": heading.get_text().strip(),
                "content": "",
                "level": int(heading.name[1])
            }
            
            # Get content until next heading
            current = heading.next_sibling
            content_parts = []
            
            while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if current.string:
                    content_parts.append(str(current.string).strip())
                current = current.next_sibling
            
            section["content"] = " ".join(content_parts)
            sections.append(section)
        
        # Extract metadata if available
        metadata = getattr(md, 'Meta', {})
        
        return ParsedDocument(
            id=f"doc_{datetime.now().timestamp()}",
            source=doc_source,
            content=content,
            format="markdown",
            sections=sections,
            metadata={
                "markdown_meta": metadata,
                "toc": getattr(md, 'toc', ""),
                "plain_text": soup.get_text()
            }
        )


class PDFParser(BaseParser):
    """Parser for PDF documents"""
    
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        if mime_type:
            return mime_type == "application/pdf"
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.suffix.lower() == ".pdf"
        
        return False
    
    def parse(self, source: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse PDF document"""
        path = Path(source)
        
        if not path.exists():
            raise ValueError(f"PDF file not found: {path}")
        
        # Read PDF
        pdf_reader = pypdf.PdfReader(str(path))
        
        # Extract text from all pages
        content_parts = []
        sections = []
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            
            if text.strip():
                content_parts.append(text)
                sections.append({
                    "index": page_num,
                    "type": "page",
                    "page_number": page_num + 1,
                    "content": text.strip()
                })
        
        content = "\n\n".join(content_parts)
        
        # Extract metadata
        metadata = {}
        if pdf_reader.metadata:
            metadata = {
                "title": pdf_reader.metadata.get("/Title", ""),
                "author": pdf_reader.metadata.get("/Author", ""),
                "subject": pdf_reader.metadata.get("/Subject", ""),
                "creator": pdf_reader.metadata.get("/Creator", ""),
                "creation_date": str(pdf_reader.metadata.get("/CreationDate", "")),
                "modification_date": str(pdf_reader.metadata.get("/ModDate", ""))
            }
        
        metadata["page_count"] = len(pdf_reader.pages)
        
        return ParsedDocument(
            id=f"doc_{datetime.now().timestamp()}",
            source=str(path),
            content=content,
            format="pdf",
            sections=sections,
            metadata=metadata
        )


class HTMLParser(BaseParser):
    """Parser for HTML documents"""
    
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        if mime_type:
            return mime_type in ["text/html", "application/xhtml+xml"]
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.suffix.lower() in [".html", ".htm", ".xhtml"]
        
        return False
    
    def parse(self, source: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse HTML document"""
        if isinstance(source, str) and not Path(source).exists():
            # Treat as raw HTML
            html_content = source
            doc_source = "raw_html"
        else:
            # Read from file
            path = Path(source)
            with open(path, "r", encoding="utf-8") as f:
                html_content = f.read()
            doc_source = str(path)
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text content
        content = soup.get_text(separator="\n", strip=True)
        
        # Extract sections
        sections = []
        
        # Extract title
        title = soup.find('title')
        if title:
            sections.append({
                "index": 0,
                "type": "title",
                "content": title.get_text().strip()
            })
        
        # Extract headings
        for i, heading in enumerate(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
            sections.append({
                "index": i + 1,
                "type": f"heading_{heading.name[1]}",
                "content": heading.get_text().strip(),
                "level": int(heading.name[1])
            })
        
        # Extract paragraphs
        for i, para in enumerate(soup.find_all('p')):
            text = para.get_text().strip()
            if text:
                sections.append({
                    "index": len(sections),
                    "type": "paragraph",
                    "content": text
                })
        
        # Extract metadata
        metadata = {}
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property', '')
            content = meta.get('content', '')
            if name and content:
                metadata[f"meta_{name}"] = content
        
        return ParsedDocument(
            id=f"doc_{datetime.now().timestamp()}",
            source=doc_source,
            content=content,
            format="html",
            sections=sections,
            metadata=metadata
        )


class JSONParser(BaseParser):
    """Parser for JSON documents"""
    
    def can_parse(self, source: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        if mime_type:
            return mime_type == "application/json"
        
        if isinstance(source, (str, Path)):
            path = Path(source)
            return path.suffix.lower() == ".json"
        
        return False
    
    def parse(self, source: Union[str, Path], **kwargs) -> ParsedDocument:
        """Parse JSON document"""
        if isinstance(source, str) and not Path(source).exists():
            # Treat as raw JSON
            try:
                data = json.loads(source)
                doc_source = "raw_json"
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON content")
        else:
            # Read from file
            path = Path(source)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            doc_source = str(path)
        
        # Convert to readable text
        content = json.dumps(data, indent=2, ensure_ascii=False)
        
        # Extract sections based on top-level keys
        sections = []
        if isinstance(data, dict):
            for i, (key, value) in enumerate(data.items()):
                sections.append({
                    "index": i,
                    "type": "field",
                    "key": key,
                    "content": json.dumps(value, indent=2, ensure_ascii=False) if not isinstance(value, str) else value
                })
        elif isinstance(data, list):
            for i, item in enumerate(data):
                sections.append({
                    "index": i,
                    "type": "item",
                    "content": json.dumps(item, indent=2, ensure_ascii=False) if not isinstance(item, str) else str(item)
                })
        
        return ParsedDocument(
            id=f"doc_{datetime.now().timestamp()}",
            source=doc_source,
            content=content,
            format="json",
            sections=sections,
            metadata={
                "data_type": type(data).__name__,
                "size": len(data) if isinstance(data, (list, dict)) else 1
            }
        )


class DocumentParser:
    """
    Main document parser that delegates to format-specific parsers
    
    Features:
    - Automatic format detection
    - Extensible parser registry
    - Metadata extraction
    - Section identification
    """
    
    def __init__(self):
        # Register parsers
        self.parsers: List[BaseParser] = [
            TextParser(),
            MarkdownParser(),
            PDFParser(),
            HTMLParser(),
            JSONParser()
        ]
        
        # Token counter for estimating costs
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def register_parser(self, parser: BaseParser):
        """Register a custom parser"""
        self.parsers.append(parser)
    
    def parse(
        self,
        source: Union[str, Path],
        format_hint: Optional[str] = None,
        **kwargs
    ) -> ParsedDocument:
        """Parse a document from various sources"""
        # Detect format
        mime_type = None
        
        if isinstance(source, (str, Path)) and Path(source).exists():
            path = Path(source)
            mime_type, _ = mimetypes.guess_type(str(path))
        
        # Override with format hint
        if format_hint:
            mime_map = {
                "text": "text/plain",
                "markdown": "text/markdown",
                "pdf": "application/pdf",
                "html": "text/html",
                "json": "application/json"
            }
            mime_type = mime_map.get(format_hint, mime_type)
        
        # Find appropriate parser
        for parser in self.parsers:
            if parser.can_parse(source, mime_type):
                doc = parser.parse(source, **kwargs)
                
                # Add token count
                doc.metadata["token_count"] = len(self.tokenizer.encode(doc.content))
                
                return doc
        
        # Fallback to text parser
        return self.parsers[0].parse(source, **kwargs)
    
    def parse_multiple(
        self,
        sources: List[Union[str, Path]],
        **kwargs
    ) -> List[ParsedDocument]:
        """Parse multiple documents"""
        documents = []
        
        for source in sources:
            try:
                doc = self.parse(source, **kwargs)
                documents.append(doc)
            except Exception as e:
                print(f"Error parsing {source}: {e}")
        
        return documents