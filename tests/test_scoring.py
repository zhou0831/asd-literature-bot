from src.models import LiteratureItem
from src.scoring import score_items


def test_scoring_sorts_relevant_items_first():
    low = LiteratureItem(title="General child development")
    high = LiteratureItem(
        title="Autistic children use gaze cueing during dynamic social intention action prediction",
        abstract="EEG and eye tracking study of theory of mind.",
        doi="10.1000/high",
    )
    ranked = score_items([low, high])
    assert ranked[0].title == high.title
    assert ranked[0].score > ranked[1].score

