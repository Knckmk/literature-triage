from __future__ import annotations

from ingest import docs_to_text, load_corpus
from models import Document, PaperMetadata


def test_local_ingestion_populates_document_metadata(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "paper one.md").write_text(
        "# Markdown Paper\n\n"
        "This abstract has enough words for ingestion to keep the document.",
        encoding="utf-8",
    )
    (corpus / "paper_two.txt").write_text(
        "Plain Text Paper\n\n"
        "This second abstract also has enough words for ingestion to keep it.",
        encoding="utf-8",
    )

    docs = load_corpus(str(corpus))

    assert len(docs) == 2
    assert all(isinstance(doc, Document) for doc in docs)
    assert all(isinstance(doc.metadata, PaperMetadata) for doc in docs)

    by_title = {doc.title: doc for doc in docs}
    md_doc = by_title["Markdown Paper"]
    txt_doc = by_title["Plain Text Paper"]

    assert md_doc.doc_id == "paper_one"
    assert md_doc.metadata.paper_id == md_doc.doc_id
    assert md_doc.metadata.source == "local"
    assert md_doc.metadata.title == md_doc.title
    assert md_doc.metadata.abstract == md_doc.body
    assert md_doc.metadata.authors == []
    assert md_doc.metadata.year is None
    assert md_doc.metadata.url is None
    assert md_doc.metadata.pdf_url is None
    assert md_doc.metadata.citation_count is None

    assert txt_doc.doc_id == "paper_two"
    assert txt_doc.rel_path == "paper_two.txt"
    assert txt_doc.word_count > 5
    assert docs_to_text([md_doc]) == [f"{md_doc.title}\n\n{md_doc.body}"]
