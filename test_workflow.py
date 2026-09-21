from datetime import datetime, timedelta
import unittest

from workflow import DentalCourseWorkflow, EnrollmentStatus


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = DentalCourseWorkflow()
        self.phone = "+6591234567"
        self.now = datetime(2026, 7, 1, 9, 0, 0)

    def test_intro_message_for_new_enquiry(self) -> None:
        message = self.workflow.process_message(self.phone, "Can you share course info?", now=self.now)
        self.assertIn("Basic Certificate in Dental Assisting", message)

    def test_enrollment_prompts_for_details(self) -> None:
        message = self.workflow.process_message(self.phone, "I want to enroll", now=self.now)
        self.assertIn("Please share", message)
        self.assertEqual(self.workflow.records[self.phone].status, EnrollmentStatus.AWAITING_DETAILS)

    def test_detail_collection_moves_to_invoice_sent(self) -> None:
        self.workflow.process_message(self.phone, "I want to enroll", now=self.now)
        response = self.workflow.process_message(
            self.phone,
            (
                "Name: Tan Ah Kow\n"
                "NRIC: S1234567A\n"
                "DOB: 1990-01-01\n"
                "Email: test@example.com\n"
                "Mobile: 91234567\n"
                "Preferred Date: 12th to 13th August 2026\n"
                "Payment Mode: SkillsFuture basic tier\n"
                "SkillsFuture Amount: 500"
            ),
            now=self.now + timedelta(minutes=2),
        )
        self.assertIn("generate your invoice", response.lower())
        self.assertEqual(self.workflow.records[self.phone].status, EnrollmentStatus.INVOICE_SENT)

    def test_payment_submission_goes_under_review(self) -> None:
        response = self.workflow.process_message(
            self.phone,
            "Attached payment screenshot",
            now=self.now,
            has_image_attachment=True,
        )
        self.assertIn("verify", response.lower())
        self.assertEqual(self.workflow.records[self.phone].status, EnrollmentStatus.PAYMENT_UNDER_REVIEW)

    def test_followups_in_sequence(self) -> None:
        self.workflow.process_message(self.phone, "Hi", now=self.now)
        due1 = self.workflow.due_followups(now=self.now + timedelta(minutes=31))
        due2 = self.workflow.due_followups(now=self.now + timedelta(days=1, minutes=31))
        due3 = self.workflow.due_followups(now=self.now + timedelta(days=3))
        self.assertEqual(len(due1), 1)
        self.assertEqual(len(due2), 1)
        self.assertEqual(len(due3), 1)

    def test_midcareer_answer(self) -> None:
        response = self.workflow.process_message(self.phone, "Can I use midcareer skillsfuture?", now=self.now)
        self.assertIn("cannot be used", response.lower())


if __name__ == "__main__":
    unittest.main()
