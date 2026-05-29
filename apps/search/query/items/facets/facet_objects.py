from typing import Callable, Dict

from rdflib import DCTERMS, URIRef, XSD
from rdflib.term import Literal, Node

from search.rdf.namespace import MoDalia, SCHEMA, bibo, fabio, hcrt


class FacetObject:
    """
    Representation of a facet

    Warning:
    Create and use instances of this class with great care, especially inside data structures (lists, dictionaries,
    ...)! Instance identity via __eq__() and __hash__() is intentionally inherited from the object class and thus relies
    only on the object id.

    This class could not be rewritten as frozen dataclass because the items field is mutable (there are no frozen
    dicts).
    """
    def __init__(
            self,
            label: str,
            key: URIRef,
            predicate: URIRef,
            items: Dict[Node, str],
            selected_facet_initializer: Callable[[str], Node]
    ):
        self.label = label
        self.key = key
        self.predicate = predicate
        self.items = items
        self.selected_facet_initializer = selected_facet_initializer


TARGET_AUDIENCE_FACET = FacetObject(
    label="Target Group",
    key=MoDalia.TargetGroup,
    predicate=MoDalia.hasTargetGroup,
    items={
        MoDalia.StudentSchool: "Student (School)",
        MoDalia.BachelorStudent: "Bachelor Student",
        MoDalia.MastersStudent: "Master's Student",
        MoDalia.PhDStudent: "PhD Student",
        MoDalia.DataSteward: "Data Steward",
        MoDalia.TeacherSchool: "Teacher (School)",
        MoDalia.TeacherHighEducation: "Teacher (Higher Education)",
        MoDalia.Researcher: "Researcher",
        MoDalia.ContentProvider: "Content provider",
    },
    selected_facet_initializer=URIRef,
)

MEDIA_TYPE_FACET = FacetObject(
    label="Media Type",
    key=MoDalia.MediaType,
    predicate=MoDalia.hasMediaType,
    items={
        SCHEMA.AudioObject: "Audio",
        MoDalia.Code: "Code",
        SCHEMA.ImageObject: "Image",
        MoDalia.Multipart: "Multipart",
        SCHEMA.PresentationDigitalDocument: "Presentation",
        SCHEMA.Text: "Text",
        SCHEMA.VideoObject: "Video",
    },
    selected_facet_initializer=URIRef,
)

LEARNING_RESOURCE_TYPE_FACET = FacetObject(
    label="Learning Resource Type",
    key=MoDalia.LearningResourceType,
    predicate=MoDalia.hasLearningType,
    items={
        bibo.Article: "Article",
        hcrt.assessment: "Assessment",
        MoDalia.BestPractices: "Best Practices",
        bibo.Book: "Book",
        hcrt.case_study: "Case Study",
        SCHEMA.SoftwareSourceCode: "Code",
        MoDalia.CodeNotebook: "Code Notebook",
        MoDalia.Cookbook: "Cookbook",
        hcrt.course: "Course",
        hcrt.diagram: "Diagram",
        hcrt.drill_and_practice: "Drill and Practice",
        MoDalia.Lecture: "Lecture",
        hcrt.lesson_plan: "Lesson Plan",
        hcrt.other: "Other resource type",
        SCHEMA.PodcastSeries: "PodcastSeries",
        MoDalia.Poster: "Poster",
        hcrt.index: "Reference Work",
        bibo.Report: "Report",
        hcrt.textbook: "Textbook",
        MoDalia.Tutorial: "Tutorial",
        bibo.Webpage: "Web page",
        hcrt.worksheet: "Worksheet",
        MoDalia.Workshop: "Workshop",
    },
    selected_facet_initializer=URIRef,
)

LANGUAGE_FACET = FacetObject(
    label="Language",
    key=XSD.language,
    predicate=DCTERMS.language,
    items={
        URIRef("http://lexvo.org/id/iso639-3/eng"): "English",
        URIRef("http://lexvo.org/id/iso639-3/fra"): "French",
        URIRef("http://lexvo.org/id/iso639-3/deu"): "German",
        URIRef("http://lexvo.org/id/iso639-3/spa"): "Spanish",
    },
    selected_facet_initializer=URIRef,
)

PROFICIENCY_LEVEL_FACET = FacetObject(
    label="Proficiency Level",
    key=MoDalia.Proficiency,
    predicate=MoDalia.requiresProficiencyLevel,
    items={
        MoDalia.Novice: "Novice",
        MoDalia.Beginner: "Advanced Beginner",
        MoDalia.Competent: "Competent",
        MoDalia.Proficient: "Proficient",
        MoDalia.Expert: "Expert",
    },
    selected_facet_initializer=URIRef,
)

