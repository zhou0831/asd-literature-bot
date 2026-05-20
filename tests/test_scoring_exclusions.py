from src.models import LiteratureItem
from src.scoring import score_items, score_item


def test_generic_ai_diagnosis_review_is_low_fit():
    review = score_item(
        LiteratureItem(
            title="Artificial intelligence in Autism Spectrum Disorder diagnosis of Visual Attention and Facial Recognition: A Scoping Review",
            abstract=(
                "This scoping review maps AI diagnosis, visual attention, facial recognition, "
                "autism, children, eye tracking and machine learning classification."
            ),
        )
    )
    core = score_item(
        LiteratureItem(
            title="False-belief anticipatory looking in autistic children using a child-friendly cartoon task",
            abstract="Autistic children completed a theory of mind anticipatory looking task.",
        )
    )
    ranked = score_items([review, core])
    assert review.topic_fit_score < 50
    assert "generic_ai_diagnosis" in review.penalty_reasons or "facial_recognition_only" in review.penalty_reasons
    assert ranked[0].title == core.title


def test_eye_tracking_joint_attention_is_not_penalized():
    item = score_item(
        LiteratureItem(
            title="Eye-tracking evidence for joint attention and gesture cueing in autistic children",
            abstract="The study measured gaze cueing and joint attention during social communication.",
        )
    )
    assert item.module == "A"
    assert item.topic_fit_score >= 50
    assert item.strong_exclusion is False


def test_social_attribution_moving_shapes_scores_high():
    item = score_item(
        LiteratureItem(
            title="Children's social attribution in moving shapes: evidence from Frith-Happe triangles",
            abstract="Animated shapes were used to study social attribution in autistic children.",
        )
    )
    assert item.module == "C"
    assert item.topic_fit_score >= 50


def test_false_belief_anticipatory_looking_scores_high():
    item = score_item(
        LiteratureItem(
            title="False-belief anticipatory looking in autistic children using a child-friendly cartoon task",
            abstract="The cartoon task assessed theory of mind and anticipatory looking.",
        )
    )
    assert item.module == "C"
    assert item.topic_fit_score >= 50
