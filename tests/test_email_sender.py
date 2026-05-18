from src.email_sender import build_message


def test_build_message_dry_run_shape():
    msg = build_message("subject", "body", "to@example.com", "from@example.com")
    assert msg["Subject"] == "subject"
    assert msg["To"] == "to@example.com"
    assert msg.get_content().strip() == "body"

