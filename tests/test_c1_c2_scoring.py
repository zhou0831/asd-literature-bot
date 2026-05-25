from src.models import LiteratureItem
from src.scoring import score_item


def test_c1_moving_shapes_sat_mc_scores_high():
    item = score_item(
        LiteratureItem(
            title="SAT-MC moving shapes task for social attribution in autistic children",
            abstract="The modified social attribution task used animated triangles and Heider-Simmel style chasing and helping events.",
        )
    )

    assert item.module == "C1"
    assert item.topic_fit_score >= 50
    assert item.reading_priority in {"deep_read", "skim"}


def test_c2_catoon_false_belief_scores_high():
    item = score_item(
        LiteratureItem(
            title="CAToon false belief and belief-consistent looking in autistic children",
            abstract="The choose-the-ending task tested knowledge difference, hidden object reasoning, and preferential looking.",
        )
    )

    assert item.module == "C2"
    assert item.topic_fit_score >= 50
    assert item.reading_priority in {"deep_read", "skim"}


def test_broad_tom_language_proficiency_does_not_score_as_core_c():
    item = score_item(
        LiteratureItem(
            title="Language proficiency and theory of mind in autistic children",
            abstract="This longitudinal study examined language proficiency and broad theory of mind outcomes using parent questionnaires and vocabulary scores.",
        )
    )

    assert item.topic_fit_score < 50
    assert item.recommendation_tier != "core"
