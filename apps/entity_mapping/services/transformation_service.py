"""
Transformation Service for Entity Mapping System

Converts RDF/Fuseki metadata into Django model-ready data structures.
Provides validation, error handling, and data quality assurance.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import re
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.text import slugify


@dataclass
class ValidationResult:
    """Result of validation with detailed feedback"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Dict[str, Any]

    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)

    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


class BaseTransformer(ABC):
    """
    Base class for entity transformers.
    All entity-specific transformers inherit from this class.
    """

    entity_type: str = None  # Override in subclasses
    required_fields: List[str] = []  # Override in subclasses
    optional_fields: List[str] = []  # Override in subclasses

    def __init__(self, fuseki_metadata: Dict[str, Any]):
        """
        Initialize transformer with Fuseki metadata

        Args:
            fuseki_metadata: Raw metadata from Fuseki entity
        """
        self.fuseki_metadata = fuseki_metadata
        self.validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            cleaned_data={}
        )

    def transform(self) -> ValidationResult:
        """
        Main transformation method - validates and transforms data

        Returns:
            ValidationResult with cleaned data or errors
        """
        # Step 1: Validate required fields
        self._validate_required_fields()

        if self.validation_result.has_errors():
            return self.validation_result

        # Step 2: Extract and clean fields
        self._extract_fields()

        # Step 3: Entity-specific transformation
        self._transform_entity_specific()

        # Step 4: Final validation
        self._validate_final_data()

        return self.validation_result

    def _validate_required_fields(self):
        """Validate that all required fields are present"""
        for field in self.required_fields:
            if field not in self.fuseki_metadata or not self.fuseki_metadata.get(field):
                self.validation_result.add_error(
                    f"Required field '{field}' is missing or empty"
                )

    @abstractmethod
    def _extract_fields(self):
        """Extract and clean fields - implement in subclasses"""
        pass

    @abstractmethod
    def _transform_entity_specific(self):
        """Entity-specific transformation logic - implement in subclasses"""
        pass

    def _validate_final_data(self):
        """Final validation of cleaned data"""
        # Check that we have at least a label
        if not self.validation_result.cleaned_data.get('label'):
            self.validation_result.add_error("Label is required but not set")

    def _clean_label(self, label: str) -> str:
        """Clean and normalize label text"""
        if not label:
            return ""
        # Remove excessive whitespace
        label = re.sub(r'\s+', ' ', label.strip())
        # Limit length
        if len(label) > 255:
            self.validation_result.add_warning(
                f"Label truncated from {len(label)} to 255 characters"
            )
            label = label[:255]
        return label

    def _clean_uri(self, uri: str) -> Optional[str]:
        """Validate and clean URI"""
        if not uri:
            return None

        uri = uri.strip()
        validator = URLValidator()
        try:
            validator(uri)
            return uri
        except ValidationError:
            self.validation_result.add_warning(
                f"Invalid URI format: {uri}"
            )
            return None

    def _generate_slug(self, label: str) -> str:
        """Generate slug from label"""
        slug = slugify(label)[:255]
        if not slug:
            self.validation_result.add_warning("Could not generate slug from label")
            return "unknown"
        return slug

    def _extract_text_field(self, field_name: str, max_length: int = 255) -> Optional[str]:
        """
        Extract and clean a text field from metadata

        Args:
            field_name: Name of the field to extract
            max_length: Maximum length of the text

        Returns:
            Cleaned text or None
        """
        value = self.fuseki_metadata.get(field_name)
        if not value:
            return None

        # Handle list values (take first)
        if isinstance(value, list):
            value = value[0] if value else None

        if not value:
            return None

        # Convert to string and clean
        value = str(value).strip()

        # Remove excessive whitespace
        value = re.sub(r'\s+', ' ', value)

        # Truncate if needed
        if len(value) > max_length:
            self.validation_result.add_warning(
                f"Field '{field_name}' truncated from {len(value)} to {max_length} characters"
            )
            value = value[:max_length]

        return value if value else None


