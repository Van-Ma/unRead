import uuid
import datetime
from typing import Optional, List, Any, Union
import tempfile
import os
from langchain import db_connection

class ContextFile:
    def __init__(
        self,
        chat_id: str,
        file_name: str,
        file_content: bytes,
        mime_type: Optional[str] = None,
        vector: Optional[List[float]] = None,
        file_id: Optional[str] = None,
        created_at: Optional[datetime.datetime] = None,
    ):
        self.chat_id = chat_id
        self.file_id = file_id or str(uuid.uuid4())
        self.file_name = file_name
        self.file_content = file_content
        self.mime_type = mime_type
        self.vector = vector
        self.created_at = created_at or datetime.datetime.utcnow()
        

class ContextManager:
    def __init__(self):
        self.db = db_connection

    def parse_file_to_text(self, file: Any, mime_type: Optional[str] = None) -> str:
        """
        Parses an uploaded file-like object (e.g. Flask FileStorage) to plain text.
        Supports txt, pdf, docx, xlsx. Returns extracted string.
        """
        mime_type = mime_type or getattr(file, 'mimetype', '') or ''
        filename = getattr(file, 'filename', '') or 'tempfile'

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=True, suffix=os.path.splitext(filename)[1]) as tmp:
            file.save(tmp.name)  # Assumes `file` has .save() method like Flask FileStorage

            if mime_type.startswith('text/plain') or filename.endswith('.txt'):
                with open(tmp.name, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

            elif mime_type == 'application/pdf' or filename.endswith('.pdf'):
                try:
                    import pdfplumber
                    with pdfplumber.open(tmp.name) as pdf:
                        pages = [page.extract_text() or '' for page in pdf.pages]
                    return '\n'.join(pages)
                except ImportError:
                    raise RuntimeError("Please install pdfplumber (`pip install pdfplumber`)")

            elif (mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                  or filename.endswith('.docx')):
                try:
                    from docx import Document
                    doc = Document(tmp.name)
                    paragraphs = [p.text for p in doc.paragraphs]
                    return '\n'.join(paragraphs)
                except ImportError:
                    raise RuntimeError("Please install python-docx (`pip install python-docx`)")

            elif (mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                  or filename.endswith('.xlsx')):
                try:
                    import pandas as pd
                    df = pd.read_excel(tmp.name)
                    return df.to_csv(index=False)
                except ImportError:
                    raise RuntimeError("Please install pandas and openpyxl (`pip install pandas openpyxl`)")

            else:
                # Unsupported type, return empty string safely
                return ""

    def parse_and_create_context_file(
        self,
        user_id: str,
        chat_id: str,
        file: Any,
        mime_type: Optional[str] = None,
        vector: Optional[List[float]] = None,
    ) -> Optional[ContextFile]:
        """
        Parses the file content and creates a ContextFile instance.
        Returns None if parsing or user/project validation fails.
        """
        try:
            text_content = self.parse_file_to_text(file, mime_type)
            if not text_content.strip():
                # No content extracted, don't create context file
                return None

            # Encode to bytes for storage (or store as string if preferred)
            content_bytes = text_content.encode('utf-8')

            context_file = ContextFile(
                chat_id=chat_id,
                file_name=getattr(file, 'filename', 'unnamed'),
                file_content=content_bytes,
                mime_type=mime_type or getattr(file, 'mimetype', None),
                vector=vector,
            )
            return context_file
        except Exception:
            # Log internally if you want
            return None

    def save_context_file(self, user_id: str, context_file: ContextFile) -> bool:
        """
        Save a context file only if the project belongs to the user.
        """
        try:
            with self.db.cursor() as cur:
                sql = """
                INSERT INTO context_files (file_id, chat_id, file_name, file_content, mime_type, vector, created_at)
                SELECT %s, %s, %s, %s, %s, %s::vector, %s
                FROM projects
                WHERE chat_id = %s AND user_id = %s
                """
                cur.execute(
                    sql,
                    (
                        context_file.file_id,
                        context_file.chat_id,
                        context_file.file_name,
                        context_file.file_content,
                        context_file.mime_type,
                        context_file.vector,
                        context_file.created_at,
                        context_file.chat_id,
                        user_id,
                    )
                )
                if cur.rowcount == 0:
                    self.db.rollback()
                    return False
                self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def get_context_files(self, user_id: str, chat_id: str, include_content: bool = True) -> List[ContextFile]:
        """
        Retrieve all context files for a given project and user.
        """
        files = []
        try:
            with self.db.cursor() as cur:
                content_field = "file_content" if include_content else "NULL AS file_content"
                sql = f"""
                SELECT cf.file_id, cf.chat_id, cf.file_name, {content_field}, cf.mime_type, cf.vector, cf.created_at
                FROM context_files cf
                JOIN projects p ON cf.chat_id = p.chat_id
                WHERE cf.chat_id = %s AND p.user_id = %s
                """
                cur.execute(sql, (chat_id, user_id))
                rows = cur.fetchall()
                for row in rows:
                    file = ContextFile(
                        chat_id=row[1],
                        file_name=row[2],
                        file_content=row[3] if include_content else b'',
                        mime_type=row[4],
                        vector=row[5],
                        file_id=row[0],
                        created_at=row[6],
                    )
                    files.append(file)
        except Exception:
            pass
        return files
