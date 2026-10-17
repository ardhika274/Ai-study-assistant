# AI Study Assistant

A student-focused AI web application that helps learners study from PDFs.

## Features

- Upload a text-based PDF
- Generate a summary
- Create practice questions
- Explain difficult topics
- Chat with PDF notes
- Generate and take MCQ quizzes

## Built With

- Python
- Streamlit
- PyMuPDF
- Ollama Cloud API

## Run Locally

1. Clone this repository
2. Install packages:

```bash
python -m pip install -r requirements.txt
```

3. Create `.streamlit/secrets.toml`:

```toml
OLLAMA_API_KEY = "your-api-key"
```

4. Run:

```bash
python -m streamlit run app.py
```

## Important

Do not upload confidential documents. AI outputs may contain mistakes, so verify answers with the original PDF.

## Developer

Built by Ardhika Sirothia.