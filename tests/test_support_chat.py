import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.support_chat import AppointmentNotice


def test_rescheduled_notice_is_patient_safe_and_operational():
    notice = AppointmentNotice("A-1042", "rescheduled", "Tuesday at 10:30")

    assert notice.patient_message() == "Appointment A-1042 has been rescheduled to Tuesday at 10:30."
    assert "diagnosis" not in notice.patient_message().lower()
