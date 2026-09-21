from datetime import datetime

from workflow import DentalCourseWorkflow


def main() -> None:
    workflow = DentalCourseWorkflow()
    phone = input("Candidate phone number: ").strip()
    print("Type natural-language messages. Type 'exit' to stop.")
    while True:
        message = input("Candidate: ").strip()
        if message.lower() == "exit":
            break
        reply = workflow.process_message(phone=phone, message=message, now=datetime.utcnow())
        print(f"Agent: {reply}")


if __name__ == "__main__":
    main()
