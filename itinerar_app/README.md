# Amadeus Itinerary Generator

Streamlit web app that parses Amadeus flight segment lines and formats a Slovenian itinerary for copying into email.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Deploy this repository as a Streamlit app, using `app.py` as the entry point and `requirements.txt` for dependencies.

Do not paste passenger names, ticket numbers, or other personal data into the app. This initial version is a practical starting point; verify parsed times and connection calculations before sending an itinerary to a customer.