DISCIPLINE_FACET = FacetObject(
    label="Discipline",
    key=URIRef("http://purl.org/spar/fabio/Discipline"),
    predicate=fabio.hasDiscipline,
    items={
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n0"): "Interdisciplinary",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n1"): "Humanities",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n2"): "Sports",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n3"): "Law, Economics and Social Sciences",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n4"): "Mathematics, Natural Sciences",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n5"): "Human Medicine / Health Sciences",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n7"): "Agricultural, Forest and Nutritional Sciences, Veterinary medicine",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n8"): "Engineering Sciences",
        URIRef("https://w3id.org/kim/hochschulfaechersystematik/n9"): "Art, Art Theory",
    },
    selected_facet_initializer=URIRef,
)

LICENSE_FACET = FacetObject(
    label="License",
    key=URIRef("http://purl.org/dc/terms/LicenseDocument"),
    predicate=DCTERMS.license,
    items={
        MoDalia.ProprietaryLicense: "Proprietary",
        URIRef("http://spdx.org/licenses/CC0-1.0"): "CC0 1.0 (Public Domain)",
        URIRef("http://spdx.org/licenses/CC-BY-3.0"): "CC BY 3.0",
        URIRef("http://spdx.org/licenses/CC-BY-4.0"): "CC BY 4.0",
        URIRef("http://spdx.org/licenses/CC-BY-SA-3.0-DE"): "CC BY-SA 3.0 DE",
        URIRef("http://spdx.org/licenses/CC-BY-SA-4.0"): "CC BY-SA 4.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-2.0"): "CC BY-NC 2.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-4.0"): "CC BY-NC 4.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-SA-3.0"): "CC BY-NC-SA 3.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-SA-3.0-DE"): "CC BY-NC-SA 3.0 DE",
        URIRef("http://spdx.org/licenses/CC-BY-NC-SA-4.0"): "CC BY-NC-SA 4.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-ND-2.0"): "CC BY-NC-ND 2.0",
        URIRef("http://spdx.org/licenses/CC-BY-NC-ND-4.0"): "CC BY-NC-ND 4.0",
        URIRef("http://spdx.org/licenses/PDDL-1.0"): "PDDL 1.0",
        URIRef("http://spdx.org/licenses/MIT"): "MIT License",
        URIRef("http://spdx.org/licenses/Apache-2.0"): "Apache 2.0",
        URIRef("http://spdx.org/licenses/GPL-3.0-only"): "GPL 3.0",
        URIRef("http://spdx.org/licenses/BSD-2-Clause"): "BSD 2-Clause",
    },
    selected_facet_initializer=URIRef,
)

FILE_FORMAT_FACET = FacetObject(
    label="File Format",
    key=DCTERMS.FileFormat,
    predicate=DCTERMS.format,
    items={
        Literal("PDF"): "PDF",
        Literal("HTML"): "HTML",
        Literal("HMTL"): "HTML",  # Handle typo in data
        Literal("MD"): "Markdown",
        Literal("DOCX"): "Word Document",
        Literal("PPTX"): "PowerPoint",
        Literal("XLSX"): "Excel",
        Literal("XLXS"): "Excel",  # Handle typo in data
        Literal("ODP"): "OpenDocument Presentation",
        Literal("ZIP"): "ZIP Archive",
        Literal("JSON"): "JSON",
        Literal("TXT"): "Text",
        Literal("TEX"): "LaTeX",
        Literal("RTB"): "Rich Text",
        Literal("IPYNB"): "Jupyter Notebook",
        Literal("RMD"): "R Markdown",
        Literal("KEY"): "Keynote",
        Literal("NUMBERS"): "Numbers",
        Literal("GSHEET"): "Google Sheets",
        Literal("PNG"): "PNG Image",
        Literal("JPG"): "JPEG Image",
        Literal("MP4"): "MP4 Video",
        Literal("MP3"): "MP3 Audio",
        Literal("MBZ"): "Moodle Backup",
        Literal("YML"): "YAML",
    },
    selected_facet_initializer=Literal,
)

