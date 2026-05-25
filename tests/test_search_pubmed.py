import xml.etree.ElementTree as ET

from src.search import search_pubmed


def test_pubmed_efetch_parses_abstract(monkeypatch):
    monkeypatch.setattr(
        "src.search._get_json",
        lambda url, params: {"esearchresult": {"idlist": ["12345"]}},
    )
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345</PMID>
          <Article>
            <Journal>
              <JournalIssue><PubDate><Year>2026</Year></PubDate></JournalIssue>
              <Title>Behavior Research Methods</Title>
            </Journal>
            <ArticleTitle>Joint attention in autistic children</ArticleTitle>
            <Abstract>
              <AbstractText Label="BACKGROUND">Joint attention is central to social cognition.</AbstractText>
              <AbstractText Label="METHODS">Children completed an interactive eye-tracking task.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author><ForeName>Chris</ForeName><LastName>Yoon</LastName></Author>
            </AuthorList>
          </Article>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1000/test</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    monkeypatch.setattr("src.search._get_xml", lambda url, params: ET.fromstring(xml))

    items = search_pubmed("autism joint attention", limit=1, days_back=180)

    assert len(items) == 1
    assert items[0].pmid == "12345"
    assert items[0].doi == "10.1000/test"
    assert items[0].year == "2026"
    assert items[0].venue == "Behavior Research Methods"
    assert items[0].authors == ["Chris Yoon"]
    assert "Joint attention is central" in items[0].abstract
    assert "interactive eye-tracking task" in items[0].abstract
