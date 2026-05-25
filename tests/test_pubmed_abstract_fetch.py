import xml.etree.ElementTree as ET

from src.search import fetch_pubmed_details


def test_pubmed_abstract_fetch_parses_labeled_abstract(monkeypatch):
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>98765</PMID>
          <Article>
            <Journal>
              <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
              <Title>Journal of Autism Research</Title>
            </Journal>
            <ArticleTitle>False belief in autistic children</ArticleTitle>
            <Abstract>
              <AbstractText Label="OBJECTIVE">We tested belief reasoning.</AbstractText>
              <AbstractText Label="RESULTS">Children showed belief-consistent looking.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author><ForeName>Ada</ForeName><LastName>Chen</LastName></Author>
            </AuthorList>
          </Article>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1000/belief</ArticleId>
            <ArticleId IdType="pmc">PMC123</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    monkeypatch.setattr("src.search._get_xml", lambda url, params: ET.fromstring(xml))

    items = fetch_pubmed_details(["98765"])

    assert len(items) == 1
    assert items[0].abstract_status == "full"
    assert items[0].abstract_source == "PubMed"
    assert items[0].pmcid == "PMC123"
    assert "OBJECTIVE: We tested belief reasoning." in items[0].abstract
    assert "RESULTS: Children showed belief-consistent looking." in items[0].abstract