COMMUNITY_FACET = FacetObject(
    label="Community",
    key=MoDalia.Community,
    predicate=URIRef("https://dalia.education/hasCommunity"),  # This will need special handling
    items={
        URIRef("https://id.dalia.education/community/f6e6a7fc-552b-4d75-9fca-8e2b1b8ad624"): "FAIRagro",
        URIRef("https://id.dalia.education/community/aac7b1be-cf00-4fdc-a26a-e8e0e1410b18"): "NFDI4Biodiversity",
        URIRef("https://id.dalia.education/community/c5d22eff-ec20-409d-b8d3-aa4e9cc2d6cb"): "ELIXIR",
        URIRef("https://id.dalia.education/community/ca42e106-dc0e-44ae-bb87-417195fd7d39"): "KonsortSWD",
        URIRef("https://id.dalia.education/community/f010e202-91ed-4e27-9595-355ec352527e"): "Text+",
        URIRef("https://id.dalia.education/community/3dc37495-59bb-4505-851f-e09c5df8e356"): "Nationale Forschungsdateninfrastruktur (NFDI)",
        URIRef("https://id.dalia.education/community/7783f91b-2496-4c1b-97ef-9db578d237ca"): "NFDI4Cat",
        URIRef("https://id.dalia.education/community/bead62a8-c3c2-46d6-9eb1-ffeaba38d5bf"): "NFDI4Chem",
        URIRef("https://id.dalia.education/community/fa16b39f-4bc1-4f48-beaf-cbd030d5a7b4"): "DataPLANT",
        URIRef("https://id.dalia.education/community/4f646323-756e-41d0-bdb6-0767411a14b5"): "NFDI4Ing",
        URIRef("https://id.dalia.education/community/6a21dd4a-200c-44e3-85b8-68fb31d510af"): "NFDI4Culture",
        URIRef("https://id.dalia.education/community/827c6f33-4e30-4b29-826e-408d41075005"): "PANGAEA",
        URIRef("https://id.dalia.education/community/eb67b524-e912-4af0-82b8-720a84d11009"): "FAIRsFAIR",
        URIRef("https://id.dalia.education/community/7ecf1a3e-e377-4f5c-ac70-78d498951843"): "BERD@NFDI",
        URIRef("https://id.dalia.education/community/f5ab031c-777d-44c9-9244-f707d3cb9ddc"): "NFDI4Energy",
        URIRef("https://id.dalia.education/community/0957e041-54d9-4f72-812c-013fcc48c2f3"): "RADAR",
        URIRef("https://id.dalia.education/community/ead5f570-c467-402c-bf06-85b80920a7a9"): "FAIRmat",
        URIRef("https://id.dalia.education/community/17ae490c-466c-40ee-9e91-027bd062979d"): "NFDIxCS",
        URIRef("https://id.dalia.education/community/0393d642-340d-4641-8c1f-e9c8b27199bf"): "DAPHNE4NFDI",
        URIRef("https://id.dalia.education/community/8cd01866-7560-4701-ba4a-da3c939b9061"): "Base4NFDI",
        URIRef("https://id.dalia.education/community/51340f34-d6fc-4ed5-b37d-b00a4d6f663a"): "Data Carpentry",
        URIRef("https://id.dalia.education/community/6d469cf2-5b97-47a9-88e2-f2ca96456cd2"): "NFDI4BIOIMAGE",
        URIRef("https://id.dalia.education/community/d5a5a668-ba2c-4d70-a037-33137ffad786"): "MaRDI",
        URIRef("https://id.dalia.education/community/d4f4ac7d-58d0-42c0-a320-58fb6fcbbd70"): "NFDI-MatWerk",
        URIRef("https://id.dalia.education/community/6c357a15-95a9-43bc-ad88-8528aa1ac23d"): "NFDI4Microbiota",
        URIRef("https://id.dalia.education/community/616d9b09-1f05-4847-b269-510479dec39b"): "PUNCH4NFDI",
        URIRef("https://id.dalia.education/community/47b9d41c-2040-4986-afcb-8be1d54d49ca"): "OER.DigiChem.NRW",
        URIRef("https://id.dalia.education/community/7c45de27-5996-40b5-8e0e-24afdfe148e5"): "NFDI4Health",
        URIRef("https://id.dalia.education/community/72456510-c4a0-4121-984c-cb14acb23dfc"): "HeFDI - Hessische Forschungsdateninfrastrukturen",
        URIRef("https://id.dalia.education/community/d996c08b-e39d-49d0-a492-7cb30d99c2b7"): "Data Science Center of the University of Bremen",
        URIRef("https://id.dalia.education/community/e26f5af3-96e5-43ce-9e36-c61a1e513a1b"): "FDM-BB",
        URIRef("https://id.dalia.education/community/1441a407-fd44-4ed7-a15d-7a1eb37da39e"): "GHGA",
        URIRef("https://id.dalia.education/community/3b75e62d-5964-4a5b-b5e0-9e3f9be29a15"): "PUNCH Young Academy (PYA)",
        URIRef("https://id.dalia.education/community/2040c8ce-b62c-4cb7-be94-85cb8eeaa0f8"): "NFDI4DataScience",
        URIRef("https://id.dalia.education/community/977cd734-1e55-49d7-b0aa-444fd035c18e"): "RDMO",
        URIRef("https://id.dalia.education/community/2156f39a-e2f4-4386-893c-4ecf4e8a6630"): "NFDI4Earth",
        URIRef("https://id.dalia.education/community/d3d6ec0c-0c42-4ba3-9316-a99ed0b169c5"): "NFDI4Memory",
        URIRef("https://id.dalia.education/community/d746f9ec-6ae3-467d-ace6-54095dc60602"): "NFDI4Immuno",
    },
    selected_facet_initializer=URIRef,
)
