from src.models import LiteratureItem
from src.scoring import score_item


def test_ai_diagnosis_facial_recognition_review_is_excluded():
    item = score_item(
        LiteratureItem(
            title="Artificial intelligence in Autism Spectrum Disorder diagnosis of Visual Attention and Facial Recognition",
            abstract="This review covers AI diagnosis, facial recognition, visual attention diagnosis, and broad ASD classification.",
        )
    )

    assert item.strong_exclusion is True
    assert item.reading_priority == "exclude"


def test_home_based_language_strategy_is_not_deep_read():
    item = score_item(
        LiteratureItem(
            title="Home-based language strategy intervention for autistic children",
            abstract="Parents delivered a home-based intervention strategy focused on language development and speech therapy.",
        )
    )

    assert item.reading_priority in {"defer", "exclude"}
    assert item.reading_priority != "deep_read"


def test_adhd_ern_erp_is_not_b_core():
    item = score_item(
        LiteratureItem(
            title="Error-related negativity and error monitoring in ADHD",
            abstract="This generic ERP biomarker study measured ERN during error monitoring in ADHD children.",
        )
    )

    assert item.module != "B"
    assert item.recommendation_tier != "core"
    assert item.reading_priority in {"defer", "exclude"}


def test_response_commentary_is_not_deep_read():
    item = score_item(
        LiteratureItem(
            title="Response to comments on mentalizing in autistic children",
            abstract="A response commentary without new task design, stimulus materials, or eye-tracking measures.",
        )
    )

    assert item.reading_priority in {"defer", "exclude"}
    assert item.reading_priority != "deep_read"
