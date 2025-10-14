"""
FHIR Clinical Note Service
Handles retrieval and text extraction from FHIR clinical note resources
(Composition and DocumentReference)
"""

from typing import Dict, List, Any, Optional
import structlog
import base64
import re
from html import unescape

from app.services.fhir.fhir_client import FhirClient, FhirClientError

logger = structlog.get_logger(__name__)


class FhirNoteService:
    """
    Service for working with FHIR clinical notes

    Handles:
    - Fetching Composition resources (structured clinical documents)
    - Fetching DocumentReference resources (document metadata + attachments)
    - Extracting text from HTML, Base64, and other formats
    - Combining multiple notes into a single clinical narrative
    """

    def __init__(self, fhir_client: FhirClient):
        """
        Initialize note service

        Args:
            fhir_client: Configured FhirClient instance
        """
        self.fhir_client = fhir_client

    async def fetch_clinical_notes(
        self,
        encounter_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all clinical notes associated with an encounter

        Queries both Composition and DocumentReference resources

        Args:
            encounter_id: FHIR Encounter ID

        Returns:
            List of clinical note dictionaries with metadata and text
        """
        logger.info("fetch_clinical_notes", encounter_id=encounter_id)

        notes = []

        # Fetch Composition resources
        try:
            compositions = await self._fetch_compositions(encounter_id)
            for composition in compositions:
                note = self._process_composition(composition)
                if note:
                    notes.append(note)
        except FhirClientError as e:
            logger.warning(
                "fetch_compositions_failed",
                encounter_id=encounter_id,
                error=str(e),
            )

        # Fetch DocumentReference resources
        try:
            document_refs = await self._fetch_document_references(encounter_id)
            for doc_ref in document_refs:
                note = await self._process_document_reference(doc_ref)
                if note:
                    notes.append(note)
        except FhirClientError as e:
            logger.warning(
                "fetch_document_references_failed",
                encounter_id=encounter_id,
                error=str(e),
            )

        logger.info(
            "fetch_clinical_notes_success",
            encounter_id=encounter_id,
            note_count=len(notes),
        )

        return notes

    async def _fetch_compositions(self, encounter_id: str) -> List[Dict[str, Any]]:
        """
        Fetch Composition resources for an encounter

        Args:
            encounter_id: FHIR Encounter ID

        Returns:
            List of Composition resources
        """
        # Search for compositions linked to this encounter
        params = {
            "encounter": f"Encounter/{encounter_id}",
            "_count": 100,  # Get up to 100 notes
        }

        compositions = await self.fhir_client.search_resources("Composition", params)

        logger.info(
            "fetch_compositions_success",
            encounter_id=encounter_id,
            count=len(compositions),
        )

        return compositions

    async def _fetch_document_references(self, encounter_id: str) -> List[Dict[str, Any]]:
        """
        Fetch DocumentReference resources for an encounter

        Args:
            encounter_id: FHIR Encounter ID

        Returns:
            List of DocumentReference resources
        """
        # Search for document references linked to this encounter
        params = {
            "encounter": f"Encounter/{encounter_id}",
            "_count": 100,
        }

        document_refs = await self.fhir_client.search_resources("DocumentReference", params)

        logger.info(
            "fetch_document_references_success",
            encounter_id=encounter_id,
            count=len(document_refs),
        )

        return document_refs

    def _process_composition(self, composition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a Composition resource and extract clinical note data

        Args:
            composition: FHIR Composition resource

        Returns:
            Dictionary with note metadata and text, or None if extraction fails
        """
        composition_id = composition.get("id")

        logger.info("process_composition", composition_id=composition_id)

        try:
            # Extract metadata
            metadata = self.get_note_metadata(composition)

            # Extract text from sections
            text = self.extract_note_text(composition)

            if not text or not text.strip():
                logger.warning(
                    "process_composition_no_text",
                    composition_id=composition_id,
                )
                return None

            return {
                "resource_type": "Composition",
                "resource_id": composition_id,
                "text": text,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(
                "process_composition_error",
                composition_id=composition_id,
                error=str(e),
            )
            return None

    async def _process_document_reference(
        self,
        document_ref: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Process a DocumentReference resource and extract clinical note data

        Args:
            document_ref: FHIR DocumentReference resource

        Returns:
            Dictionary with note metadata and text, or None if extraction fails
        """
        doc_ref_id = document_ref.get("id")

        logger.info("process_document_reference", doc_ref_id=doc_ref_id)

        try:
            # Extract metadata
            metadata = self.get_note_metadata(document_ref)

            # Extract text from attachment
            text = self.extract_note_text(document_ref)

            if not text or not text.strip():
                logger.warning(
                    "process_document_reference_no_text",
                    doc_ref_id=doc_ref_id,
                )
                return None

            return {
                "resource_type": "DocumentReference",
                "resource_id": doc_ref_id,
                "text": text,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(
                "process_document_reference_error",
                doc_ref_id=doc_ref_id,
                error=str(e),
            )
            return None

    def extract_note_text(self, resource: Dict[str, Any]) -> str:
        """
        Extract clinical note text from FHIR resource

        Handles:
        - Composition.section[].text.div (HTML)
        - DocumentReference.content[].attachment.data (Base64)
        - DocumentReference.content[].attachment.url (reference)

        Args:
            resource: FHIR Composition or DocumentReference resource

        Returns:
            Extracted text content
        """
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")

        logger.info(
            "extract_note_text",
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == "Composition":
            return self._extract_text_from_composition(resource)
        elif resource_type == "DocumentReference":
            return self._extract_text_from_document_reference(resource)
        else:
            logger.warning(
                "extract_note_text_unsupported_type",
                resource_type=resource_type,
                resource_id=resource_id,
            )
            return ""

    def _extract_text_from_composition(self, composition: Dict[str, Any]) -> str:
        """
        Extract text from Composition.section[].text.div

        FHIR Composition sections contain narrative HTML in text.div field

        Args:
            composition: FHIR Composition resource

        Returns:
            Combined text from all sections
        """
        sections = composition.get("section", [])

        if not sections:
            logger.warning(
                "extract_composition_text_no_sections",
                composition_id=composition.get("id"),
            )
            return ""

        text_parts = []

        for section in sections:
            # Get section title
            title = section.get("title", "")
            if title:
                text_parts.append(f"\n{title}\n{'=' * len(title)}\n")

            # Get section text (HTML narrative)
            text_element = section.get("text", {})
            div_html = text_element.get("div", "")

            if div_html:
                # Convert HTML to plain text
                plain_text = self._html_to_text(div_html)
                text_parts.append(plain_text)

            # Recursively process subsections
            subsections = section.get("section", [])
            if subsections:
                for subsection in subsections:
                    subsection_title = subsection.get("title", "")
                    if subsection_title:
                        text_parts.append(f"\n{subsection_title}\n{'-' * len(subsection_title)}\n")

                    subsection_text = subsection.get("text", {}).get("div", "")
                    if subsection_text:
                        plain_text = self._html_to_text(subsection_text)
                        text_parts.append(plain_text)

        return "\n".join(text_parts).strip()

    def _extract_text_from_document_reference(self, document_ref: Dict[str, Any]) -> str:
        """
        Extract text from DocumentReference.content[].attachment

        Handles Base64-encoded text attachments

        Args:
            document_ref: FHIR DocumentReference resource

        Returns:
            Extracted text
        """
        content_list = document_ref.get("content", [])

        if not content_list:
            logger.warning(
                "extract_document_reference_text_no_content",
                doc_ref_id=document_ref.get("id"),
            )
            return ""

        text_parts = []

        for content in content_list:
            attachment = content.get("attachment", {})

            # Check for inline Base64 data
            base64_data = attachment.get("data")
            if base64_data:
                try:
                    # Decode Base64
                    decoded_bytes = base64.b64decode(base64_data)
                    decoded_text = decoded_bytes.decode("utf-8", errors="ignore")

                    # Check if it's HTML
                    content_type = attachment.get("contentType", "")
                    if "html" in content_type.lower():
                        decoded_text = self._html_to_text(decoded_text)

                    text_parts.append(decoded_text)

                except Exception as e:
                    logger.error(
                        "extract_document_reference_base64_decode_error",
                        doc_ref_id=document_ref.get("id"),
                        error=str(e),
                    )
                    continue

            # Check for URL reference
            url = attachment.get("url")
            if url and not base64_data:
                # URL reference - would need to fetch separately
                # For now, log and skip
                logger.info(
                    "extract_document_reference_url_reference",
                    doc_ref_id=document_ref.get("id"),
                    url=url,
                    message="URL attachments not yet supported",
                )

        return "\n".join(text_parts).strip()

    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text

        Removes HTML tags and decodes HTML entities

        Args:
            html: HTML string

        Returns:
            Plain text
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)

        # Decode HTML entities
        text = unescape(text)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)  # Remove excessive blank lines
        text = re.sub(r"[ \t]+", " ", text)  # Normalize spaces

        return text.strip()

    def get_note_metadata(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from clinical note resource

        Args:
            resource: FHIR Composition or DocumentReference resource

        Returns:
            Dictionary with note metadata
        """
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")

        metadata = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "note_type": None,
            "author": None,
            "date": None,
            "title": None,
        }

        if resource_type == "Composition":
            metadata.update(self._get_composition_metadata(resource))
        elif resource_type == "DocumentReference":
            metadata.update(self._get_document_reference_metadata(resource))

        return metadata

    def _get_composition_metadata(self, composition: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Composition resource"""
        metadata = {}

        # Title
        metadata["title"] = composition.get("title")

        # Date
        metadata["date"] = composition.get("date")

        # Type
        type_element = composition.get("type", {})
        type_coding = type_element.get("coding", [])
        if type_coding:
            metadata["note_type"] = type_coding[0].get("display") or type_coding[0].get("code")
        else:
            metadata["note_type"] = type_element.get("text")

        # Author (first author)
        authors = composition.get("author", [])
        if authors:
            author_ref = authors[0].get("reference", "")
            metadata["author"] = author_ref.split("/")[-1] if "/" in author_ref else author_ref

        return metadata

    def _get_document_reference_metadata(self, document_ref: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from DocumentReference resource"""
        metadata = {}

        # Description as title
        metadata["title"] = document_ref.get("description")

        # Date
        metadata["date"] = document_ref.get("date")

        # Type
        type_element = document_ref.get("type", {})
        type_coding = type_element.get("coding", [])
        if type_coding:
            metadata["note_type"] = type_coding[0].get("display") or type_coding[0].get("code")
        else:
            metadata["note_type"] = type_element.get("text")

        # Author (first author)
        authors = document_ref.get("author", [])
        if authors:
            author_ref = authors[0].get("reference", "")
            metadata["author"] = author_ref.split("/")[-1] if "/" in author_ref else author_ref

        return metadata

    def combine_notes(self, notes: List[Dict[str, Any]]) -> str:
        """
        Combine multiple clinical notes into a single text document

        Args:
            notes: List of note dictionaries from fetch_clinical_notes()

        Returns:
            Combined clinical narrative text
        """
        if not notes:
            return ""

        combined_parts = []

        for note in notes:
            metadata = note.get("metadata", {})
            text = note.get("text", "")

            if not text:
                continue

            # Add note header with metadata
            header_parts = []

            note_type = metadata.get("note_type")
            if note_type:
                header_parts.append(f"Note Type: {note_type}")

            title = metadata.get("title")
            if title:
                header_parts.append(f"Title: {title}")

            date = metadata.get("date")
            if date:
                header_parts.append(f"Date: {date}")

            author = metadata.get("author")
            if author:
                header_parts.append(f"Author: {author}")

            if header_parts:
                header = "\n".join(header_parts)
                combined_parts.append(f"\n{'=' * 80}\n{header}\n{'=' * 80}\n")

            combined_parts.append(text)

        return "\n\n".join(combined_parts).strip()
