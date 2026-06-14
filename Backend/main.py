import os
import json
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def generate_questions(notes: str, count: int) -> list[dict]:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Based on the following notes, generate exactly {count} unique quiz questions. "
                    "Return ONLY a JSON array, no extra text. Each item must have:\n"
                    '  "question": the quiz question\n'
                    '  "answer": a concise model answer\n'
                    '  "topic": the key concept being tested (2-4 words)\n\n'
                    f"Notes:\n{notes}"
                )
            }
        ]
    )
    text = message.content[0].text
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to parse questions from model response: {e}\n\nRaw response:\n{text}")

def evaluate_answers(questions: list[dict], user_answers: list[str]) -> str:
    qa_pairs = "\n\n".join(
        f"Question {i+1} (topic: {q['topic']}): {q['question']}\n"
        f"Model answer: {q['answer']}\n"
        f"Student answer: {user_answers[i]}"
        for i, q in enumerate(questions)
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Evaluate the student's answers. For each one, briefly note if they got it "
                    "right, partially right, or wrong. Then give a short summary:\n"
                    "- What they know well\n"
                    "- What they struggled with\n"
                    "- Where to focus study time before the test\n\n"
                    + qa_pairs
                )
            }
        ]
    )
    return message.content[0].text

def main():
    print("Study Quiz Generator")
    print("=" * 40)
    print('Paste your notes below. Type "END" on its own line when done:\n')

    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)

    notes = "\n".join(lines).strip()

    if not notes:
        print("No notes provided. Exiting.")
        return

    while True:
        raw = input("\nHow many questions do you want? ")
        if raw.strip().isdigit() and int(raw.strip()) > 0:
            count = int(raw.strip())
            break
        print("Please enter a positive whole number.")

    print("\nGenerating questions...")
    questions = generate_questions(notes, count)

    print("\n" + "=" * 40)
    print("Answer each question. Press Enter when done.\n")

    user_answers = []
    for i, q in enumerate(questions):
        print(f"Q{i+1}: {q['question']}")
        answer = input("Your answer: ").strip()
        user_answers.append(answer)
        print()

    print("Evaluating your answers...")
    feedback = evaluate_answers(questions, user_answers)
    print("\n" + "=" * 40)
    print(feedback)

if __name__ == "__main__":
    main()
