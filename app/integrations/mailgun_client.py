from __future__ import annotations

from pathlib import Path

import httpx


class MailgunClient:
    def __init__(self, *, api_key: str, domain: str, from_email: str, timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key
        self.domain = domain
        self.from_email = from_email
        self.timeout_seconds = timeout_seconds

    def send_message(
        self,
        *,
        to_email: str,
        subject: str,
        text: str,
        attachment_paths: list[Path] | None = None,
    ) -> dict:
        url = f"https://api.mailgun.net/v3/{self.domain}/messages"

        data = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "text": text,
        }

        print(f"\nSending email via Mailgun API to {to_email} with subject '{subject}' and {len(attachment_paths or [])} attachments\n")
        print(data)

        files = []
        try:
            for path in attachment_paths or []:
                files.append(
                    ("attachment", (path.name, open(path, "rb"), "application/zip"))
                )

            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(
                    url,
                    auth=("api", self.api_key),
                    data=data,
                    files=files,
                )

                resp.raise_for_status()
                return resp.json()
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()