from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re
from typing import Dict, List, Optional


INTRO_MESSAGE = (
    "Hi! Thank you for your interest in our Basic Certificate in Dental Assisting course.\n"
    "Upcoming intake dates:\n"
    "- 15th to 16th July 2026 (Weekdays)\n"
    "- 25th & 26th July 2026 (Weekends)\n"
    "- 12th to 13th August 2026\n"
    "Course fee is $600 nett for 2 consecutive days (9:30am to 5:30pm) at our HQ, Clementi Loop.\n"
    "You may use SkillsFuture Credit (basic tier) for payment.\n"
    "If you would like to enroll, reply in natural language and I will guide you."
)

FIRST_FOLLOWUP = (
    "Just checking in—would you like help with course dates, SkillsFuture eligibility, or enrollment?"
)
SECOND_FOLLOWUP = (
    "Friendly reminder: I can help you enroll and prepare your invoice when you are ready."
)
THIRD_FOLLOWUP = (
    "Final follow-up for now. If you still want to join the Dental Assisting course, just reply here anytime."
)

DETAILS_PROMPT = (
    "Great, I can help with enrollment. Please share:\n"
    "1) Full name (as per NRIC)\n"
    "2) NRIC number\n"
    "3) Date of birth\n"
    "4) Email address\n"
    "5) Mobile number\n"
    "6) Preferred course date\n"
    "7) Payment mode (SkillsFuture basic tier / PayNow / UTAP)\n"
    "8) SkillsFuture claim amount if applicable"
)

PAYMENT_INSTRUCTION = (
    "Thank you. I will generate your invoice and email it with SkillsFuture and PayNow instructions.\n"
    "After payment/claim submission, please send:\n"
    "- Invoice screenshot\n"
    "- PayNow screenshot\n"
    "- SFC screenshot"
)

CONFIRMATION_MESSAGE = (
    "Payment has been verified and your enrollment is confirmed.\n"
    "I have recorded your enrollment and will add you to the course schedule."
)

FAQ_RESPONSES = {
    "midcareer": (
        "Our course is only eligible for SkillsFuture basic tier. Mid-Career SkillsFuture Credit cannot be used."
    ),
    "qualification": (
        "Preferred qualification is GCE 'N' Levels. If not available, basic English reading/writing is accepted."
    ),
    "job": (
        "Suitable candidates may be offered opportunities after the course, subject to HR selection criteria."
    ),
    "expensive": (
        "The fee includes expert instruction, materials, and facilities designed to support practical skill development."
    ),
    "utap": (
        "NTUC Union members can claim UTAP support after course completion, subject to union rules and timelines."
    ),
}


class Intent(str, Enum):
    ENQUIRY = "enquiry"
    ENROLLMENT = "enrollment"
    PAYMENT = "payment_submission"
    UNKNOWN = "unknown"


class EnrollmentStatus(str, Enum):
    ENQUIRY = "enquiry"
    AWAITING_DETAILS = "awaiting_details"
    INVOICE_SENT = "invoice_sent"
    AWAITING_PAYMENT_PROOF = "awaiting_payment_proof"
    PAYMENT_UNDER_REVIEW = "payment_under_review"
    PAYMENT_CONFIRMED = "payment_confirmed"
    COMPLETED = "completed"


@dataclass
class CandidateRecord:
    phone: str
    status: EnrollmentStatus = EnrollmentStatus.ENQUIRY
    details: Dict[str, str] = field(default_factory=dict)
    first_contact_at: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    followups_sent: int = 0
    confirmation_sent: bool = False
    added_to_timetree: bool = False


def classify_intent(message: str, has_image_attachment: bool = False) -> Intent:
    text = message.lower()
    if has_image_attachment or any(k in text for k in ["screenshot", "receipt", "paynow", "paid"]):
        return Intent.PAYMENT
    if any(k in text for k in ["enroll", "register", "sign up", "join course", "i want to join"]):
        return Intent.ENROLLMENT
    if any(k in text for k in ["skillsfuture", "course", "qualification", "fee", "utap", "job"]):
        return Intent.ENQUIRY
    return Intent.UNKNOWN


