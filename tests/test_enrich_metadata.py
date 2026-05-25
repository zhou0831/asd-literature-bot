from src.enrich import enrich_metadata
from src.models import LiteratureItem


def test_enrich_metadata_fills_missing_abstract_from_pubmed(monkeypatch):
    def fake_fetch(pmids):
        return [
            LiteratureItem(
                title="Joint attention",
                pmid=pmids[0],
                abstract="This PubMed abstract describes joint attention and gaze cueing in autistic children using eye tracking.",
                abstract_status="full",
                abstract_source="PubMed",
                metadata_sources=["PubMed"],
            )
        ]

    monkeypatch.setattr("src.enrich.fetch_pubmed_details", fake_fetch)
    item = LiteratureItem(title="Joint attention", pmid="123", abstract="")

    enriched = enrich_metadata([item])

    assert enriched[0].abstract_status == "full"
    assert enriched[0].abstract_source == "PubMed"
    assert "joint attention" in enriched[0].abstract
