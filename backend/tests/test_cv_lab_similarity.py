from app.services.cv_lab_similarity import compare_cv_to_lab


def test_tfidf_similarity_returns_deterministic_matches() -> None:
    first = compare_cv_to_lab(
        "Python Computer Vision PyTorch", "Computer Vision lab develops PyTorch models"
    )
    second = compare_cv_to_lab(
        "Python Computer Vision PyTorch", "Computer Vision lab develops PyTorch models"
    )

    assert first == second
    assert first.similarity_score > 0
    assert first.matched_keywords == ["computer", "pytorch", "vision"]


def test_tfidf_similarity_handles_empty_input() -> None:
    result = compare_cv_to_lab("", "Computer Vision")
    assert result.similarity_score == 0
    assert result.matched_keywords == []
