import json
import re

import fitz
import requests
import streamlit as st


# =====================================================
# PAGE SETTINGS
# =====================================================

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("📚 AI Study Assistant")
st.write(
    "Upload study notes, generate summaries, create questions, "
    "take quizzes, and chat with your PDF."
)
st.warning(
    "⚠️ Do not upload private documents, exam papers, personal IDs, "
    "medical records, passwords, or confidential college files. "
    "Always verify AI answers using your original notes."
)

# =====================================================
# CONFIGURATION
# =====================================================

# Ollama Cloud API endpoint
OLLAMA_URL = "https://ollama.com/api/chat"

# Official cloud-model example from Ollama documentation
MODEL_NAME = "gemma4:31b"

# Lower number means quicker responses
MAX_TEXT_LENGTH = 3500
CHAT_TEXT_LENGTH = 2500


# =====================================================
# API KEY FROM .streamlit/secrets.toml
# =====================================================

try:
    OLLAMA_API_KEY = st.secrets["OLLAMA_API_KEY"]

except Exception:
    st.error("❌ API key not found.")

    st.markdown(
        """
Create this file inside your project folder:

```text
.streamlit/secrets.toml
```

Paste this inside it:

```toml
OLLAMA_API_KEY = "your-real-ollama-api-key"
```

Save the file, stop Streamlit, and run the app again.
        """
    )

    st.stop()


# =====================================================
# AI FUNCTION
# =====================================================

def ask_ai(prompt, max_tokens=300, json_mode=False):
    system_message = """
You are an accurate and helpful college study assistant.
When a student asks about their PDF, use only the PDF text
provided in the prompt. If information is not in the PDF,
say that clearly. Do not invent facts.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": max_tokens
        }
    }

    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(
            OLLAMA_URL,
            headers={
                "Authorization": f"Bearer {OLLAMA_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=180
        )

    except requests.RequestException as error:
        raise RuntimeError(
            f"Could not connect to Ollama Cloud: {error}"
        )

    if not response.ok:
        raise RuntimeError(
            f"Ollama API error {response.status_code}:\n"
            f"{response.text}"
        )

    data = response.json()

    try:
        return data["message"]["content"]

    except KeyError:
        raise RuntimeError(
            f"Unexpected answer from Ollama:\n{data}"
        )


# =====================================================
# PDF EXTRACTION WITH CACHE
# =====================================================

@st.cache_data(show_spinner=False)
def extract_pdf_text(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        pages = []

        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text", sort=True)

            if page_text.strip():
                pages.append(f"Page {page_number}\n{page_text}")

    return "\n\n".join(pages), len(pages)


# =====================================================
# QUIZ JSON HELPER
# =====================================================

def parse_quiz_json(text):
    cleaned_text = re.sub(
        r"```(?:json)?|```",
        "",
        text
    ).strip()

    start = cleaned_text.find("{")
    end = cleaned_text.rfind("}")

    if start != -1 and end != -1:
        cleaned_text = cleaned_text[start:end + 1]

    return json.loads(cleaned_text)


# =====================================================
# SESSION STATE
# =====================================================

defaults = {
    "pdf_name": "",
    "summary": "",
    "questions": "",
    "explanation": "",
    "explained_topic": "",
    "chat_history": [],
    "quiz_questions": [],
    "quiz_answers": {},
    "quiz_submitted": False
}

for key, default_value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# =====================================================
# PDF UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "📄 Upload your study PDF",
    type=["pdf"]
)

if uploaded_file is None:
    st.info("👆 Upload a text-based PDF to begin studying.")

    st.markdown(
        """
### What you can do

- ✨ Generate a short summary
- 📝 Generate practice questions
- 💡 Explain a difficult topic
- 💬 Ask questions about the PDF
- 🎯 Take an MCQ quiz

