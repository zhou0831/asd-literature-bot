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
    assert item.module == "C1"
    assert item.topic_fit_score >= 50


def test_false_belief_anticipatory_looking_scores_high():
    item = score_item(
        LiteratureItem(
            title="False-belief anticipatory looking in autistic children using a child-friendly cartoon task",
            abstract="The cartoon task assessed theory of mind and anticipatory looking.",
        )
    )
    assert item.module == "C2"
    assert item.topic_fit_score >= 50


def test_ai_diagnosis_facial_recognition_review_is_strong_exclusion():
    item = score_item(
        LiteratureItem(
            title="Artificial intelligence in Autism Spectrum Disorder diagnosis of Visual Attention and Facial Recognition: A Scoping Review",
            abstract="AI diagnosis and machine learning classification of visual attention and facial recognition in autism.",
        )
    )
    assert item.strong_exclusion is True
    assert item.reading_priority == "exclude"


def test_adhd_ern_eeg_is_not_b_module_core():
    item = score_item(
        LiteratureItem(
            title="Error-related negativity and error monitoring in ADHD children",
            abstract="This ERP biomarker study measured ERN during error monitoring in ADHD.",
        )
    )
    assert item.module != "B"
    assert item.strong_exclusion is True
    assert item.reading_priority == "exclude"


def test_joint_attention_eye_tracking_battery_can_be_a_skim_core_candidate():
    item = score_item(
        LiteratureItem(
            title="Towards the ecological automated measurement of joint attention: Development of an interactive eye-tracking battery for joint attention in children with and without autism",
            abstract="",
        )
    )
    assert item.module == "A"
    assert item.recommendation_tier == "core"
    assert item.reading_priority == "skim"


def test_sat_mc_social_attribution_scores_high():
    item = score_item(
        LiteratureItem(
            title="SAT-MC moving shapes task for social attribution in autistic children",
            abstract="The mSAT and Heider-Simmel style animated shapes measured social attribution.",
        )
    )
    assert item.module == "C1"
    assert item.topic_fit_score >= 50


def test_catoon_false_belief_scores_high():
    item = score_item(
        LiteratureItem(
            title="CAToon false belief and belief-consistent looking in autistic children",
            abstract="A choose-the-ending cartoon task measured knowledge difference and belief reasoning.",
        )
    )
    assert item.module == "C2"
    assert item.topic_fit_score >= 50
