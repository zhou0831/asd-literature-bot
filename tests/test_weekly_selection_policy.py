from src.models import LiteratureItem
from src.summarize import select_weekly_top


def test_home_based_language_strategy_does_not_enter_weekly_top3():
    language = LiteratureItem(
        title="Home-based language strategy intervention for autistic children",
        abstract="A home-based intervention strategy for language development and speech therapy.",
        recommendation_score=99,
        topic_fit_score=99,
        recommendation_tier="background",
        reading_priority="exclude",
        strong_exclusion=True,
        penalty_reasons=["language_intervention_only"],
        module="方法学",
    )
    core = LiteratureItem(
        title="Joint attention eye-tracking task in autistic children",
        abstract="Interactive eye-tracking measured joint attention and gaze cueing.",
        recommendation_score=60,
        topic_fit_score=55,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="A",
    )

    top = select_weekly_top([language, core])

    assert core in top
    assert language not in top


def test_weekly_top3_not_only_recommendation_score():
    high_bad = LiteratureItem(
        title="Generic AI classification for ASD diagnosis",
        abstract="Machine learning classification and AI diagnosis without social cognition tasks.",
        recommendation_score=100,
        topic_fit_score=10,
        recommendation_tier="background",
        reading_priority="exclude",
        strong_exclusion=True,
        penalty_reasons=["generic_ai_diagnosis", "generic_classification"],
        module="综述",
    )
    lower_good = LiteratureItem(
        title="False belief CAToon task in autistic children",
        abstract="Belief reasoning and belief-consistent looking in a child-friendly cartoon task.",
        recommendation_score=58,
        topic_fit_score=52,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="C2",
    )

    top = select_weekly_top([high_bad, lower_good])

    assert top[0] is lower_good


def test_adhd_ern_does_not_enter_weekly_top3():
    adhd = LiteratureItem(
        title="Error-related negativity and error monitoring in ADHD",
        abstract="This ERP biomarker study measured ERN during error monitoring.",
        recommendation_score=95,
        recommendation_tier="background",
        reading_priority="exclude",
        strong_exclusion=True,
        penalty_reasons=["adhd_error_monitoring_only", "generic_erp_biomarker"],
        module="方法学",
    )
    good = LiteratureItem(
        title="Social attribution in moving shapes",
        abstract="Animated triangles measured social attribution in autistic children.",
        recommendation_score=55,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="C1",
    )

    assert adhd not in select_weekly_top([adhd, good])


def test_response_commentary_does_not_enter_weekly_top3():
    response = LiteratureItem(
        title="Response to comments on mentalizing in autistic children",
        abstract="A response commentary without a new task or dataset.",
        recommendation_score=90,
        recommendation_tier="background",
        reading_priority="exclude",
        strong_exclusion=True,
        penalty_reasons=["response_commentary"],
        module="C2",
    )
    good = LiteratureItem(
        title="False belief CAToon task",
        abstract="Belief-consistent looking measured false belief reasoning.",
        recommendation_score=50,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="C2",
    )

    assert response not in select_weekly_top([response, good])


def test_joint_attention_eye_tracking_can_enter_as_skim():
    item = LiteratureItem(
        title="Joint attention eye-tracking battery",
        abstract="",
        recommendation_score=60,
        recommendation_tier="core",
        reading_priority="skim",
        module="A",
    )

    assert item in select_weekly_top([item])


def test_c1_c2_high_relevance_preferred_for_weekly_top3():
    c1 = LiteratureItem(
        title="Social attribution in animated triangles",
        abstract="Moving shapes measured social attribution.",
        recommendation_score=60,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="C1",
    )
    c2 = LiteratureItem(
        title="False belief CAToon",
        abstract="Belief-consistent looking measured knowledge difference.",
        recommendation_score=59,
        recommendation_tier="core",
        reading_priority="deep_read",
        module="C2",
    )
    background = LiteratureItem(
        title="Language strategy for parents",
        abstract="Language intervention strategy.",
        recommendation_score=99,
        recommendation_tier="background",
        reading_priority="defer",
        module="方法学",
        penalty_reasons=["language_intervention_only"],
    )

    top = select_weekly_top([background, c1, c2], limit=2)

    assert top == [c1, c2]