**Important:** Check AI answers with your original notes.
        """
    )

    st.stop()


# =====================================================
# EXTRACT PDF
# =====================================================

try:
    pdf_bytes = uploaded_file.getvalue()
    extracted_text, page_count = extract_pdf_text(pdf_bytes)

except Exception as error:
    st.error("❌ This PDF could not be read.")
    st.code(str(error))
    st.stop()


# Reset old result data for a new uploaded PDF
if st.session_state["pdf_name"] != uploaded_file.name:
    st.session_state["pdf_name"] = uploaded_file.name
    st.session_state["summary"] = ""
    st.session_state["questions"] = ""
    st.session_state["explanation"] = ""
    st.session_state["explained_topic"] = ""
    st.session_state["chat_history"] = []
    st.session_state["quiz_questions"] = []
    st.session_state["quiz_answers"] = {}
    st.session_state["quiz_submitted"] = False


if not extracted_text.strip():
    st.warning(
        "No readable text was found. This may be a scanned "
        "image PDF and require OCR."
    )
    st.stop()


# Use only part of PDF to make responses faster
study_text = extracted_text[:MAX_TEXT_LENGTH]
chat_text = extracted_text[:CHAT_TEXT_LENGTH]

st.success(f"✅ PDF uploaded successfully: {page_count} page(s).")

st.caption(
    "Fast mode is active. The app uses the first part of the "
    "PDF text, so later pages may not be included yet."
)


# =====================================================
# VIEW TEXT
# =====================================================

with st.expander("📖 View Extracted PDF Text"):
    st.text_area(
        "Extracted text",
        value=extracted_text,
        height=250
    )

st.download_button(
    "⬇️ Download Extracted Text",
    data=extracted_text,
    file_name="extracted_notes.txt",
    mime="text/plain"
)

st.divider()


# =====================================================
# SUMMARY
# =====================================================

st.header("✨ 1. Generate Summary")

if st.button("Generate Fast Summary", use_container_width=True):
    prompt = f"""
Create a short summary from this study material.

Rules:
- Give a meaningful title.
- Use bullet points.
- Use easy language.
- Include important definitions, formulas, and exam points.
- Do not invent facts.
- Keep the answer under 250 words.

Study material:
{study_text}
"""

    with st.spinner("Generating summary..."):
        try:
            st.session_state["summary"] = ask_ai(
                prompt,
                max_tokens=350
            )

        except Exception as error:
            st.error("❌ Summary generation failed.")
            st.code(str(error))

if st.session_state["summary"]:
    st.subheader("📝 Your Summary")
    st.markdown(st.session_state["summary"])

    st.download_button(
        "⬇️ Download Summary",
        data=st.session_state["summary"],
        file_name="study_summary.txt",
        mime="text/plain"
    )

st.divider()


# =====================================================
# PRACTICE QUESTIONS
# =====================================================

st.header("📝 2. Generate Practice Questions")

question_type = st.selectbox(
    "Choose question type",
    [
        "Short-answer questions",
        "Multiple-choice questions",
        "Mixed questions"
    ]
)

if st.button("Generate 5 Questions", use_container_width=True):
    prompt = f"""
Create exactly 5 {question_type} from the study material.

Rules:
- Use simple language.
- Do not repeat questions.
- Use only information from the study material.
- For MCQs, give four options and state the correct answer.
- For short answers, give a concise model answer.
- Keep the full answer under 350 words.

Study material:
{study_text}
"""

    with st.spinner("Generating questions..."):
        try:
            st.session_state["questions"] = ask_ai(
                prompt,
                max_tokens=450
            )

        except Exception as error:
            st.error("❌ Practice question generation failed.")
            st.code(str(error))

if st.session_state["questions"]:
    st.subheader("📚 Practice Questions")
    st.markdown(st.session_state["questions"])

    st.download_button(
        "⬇️ Download Questions",
        data=st.session_state["questions"],
        file_name="practice_questions.txt",
        mime="text/plain"
    )

st.divider()


# =====================================================
# EXPLAIN TOPIC
# =====================================================

st.header("💡 3. Explain a Difficult Topic")

topic = st.text_input(
    "Enter a topic from your PDF",
    placeholder="Example: Queue in Data Structures"
)

if st.button("Explain Topic", use_container_width=True):
    if not topic.strip():
        st.warning("Please type a topic first.")

    else:
        prompt = f"""
Explain this topic to a beginner: {topic}

Rules:
- Start with a simple definition.
- Explain step by step.
- Give one simple example if appropriate.
- Use the PDF as the main source.
- If it is not covered in the PDF, say so.
- Keep the answer under 220 words.

Study material:
{study_text}
"""

        with st.spinner("Preparing explanation..."):
            try:
                st.session_state["explanation"] = ask_ai(
                    prompt,
                    max_tokens=320
                )

                st.session_state["explained_topic"] = topic

            except Exception as error:
                st.error("❌ Topic explanation failed.")
                st.code(str(error))

if st.session_state["explanation"]:
    st.subheader(
        f"📖 Explanation: {st.session_state['explained_topic']}"
    )

    st.markdown(st.session_state["explanation"])

    st.download_button(
        "⬇️ Download Explanation",
        data=st.session_state["explanation"],
        file_name="topic_explanation.txt",
        mime="text/plain"
    )

st.divider()


# =====================================================
# CHAT WITH PDF
# =====================================================

st.header("💬 4. Chat with Your PDF")
st.caption("Fast mode uses a short PDF section and concise answers.")

for message in st.session_state["chat_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("Ask something about your PDF...")

if user_question:
    st.session_state["chat_history"].append({
        "role": "user",
        "content": user_question
    })

    with st.chat_message("user"):
        st.markdown(user_question)

    recent_history = st.session_state["chat_history"][-5:-1]

    conversation_context = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in recent_history
    )

    prompt = f"""
