"""
Indexer module for note-rag
Handles document chunking, embedding, and storage in LanceDB

Non-blocking version: Uses thread pool for CPU work and yields to event loop
"""

import os
import re
import logging
import hashlib
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import httpx
import frontmatter
import lancedb
from lancedb.pydantic import LanceModel, Vector

from config import Settings

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations (file I/O, hashing, chunking)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="indexer")


class DocumentChunk(LanceModel):
    """Schema for document chunks in LanceDB."""
    id: str                      # Unique chunk ID (file_hash + chunk_index)
    vector: Vector(768)          # nomic-embed-text dimension
    file_path: str
    file_hash: str               # MD5 of file content (for change detection)
    title: str
    category: str
    people: List[str]
    projects: List[str]
    date: Optional[str]
    vault: str
    chunk_index: int
    content: str


class Indexer:
    def __init__(self, db: lancedb.DBConnection, settings: Settings, fts_index=None):
        self.db = db
        self.settings = settings
        self.embedding_cache = {}
        self._cancel_requested = False
        self.fts_index = fts_index  # Optional FTS index for hybrid search
    
    def request_cancel(self):
        """Request cancellation of current indexing job."""
        self._cancel_requested = True
    
    async def init_tables(self):
        """Initialize LanceDB tables if they don't exist."""
        existing_tables = self.db.table_names()
        
        if "work" not in existing_tables:
            logger.info("Creating 'work' table")
            self.db.create_table("work", schema=DocumentChunk)
        
        if "personal" not in existing_tables:
            logger.info("Creating 'personal' table")
            self.db.create_table("personal", schema=DocumentChunk)
        
        logger.info("Tables initialized")
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama."""
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.ollama_url}/api/embed",
                json={
                    "model": self.settings.embedding_model,
                    "input": text
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["embeddings"][0]
        
        # Cache it
        self.embedding_cache[cache_key] = embedding
        return embedding
    
    def _chunk_document_sync(self, content: str, metadata: dict) -> List[Dict]:
        """Split document into chunks with overlap. (CPU-bound, runs in thread pool)"""
        chunks = []
        
        # Simple chunking by paragraphs/sections
        # Split on double newlines or headers
        sections = re.split(r'\n\n+|(?=^###?\s)', content, flags=re.MULTILINE)
        
        current_chunk = ""
        chunk_index = 0
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # If adding this section exceeds chunk size, save current and start new
            if len(current_chunk) + len(section) > self.settings.chunk_size * 4:  # Approx chars
                if current_chunk:
                    chunks.append({
                        "chunk_index": chunk_index,
                        "content": current_chunk.strip(),
                        **metadata
                    })
                    chunk_index += 1
                    # Keep overlap
                    overlap_start = max(0, len(current_chunk) - self.settings.chunk_overlap * 4)
                    current_chunk = current_chunk[overlap_start:] + "\n\n" + section
                else:
                    current_chunk = section
            else:
                current_chunk += "\n\n" + section if current_chunk else section
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "content": current_chunk.strip(),
                **metadata
            })
        
        return chunks
    
    async def chunk_document(self, content: str, metadata: dict) -> List[Dict]:
        """Split document into chunks with overlap. Non-blocking wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, 
            self._chunk_document_sync, 
            content, 
            metadata
        )
    
    def _extract_metadata_sync(self, file_path: Path, content: str) -> Dict:
        """Extract metadata from file. (CPU-bound, runs in thread pool)"""
        # Parse frontmatter
        try:
            post = frontmatter.loads(content)
            fm = post.metadata
            body = post.content
        except:
            fm = {}
            body = content
        
        # Determine vault
        path_str = str(file_path)
        if self.settings.vault_work_path in path_str:
            vault = "work"
        elif self.settings.vault_personal_path in path_str:
            vault = "personal"
        else:
            vault = "unknown"
        
        # Extract category from path
        relative_path = file_path.relative_to(
            self.settings.vault_work_path if vault == "work" 
            else self.settings.vault_personal_path
        )
        category = relative_path.parts[0] if relative_path.parts else "other"
        
        # Get title
        title = fm.get("title", file_path.stem)
        
        # Get date
        date = fm.get("date")
        if date:
            date = str(date)
        else:
            # Try to extract from filename
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path.name)
            if date_match:
                date = date_match.group(1)
        
        # Get people and projects
        people = fm.get("people", [])
        if isinstance(people, str):
            people = [p.strip() for p in people.split(",")]
        
        projects = fm.get("projects", [])
        if isinstance(projects, str):
            projects = [p.strip() for p in projects.split(",")]
        
        return {
            "file_path": str(file_path),
            "file_hash": hashlib.md5(content.encode()).hexdigest(),
            "title": title,
            "category": category,
            "people": people,
            "projects": projects,
            "date": date,
            "vault": vault,
            "body": body
        }
    
    async def extract_metadata(self, file_path: Path, content: str) -> Dict:
        """Extract metadata from file. Non-blocking wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._extract_metadata_sync,
            file_path,
            content
        )
    
    def is_excluded(self, file_path: Path) -> bool:
        """Check if file should be excluded."""
        path_str = str(file_path)
        for excluded in self.settings.excluded_folders_list:
            if excluded in path_str:
                return True
        return False
    
    def _read_file_sync(self, file_path: Path) -> Optional[str]:
        """Read file content. (I/O-bound, runs in thread pool)"""
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    async def read_file(self, file_path: Path) -> Optional[str]:
        """Read file content. Non-blocking wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._read_file_sync, file_path)
    
    async def index_file(self, file_path: Path, table_name: str) -> int:
        """Index a single file."""
        if self.is_excluded(file_path):
            logger.debug(f"Skipping excluded file: {file_path}")
            return 0
        
        content = await self.read_file(file_path)
        if content is None or len(content.strip()) < 50:
            logger.debug(f"Skipping short/unreadable file: {file_path}")
            return 0
        
        metadata = await self.extract_metadata(file_path, content)
        body = metadata.pop("body")
        chunks = await self.chunk_document(body, metadata)
        
        if not chunks:
            return 0
        
        table = self.db.open_table(table_name)
        
        # Generate embeddings and prepare records
        records = []
        for chunk in chunks:
            # Check for cancellation
            if self._cancel_requested:
                logger.info("Indexing cancelled")
                return len(records)
            
            try:
                embedding = await self.get_embedding(chunk["content"][:8000])  # Limit input
                
                chunk_id = f"{chunk['file_hash']}_{chunk['chunk_index']}"
                
                records.append(DocumentChunk(
                    id=chunk_id,
                    vector=embedding,
                    file_path=chunk["file_path"],
                    file_hash=chunk["file_hash"],
                    title=chunk["title"],
                    category=chunk["category"],
                    people=chunk["people"],
                    projects=chunk["projects"],
                    date=chunk["date"],
                    vault=chunk["vault"],
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"]
                ))
            except Exception as e:
                logger.error(f"Error embedding chunk {chunk['chunk_index']} of {file_path}: {e}")
        
        if records:
            # Delete existing chunks for this file (by file_hash prefix)
            try:
                table.delete(f'file_hash = "{metadata["file_hash"]}"')
            except:
                pass  # Table might be empty
            
            # Add new records
            table.add([r.dict() for r in records])
            logger.info(f"Indexed {len(records)} chunks from {file_path.name}")
            
            # Also index to FTS for hybrid search
            if self.fts_index:
                try:
                    self.fts_index.upsert_document(
                        file_path=str(file_path),
                        title=metadata.get("title", ""),
                        content=body,  # Full document content
                        vault=table_name,
                        category=metadata.get("category", ""),
                        people=metadata.get("people", []),
                        date=metadata.get("date")
                    )
                except Exception as e:
                    logger.warning(f"FTS indexing failed for {file_path}: {e}")
        
        return len(records)
    
    def _list_markdown_files_sync(self, vault_path: Path) -> List[Path]:
        """List all markdown files in vault. (I/O-bound, runs in thread pool)"""
        files = []
        for md_file in vault_path.rglob("*.md"):
            if not md_file.name.startswith("."):
                files.append(md_file)
        return files
    
    async def list_markdown_files(self, vault_path: Path) -> List[Path]:
        """List all markdown files in vault. Non-blocking wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._list_markdown_files_sync,
            vault_path
        )
    
    async def full_reindex(self, vault: str = "all") -> int:
        """Full reindex of vault(s). Non-blocking."""
        self._cancel_requested = False
        total_indexed = 0
        
        vaults_to_index = []
        if vault in ["all", "work"]:
            vaults_to_index.append(("work", Path(self.settings.vault_work_path)))
        if vault in ["all", "personal"]:
            vaults_to_index.append(("personal", Path(self.settings.vault_personal_path)))
        
        for table_name, vault_path in vaults_to_index:
            if self._cancel_requested:
                break
                
            logger.info(f"Full reindex of {table_name} vault...")
            
            # Clear table
            try:
                table = self.db.open_table(table_name)
                # LanceDB doesn't have truncate, so we delete all
                table.delete("id IS NOT NULL")
            except:
                pass
            
            # List files (non-blocking)
            md_files = await self.list_markdown_files(vault_path)
            total_files = len(md_files)
            logger.info(f"Found {total_files} files to index in {table_name}")
            
            # Index all markdown files
            for i, md_file in enumerate(md_files):
                if self._cancel_requested:
                    logger.info("Indexing cancelled by request")
                    break
                
                count = await self.index_file(md_file, table_name)
                total_indexed += count
                
                # Yield to event loop every 10 files to keep server responsive
                if i % 10 == 0:
                    await asyncio.sleep(0)
                    if i > 0 and i % 100 == 0:
                        logger.info(f"Progress: {i}/{total_files} files ({table_name})")
        
        logger.info(f"Full reindex complete: {total_indexed} chunks")
        return total_indexed
    
    async def incremental_index(self, vault: str = "all") -> int:
        """Incremental index (only new/modified files). Non-blocking."""
        self._cancel_requested = False
        total_indexed = 0
        
        vaults_to_index = []
        if vault in ["all", "work"]:
            vaults_to_index.append(("work", Path(self.settings.vault_work_path)))
        if vault in ["all", "personal"]:
            vaults_to_index.append(("personal", Path(self.settings.vault_personal_path)))
        
        for table_name, vault_path in vaults_to_index:
            if self._cancel_requested:
                break
                
            logger.info(f"Incremental index of {table_name} vault...")
            
            table = self.db.open_table(table_name)
            
            # Get existing file hashes
            try:
                existing = table.search().select(["file_path", "file_hash"]).limit(100000).to_list()
                existing_hashes = {r["file_path"]: r["file_hash"] for r in existing}
            except:
                existing_hashes = {}
            
            # List files (non-blocking)
            md_files = await self.list_markdown_files(vault_path)
            
            # Check each file
            files_checked = 0
            for md_file in md_files:
                if self._cancel_requested:
                    logger.info("Indexing cancelled by request")
                    break
                
                content = await self.read_file(md_file)
                if content is None:
                    continue
                
                # Compute hash in thread pool
                loop = asyncio.get_event_loop()
                current_hash = await loop.run_in_executor(
                    _executor,
                    lambda c: hashlib.md5(c.encode()).hexdigest(),
                    content
                )
                
                file_path_str = str(md_file)
                
                # Skip if unchanged
                if file_path_str in existing_hashes:
                    if existing_hashes[file_path_str] == current_hash:
                        continue
                
                # Index new/modified file
                count = await self.index_file(md_file, table_name)
                total_indexed += count
                
                files_checked += 1
                # Yield every 10 files
                if files_checked % 10 == 0:
                    await asyncio.sleep(0)
        
        logger.info(f"Incremental index complete: {total_indexed} chunks")
        return total_indexed