class LicenseTransformer(BaseTransformer):
    """
    Transformer for License entities
    Maps Fuseki license data to curation.License model
    """

    entity_type = "license"
    required_fields = ["label"]
    optional_fields = ["uri", "spdx_id", "spdxId"]

    def _extract_fields(self):
        """Extract license-specific fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            # Try alternative field names
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

        # Extract SPDX ID
        spdx_id = self._extract_text_field("spdx_id", max_length=64)
        if not spdx_id:
            spdx_id = self._extract_text_field("spdxId", max_length=64)

        if spdx_id:
            self.validation_result.cleaned_data['spdx_id'] = spdx_id

    def _transform_entity_specific(self):
        """License-specific transformation"""
        # Generate slug
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Validate SPDX ID format if present
        spdx_id = self.validation_result.cleaned_data.get('spdx_id')
        if spdx_id:
            # SPDX IDs typically follow pattern: MIT, GPL-3.0, CC-BY-4.0, etc.
            if not re.match(r'^[\w\-\.]+$', spdx_id):
                self.validation_result.add_warning(
                    f"SPDX ID '{spdx_id}' has unusual format"
                )


class LearningResourceTypeTransformer(BaseTransformer):
    """
    Transformer for Learning Resource Type entities
    Maps Fuseki learning resource type data to curation.LearningResourceType model
    """

    entity_type = "learning_resource_type"
    required_fields = ["label"]
    optional_fields = ["uri", "description"]

    def _extract_fields(self):
        """Extract learning resource type fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

    def _transform_entity_specific(self):
        """Learning resource type specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Common learning resource types validation
        known_types = [
            'course', 'tutorial', 'dataset', 'software', 'publication',
            'presentation', 'video', 'documentation', 'workshop', 'webinar'
        ]
        label_lower = label.lower()
        if not any(known_type in label_lower for known_type in known_types):
            self.validation_result.add_warning(
                f"Learning resource type '{label}' is not a commonly recognized type"
            )


class ProficiencyLevelTransformer(BaseTransformer):
    """
    Transformer for Proficiency Level entities
    Maps Fuseki proficiency level data to curation.ProficiencyLevel model
    """

    entity_type = "proficiency_level"
    required_fields = ["label"]
    optional_fields = ["uri", "description"]

    def _extract_fields(self):
        """Extract proficiency level fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

    def _transform_entity_specific(self):
        """Proficiency level specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Common proficiency levels validation
        known_levels = ['beginner', 'intermediate', 'advanced', 'expert', 'novice', 'master']
        label_lower = label.lower()
        if not any(level in label_lower for level in known_levels):
            self.validation_result.add_warning(
                f"Proficiency level '{label}' is not a commonly recognized level"
            )


class TargetGroupTransformer(BaseTransformer):
    """
    Transformer for Target Group entities
    Maps Fuseki target group data to curation.TargetGroup model
    """

    entity_type = "target_group"
    required_fields = ["label"]
    optional_fields = ["uri", "description"]

    def _extract_fields(self):
        """Extract target group fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

    def _transform_entity_specific(self):
        """Target group specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Common target groups validation
        known_groups = [
            'researchers', 'students', 'practitioners', 'educators',
            'professionals', 'academics', 'undergraduates', 'graduates',
            'postdocs', 'faculty', 'industry'
        ]
        label_lower = label.lower()
        if not any(group in label_lower for group in known_groups):
            self.validation_result.add_warning(
                f"Target group '{label}' is not a commonly recognized group"
            )


class FileFormatTransformer(BaseTransformer):
    """
    Transformer for File Format entities
    Maps Fuseki file format data to curation.FileFormat model
    """

    entity_type = "file_format"
    required_fields = ["label"]
    optional_fields = ["uri", "mime_type", "extension"]

    def _extract_fields(self):
        """Extract file format fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

    def _transform_entity_specific(self):
        """File format specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Common file formats validation
        known_formats = [
            'pdf', 'csv', 'json', 'xml', 'html', 'txt', 'doc', 'docx',
            'xls', 'xlsx', 'zip', 'tar', 'gz', 'png', 'jpg', 'jpeg',
            'gif', 'svg', 'mp4', 'avi', 'mp3', 'wav'
        ]
        label_lower = label.lower()
        if not any(fmt in label_lower for fmt in known_formats):
            self.validation_result.add_warning(
                f"File format '{label}' is not a commonly recognized format"
            )


class MediaTypeTransformer(BaseTransformer):
    """
    Transformer for Media Type entities
    Maps Fuseki media type data to curation.MediaType model
    """

    entity_type = "media_type"
    required_fields = ["label"]
    optional_fields = ["uri", "description"]

    def _extract_fields(self):
        """Extract media type fields"""
        # Extract label
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

    def _transform_entity_specific(self):
        """Media type specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Common media types validation
        known_types = [
            'text', 'video', 'audio', 'image', 'interactive', 'dataset',
            'application', 'software', 'simulation', 'game'
        ]
        label_lower = label.lower()
        if not any(media_type in label_lower for media_type in known_types):
            self.validation_result.add_warning(
                f"Media type '{label}' is not a commonly recognized type"
            )


