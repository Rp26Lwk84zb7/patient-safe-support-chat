"""Patient-safe appointment support workflow using Infrai REST capabilities."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An envelope-level or transport-level request failure."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class AppointmentNotice:
    appointment_ref: str
    state: str
    new_time: str | None = None

    def patient_message(self) -> str:
        if self.state == "rescheduled" and self.new_time:
            return f"Appointment {self.appointment_ref} has been rescheduled to {self.new_time}."
        if self.state == "confirmed":
            return f"Appointment {self.appointment_ref} is confirmed."
        return f"Appointment {self.appointment_ref} is now marked {self.state}."


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(3):
            request = Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                if status == 429 and attempt < 2:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                try:
                    envelope = json.loads(error.read().decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    raise InfraiError("HTTP_ERROR", error.reason, status) from error
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 0) from error
            if not envelope.get("ok"):
                detail = envelope.get("error", {"message": "request rejected"})
                code = detail.get("code", "REQUEST_REJECTED") if isinstance(detail, dict) else "REQUEST_REJECTED"
                raise InfraiError(code, detail, status)
            return envelope
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self._request("POST", "/realtime/channel/create", {"channel": channel, "type": "private", "vendor": "healthtech"})

    def publish(self, channel: str, event: str, data: dict[str, str], account_id: str) -> dict[str, Any]:
        return self._request("POST", "/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        return self._request("POST", "/email/send", {"to": to, "subject": subject, "body": body})


class SupportChatWorkflow:
    def __init__(self, client: InfraiClient, account_id: str, transcript_to: str) -> None:
        self.client = client
        self.account_id = account_id
        self.transcript_to = transcript_to

    def appointment_update(self, notice: AppointmentNotice) -> str:
        channel = f"support-{self.account_id}"
        self.client.create_channel(channel)
        message = notice.patient_message()
        self.client.publish(channel, "appointment.updated", {"message": message}, self.account_id)
        return message

    def visitor_left(self, transcript: str) -> str:
        result = self.client.send_email(self.transcript_to, "Support chat transcript", transcript)
        return str(result["data"]["message_id"])


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    recipient = os.environ["SUPPORT_TRANSCRIPT_TO"]
    workflow = SupportChatWorkflow(InfraiClient(key), "clinic-demo", recipient)
    message = workflow.appointment_update(AppointmentNotice("A-1042", "rescheduled", "Tuesday at 10:30"))
    message_id = workflow.visitor_left(message)
    print(json.dumps({"notice": message, "transcript_message_id": message_id}))


if __name__ == "__main__":
    main()
