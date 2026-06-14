import os
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv
from main import generate_questions, evaluate_answers

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    notes = request.form.get("notes", "").strip()
    count_raw = request.form.get("count", "5").strip()

    if not notes:
        return render_template("index.html", error="Please paste your notes before generating.")

    try:
        count = int(count_raw)
        if not 1 <= count <= 20:
            raise ValueError
    except ValueError:
        return render_template("index.html", error="Question count must be a number between 1 and 20.", notes=notes)

    try:
        questions = generate_questions(notes, count)
    except Exception as e:
        return render_template("index.html", error=f"Generation failed: {e}", notes=notes, count=count_raw)

    session["questions"] = questions
    return render_template("quiz.html", questions=questions)


@app.route("/submit", methods=["POST"])
def submit():
    questions = session.get("questions")
    if not questions:
        return redirect(url_for("index"))

    user_answers = [
        request.form.get(f"answer_{i}", "").strip()
        for i in range(len(questions))
    ]

    try:
        feedback = evaluate_answers(questions, user_answers)
    except Exception as e:
        return render_template("quiz.html", questions=questions, error=f"Evaluation failed: {e}")

    session.pop("questions", None)
    return render_template("results.html", questions=questions, user_answers=user_answers, feedback=feedback)


if __name__ == "__main__":
    app.run(debug=True)