class LanguageTransformer(BaseTransformer):
    """
    Transformer for Language entities
    Maps Fuseki language data to curation.Language model
    URI pattern: http://lexvo.org/id/iso639-3/LANGUAGE_CODE
    """

    entity_type = "language"
    required_fields = ["label"]  # 'value' (URI) is passed separately as fuseki_uri
    optional_fields = ["native_name", "description", "code", "uri"]

    def _extract_fields(self):
        """Extract language fields"""
        # Extract label (e.g., "English", "German")
        label = self._extract_text_field("label")
        if not label:
            label = self._extract_text_field("name")

        if label:
            self.validation_result.cleaned_data['label'] = self._clean_label(label)

        # Extract URI - try multiple sources
        # Note: The URI is typically in fuseki_uri from EntityMapping, not in metadata
        uri = self._extract_text_field("uri", max_length=500)
        if not uri:
            uri = self._extract_text_field("value", max_length=500)

        uri = self._clean_uri(uri)
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

        # Extract code if provided in metadata
        code = self._extract_text_field("code", max_length=10)
        if code:
            self.validation_result.cleaned_data['code'] = code

        # Extract native_name if available
        native_name = self._extract_text_field("native_name", max_length=100)
        if native_name:
            self.validation_result.cleaned_data['native_name'] = native_name

    def _transform_entity_specific(self):
        """Language-specific transformation"""
        label = self.validation_result.cleaned_data.get('label', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(label)

        # Extract ISO code from URI
        # Pattern: http://lexvo.org/id/iso639-3/LANGUAGE_CODE
        uri = self.validation_result.cleaned_data.get('uri', '')
        code = self._extract_language_code_from_uri(uri)

        if code:
            self.validation_result.cleaned_data['code'] = code
        else:
            # If no code found, generate from slug as fallback
            slug = self.validation_result.cleaned_data.get('slug', '')
            self.validation_result.cleaned_data['code'] = slug[:10]  # max_length=10
            self.validation_result.add_warning(
                f"Could not extract language code from URI, using slug: {slug[:10]}"
            )

        # If native_name not provided, use label as fallback
        if 'native_name' not in self.validation_result.cleaned_data:
            self.validation_result.cleaned_data['native_name'] = label

    def _extract_language_code_from_uri(self, uri: str) -> Optional[str]:
        """
        Extract language code from Lexvo URI.

        Examples:
          http://lexvo.org/id/iso639-3/aar -> aar
          http://lexvo.org/id/iso639-1/en -> en

        Args:
            uri: Lexvo URI

        Returns:
            Language code or None
        """
        if not uri:
            return None

        # Pattern: http://lexvo.org/id/iso639-X/CODE
        import re
        match = re.search(r'/iso639-[0-9]/([a-zA-Z]{2,3})$', uri)
        if match:
            return match.group(1).lower()

        # Try extracting last segment as fallback
        parts = uri.rstrip('/').split('/')
        if parts:
            last_part = parts[-1]
            # Validate it looks like a language code (2-3 letters)
            if re.match(r'^[a-zA-Z]{2,3}$', last_part):
                return last_part.lower()

        return None


class CommunityTransformer(BaseTransformer):
    """
    Transformer for Community entities
    Maps Fuseki community data to curation.Community model

    Note: Fuseki provides "label" which we map to "title" for the Community model
    """

    entity_type = "community"
    required_fields = ["label"]  # Fuseki uses "label", we map it to "title"
    optional_fields = ["uri", "description", "moderation_policy"]

    def _extract_fields(self):
        """Extract community fields"""
        # Extract title (communities use 'title' instead of 'label')
        title = self._extract_text_field("title")
        if not title:
            # Try alternative field names
            title = self._extract_text_field("label")
        if not title:
            title = self._extract_text_field("name")

        if title:
            cleaned_title = self._clean_label(title)
            self.validation_result.cleaned_data['title'] = cleaned_title
        else:
            self.validation_result.add_error("Community title is required")

        # Extract URI
        uri = self._clean_uri(self._extract_text_field("uri", max_length=500))
        if uri:
            self.validation_result.cleaned_data['uri'] = uri

        # Extract description
        description = self._extract_text_field("description", max_length=5000)
        if description:
            self.validation_result.cleaned_data['description'] = description

        # Extract moderation policy
        moderation_policy = self._extract_text_field("moderation_policy", max_length=5000)
        if moderation_policy:
            self.validation_result.cleaned_data['moderation_policy'] = moderation_policy

    def _transform_entity_specific(self):
        """Community specific transformation"""
        title = self.validation_result.cleaned_data.get('title', '')
        self.validation_result.cleaned_data['slug'] = self._generate_slug(title)

        # Set default governance values
        if 'auto_publish_threshold' not in self.validation_result.cleaned_data:
            self.validation_result.cleaned_data['auto_publish_threshold'] = 2

        if 'requires_approval' not in self.validation_result.cleaned_data:
            self.validation_result.cleaned_data['requires_approval'] = True

    def _validate_final_data(self):
        """Override: Community uses 'title' instead of 'label'"""
        if not self.validation_result.cleaned_data.get('title'):
            self.validation_result.add_error("Title is required but not set")

        # Validate title uniqueness will be handled at database level


class TransformationService:
    """
    Main service for transforming Fuseki entities to Django model data.
    Provides factory method to get appropriate transformer for each entity type.
    """

    # Mapping of entity types to transformer classes
    TRANSFORMERS = {
        'license': LicenseTransformer,
        'learning_resource_type': LearningResourceTypeTransformer,
        'proficiency_level': ProficiencyLevelTransformer,
        'target_group': TargetGroupTransformer,
        'file_format': FileFormatTransformer,
        'media_type': MediaTypeTransformer,
        'language': LanguageTransformer,
        'community': CommunityTransformer,
    }

    @classmethod
    def get_transformer(cls, entity_type: str, fuseki_metadata: Dict[str, Any]) -> Optional[BaseTransformer]:
        """
        Get appropriate transformer for entity type

        Args:
            entity_type: Type of entity to transform
            fuseki_metadata: Raw metadata from Fuseki

        Returns:
            Transformer instance or None if entity type not supported
        """
        transformer_class = cls.TRANSFORMERS.get(entity_type)
        if not transformer_class:
            return None

        return transformer_class(fuseki_metadata)

    @classmethod
    def transform_entity(cls, entity_type: str, fuseki_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Transform entity metadata to Django model data

        Args:
            entity_type: Type of entity to transform
            fuseki_metadata: Raw metadata from Fuseki

        Returns:
            ValidationResult with cleaned data or errors
        """
        transformer = cls.get_transformer(entity_type, fuseki_metadata)

        if not transformer:
            result = ValidationResult(
                is_valid=False,
                errors=[f"No transformer available for entity type '{entity_type}'"],
                warnings=[],
                cleaned_data={}
            )
            return result

        return transformer.transform()

    @classmethod
    def supported_entity_types(cls) -> List[str]:
        """Get list of supported entity types"""
        return list(cls.TRANSFORMERS.keys())

    @classmethod
    def validate_entity(cls, entity_type: str, fuseki_metadata: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate entity metadata without full transformation

        Args:
            entity_type: Type of entity to validate
            fuseki_metadata: Raw metadata from Fuseki

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        result = cls.transform_entity(entity_type, fuseki_metadata)
        return (result.is_valid, result.errors, result.warnings)