def _extract_details(message: str) -> Dict[str, str]:
    fields = {
        "name": r"(?:name)\s*[:\-]\s*(.+)",
        "nric": r"(?:nric)\s*[:\-]\s*([a-z0-9]+)",
        "dob": r"(?:date of birth|dob)\s*[:\-]\s*([0-9/\-]+)",
        "email": r"(?:email)\s*[:\-]\s*([^\s]+@[^\s]+)",
        "mobile": r"(?:mobile|phone|hp)\s*[:\-]\s*([\+\d\s\-]{8,})",
        "course_date": r"(?:course date|preferred date)\s*[:\-]\s*(.+)",
        "payment_mode": r"(?:payment mode)\s*[:\-]\s*(.+)",
        "skillsfuture_amount": r"(?:skillsfuture amount|sfc amount)\s*[:\-]\s*([0-9]+(?:\.[0-9]{1,2})?)",
    }
    text = message.lower()
    extracted: Dict[str, str] = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            extracted[key] = match.group(1).strip()
    return extracted


def _faq_response(message: str) -> Optional[str]:
    text = message.lower()
    if "midcareer" in text:
        return FAQ_RESPONSES["midcareer"]
    if "qualification" in text or "minimum" in text:
        return FAQ_RESPONSES["qualification"]
    if "job" in text or "position" in text:
        return FAQ_RESPONSES["job"]
    if "expensive" in text or "cost" in text:
        return FAQ_RESPONSES["expensive"]
    if "utap" in text or "union" in text:
        return FAQ_RESPONSES["utap"]
    return None


class DentalCourseWorkflow:
    def __init__(self) -> None:
        self.records: Dict[str, CandidateRecord] = {}

    def process_message(
        self,
        phone: str,
        message: str,
        now: Optional[datetime] = None,
        has_image_attachment: bool = False,
    ) -> str:
        now = now or datetime.utcnow()
        record = self.records.setdefault(phone, CandidateRecord(phone=phone))
        if record.first_contact_at is None:
            record.first_contact_at = now
        record.last_contact_at = now

        details = _extract_details(message)
        if details:
            record.details.update(details)
            required = {"name", "nric", "dob", "email", "mobile", "course_date", "payment_mode"}
            if required.issubset(record.details):
                record.status = EnrollmentStatus.INVOICE_SENT
                return PAYMENT_INSTRUCTION
            record.status = EnrollmentStatus.AWAITING_DETAILS
            return DETAILS_PROMPT

        intent = classify_intent(message, has_image_attachment)
        if record.status == EnrollmentStatus.ENQUIRY and intent in {Intent.ENQUIRY, Intent.UNKNOWN}:
            faq = _faq_response(message)
            return faq or INTRO_MESSAGE
        if intent == Intent.ENROLLMENT:
            record.status = EnrollmentStatus.AWAITING_DETAILS
            return DETAILS_PROMPT
        if intent == Intent.PAYMENT:
            record.status = EnrollmentStatus.PAYMENT_UNDER_REVIEW
            return "Received your payment screenshots. I will verify amount against your invoice now."

        faq = _faq_response(message)
        return faq or "Thanks for your message. I can help with enquiries, enrollment, or payment verification."

    def confirm_payment(self, phone: str, amount_match: bool) -> str:
        record = self.records[phone]
        if amount_match:
            record.status = EnrollmentStatus.PAYMENT_CONFIRMED
            return CONFIRMATION_MESSAGE
        return "I found a payment mismatch. Please resend a clearer screenshot or confirm the paid amount."

    def save_screenshots(self, phone: str) -> str:
        if phone not in self.records:
            return "No candidate record found."
        self.records[phone].status = EnrollmentStatus.PAYMENT_CONFIRMED
        return "Screenshots have been saved to the participant folder in OneDrive."

    def send_confirmation(self, phone: str) -> str:
        if phone not in self.records:
            return "No candidate record found."
        record = self.records[phone]
        record.confirmation_sent = True
        record.status = EnrollmentStatus.COMPLETED
        return CONFIRMATION_MESSAGE

    def add_to_timetree(self, phone: str) -> str:
        if phone not in self.records:
            return "No candidate record found."
        self.records[phone].added_to_timetree = True
        return "Participant has been added to TimeTree for the selected course date."

    def due_followups(self, now: Optional[datetime] = None) -> List[Dict[str, str]]:
        now = now or datetime.utcnow()
        results: List[Dict[str, str]] = []
        schedule = [
            (timedelta(minutes=30), FIRST_FOLLOWUP),
            (timedelta(days=1), SECOND_FOLLOWUP),
            (timedelta(days=2), THIRD_FOLLOWUP),
        ]
        for phone, record in self.records.items():
            if record.first_contact_at is None or record.followups_sent >= len(schedule):
                continue
            next_due, message = schedule[record.followups_sent]
            if now - record.last_contact_at >= next_due:
                results.append({"phone": phone, "message": message})
                record.followups_sent += 1
                record.last_contact_at = now
        return results