Answer the student's question using the PDF material.

Rules:
- Answer simply and directly.
- If the PDF does not contain the answer, say so.
- Do not invent facts.
- Keep the answer under 150 words.

Recent conversation:
{conversation_context}

Student question:
{user_question}

PDF material:
{chat_text}
"""

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer = ask_ai(
                    prompt,
                    max_tokens=220
                )

                st.markdown(answer)

                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:
                st.error("❌ Chat request failed.")
                st.code(str(error))

if st.button("Clear Chat History"):
    st.session_state["chat_history"] = []
    st.rerun()

st.divider()


# =====================================================
# QUIZ
# =====================================================

st.header("🎯 5. Quiz Mode")

if st.button("Generate 5-Question Quiz", use_container_width=True):
    quiz_prompt = f"""
Create exactly 5 multiple-choice questions from the study material.

Return ONLY valid JSON. Do not include Markdown code fences.
Do not add an introduction or extra explanation outside JSON.

Use this exact JSON structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": "Option A",
      "explanation": "Short explanation"
    }}
  ]
}}

Rules:
- Return exactly 5 questions.
- Give exactly 4 options for each question.
- The answer must exactly match one of the options.
- Use facts only from the study material.
- Make explanations short.

Study material:
{study_text}
"""

    with st.spinner("Creating quiz..."):
        try:
            quiz_response = ask_ai(
                quiz_prompt,
                max_tokens=650,
                json_mode=True
            )

            quiz_data = parse_quiz_json(quiz_response)
            generated_questions = quiz_data.get("questions", [])

            valid_questions = []

            for question in generated_questions:
                options = question.get("options", [])
                answer = question.get("answer", "")

                if (
                    question.get("question")
                    and len(options) == 4
                    and answer in options
                ):
                    valid_questions.append(question)

            if len(valid_questions) < 5:
                st.error(
                    "The AI did not create five valid questions. "
                    "Please click the button again."
                )

            else:
                st.session_state["quiz_questions"] = valid_questions[:5]
                st.session_state["quiz_answers"] = {}
                st.session_state["quiz_submitted"] = False
                st.rerun()

        except Exception as error:
            st.error("❌ Quiz creation failed.")
            st.code(str(error))


# =====================================================
# QUIZ DISPLAY AND RESULT
# =====================================================

if st.session_state["quiz_questions"]:
    st.subheader("Your Quiz")

    with st.form("quiz_form"):
        selected_answers = {}

        for index, question in enumerate(
            st.session_state["quiz_questions"]
        ):
            st.markdown(
                f"**Q{index + 1}. {question['question']}**"
            )

            selected_answers[index] = st.radio(
                "Select one answer",
                question["options"],
                index=None,
                key=f"quiz_answer_{index}"
            )

        submitted = st.form_submit_button("Submit Quiz")

    if submitted:
        st.session_state["quiz_answers"] = selected_answers
        st.session_state["quiz_submitted"] = True

    if st.session_state["quiz_submitted"]:
        score = 0
        total = len(st.session_state["quiz_questions"])

        st.subheader("📊 Quiz Result")

        for index, question in enumerate(
            st.session_state["quiz_questions"]
        ):
            selected = st.session_state["quiz_answers"].get(index)
            correct = question["answer"]

            if selected == correct:
                score += 1
                st.success(f"Question {index + 1}: Correct ✅")

            else:
                st.error(f"Question {index + 1}: Incorrect ❌")
                st.write(f"Correct answer: {correct}")

            if question.get("explanation"):
                st.caption(
                    f"Explanation: {question['explanation']}"
                )

        percentage = (score / total) * 100

        st.metric("Final Score", f"{score} / {total}")
        st.progress(int(percentage))
        st.write(f"You scored {percentage:.0f}%.")

        if percentage >= 80:
            st.success("Excellent work! 🎉")
        elif percentage >= 50:
            st.info("Good effort. Revise incorrect questions.")
        else:
            st.warning("Review the PDF and try again.")

st.divider()

st.caption(
    "AI Study Assistant | Python + Streamlit + PyMuPDF + Ollama Cloud"
)

st.caption(
    "This is a learning project. Always verify answers using "
    "your original study PDF."
)