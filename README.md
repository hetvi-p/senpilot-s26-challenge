# UARB Regulatory Document Agent

AI-powered email agent that retrieves regulatory documents from the Nova Scotia Utility and Review Board (UARB) public database and delivers them to users via email.

The agent accepts a **matter number** and **document type** via email, automatically scrapes the UARB website, downloads up to 10 documents, compresses them into a ZIP file, and sends them back to the requester with summarized metadata.

The system is designed as a **production-style asynchronous pipeline** using FastAPI, Celery, Redis, and Playwright.

---

# Demo

Send an email to:

```
dev@hetvi.ca
```
**Note:**
This project is deployed on the free tier of Render. After periods of inactivity, the server may go to sleep and take a few minutes to spin back up.

Because of this, Mailgun requests may timeout if the server is still waking up.

Before sending an email request, please first hit the health endpoint to wake the server:

`https://senpilot-s26-challenge.onrender.com/health`

**Example email:**

```
Hi Agent,

Can you give me Other Documents files from M12205?

Thanks!
```

The agent will:

1. Parse the email
2. Extract the matter number and document type
3. Scrape the UARB website
4. Download up to 10 documents
5. Create a ZIP archive
6. Email the ZIP back to the user

---

# Problem Overview

Utilities submit regulatory filings that contain large numbers of documents.

This agent automates document retrieval by:

* Navigating the UARB public document database
* Finding documents for a specific matter number
* Downloading relevant files
* Packaging them
* Returning them via email

The challenge requirements include:

* Email-triggered automation
* Website navigation
* Document downloads
* ZIP compression
* Email response with metadata and counts

These requirements were provided as part of the Senpilot engineering challenge. 

---

# Example Response Email

```
Hi User,

M12205 is about the Halifax Regional Water Commission -
Windsor Street Exchange Redevelopment Project ($69,270,000).

It relates to Capital Expenditure within the Water category.

The matter had an initial filing on April 7, 2025 and a final filing on October 23, 2025.

I found:
13 Exhibits
5 Key Documents
21 Other Documents
0 Transcripts
0 Recordings

I downloaded 10 of the 21 Other Documents and attached them as a ZIP.
```

---

# System Architecture

The system is built as an **event-driven pipeline**.

```
User Email
    ↓
Mailgun Webhook
    ↓
FastAPI API
    ↓
Celery Task Queue
    ↓
Playwright Scraper
    ↓
Document Downloader
    ↓
ZIP Compressor
    ↓
Email Sender
```

---

# Tech Stack

Backend

* FastAPI
* Python 3.11+

Async Processing

* Celery
* Redis

Web Scraping

* Playwright

Email

* Mailgun

Deployment

* Docker
* Render

Configuration

* Pydantic Settings

---

# Project Structure

```
app
├── api
│   └── routes
│       ├── health.py
│       └── mailgun_webhook.py
│
├── core
│   └── settings.py
│
├── services
│   ├── pipeline.py
│   ├── scraper.py
│   ├── email_parser.py
│   ├── downloader.py
│   └── zipper.py
│
├── workers
│   ├── celery_app.py
│   └── tasks.py
│
└── main.py
```

---

# Core Components

## FastAPI API

Handles incoming requests.

Endpoints:

```
/health
/webhooks/mailgun
```

The Mailgun webhook receives inbound emails and triggers the processing pipeline.

---

## Celery Worker

Handles asynchronous tasks:

* document scraping
* downloads
* compression
* response email

Tasks are queued through Redis.

---

## Playwright Scraper

The scraper automates the following workflow:

1. Open the UARB database

```
https://uarb.novascotia.ca/fmi/webd/UARB15
```

2. Enter the matter number

3. Navigate to the correct tab

* Exhibits
* Key Documents
* Other Documents
* Transcripts
* Recordings

4. Download up to 10 documents.

The site UI for these steps is shown in the challenge document screenshots. 

---

## Email Parser

Extracts structured data from natural language emails.

Example:

```
"Can you give me Other Documents files from M12205?"
```

Parsed result:

```
matter_number = M12205
document_type = Other Documents
```

---

## ZIP Generator

Downloaded files are compressed into:

```
matter_M12205_other_documents.zip
```

---

## Email Response

The agent sends a response email containing:

* document counts
* matter metadata
* ZIP attachment

---

# Environment Variables

Example `.env`

```
APP_ENV=local
APP_NAME=uarb-matter-mail-agent
BASE_URL=http://localhost:8000

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

MAILGUN_API_KEY=xxxx
MAILGUN_DOMAIN=hetvi.ca
MAILGUN_FROM="UARB Agent <postmaster@hetvi.ca>"
MAILGUN_WEBHOOK_SIGNING_KEY=xxxx

UARB_BASE_URL=https://uarb.novascotia.ca/fmi/webd/UARB15

MAX_DOCS=10
MAX_ZIP_MB=20
```

---

# Running Locally

## 1 Install dependencies

```
pip install -r requirements.txt
playwright install
```

---

## 2 Start Redis

```
redis-server
```

---

## 3 Start API

```
uvicorn app.main:app --reload
```

---

## 4 Start Celery worker

```
celery -A app.workers.celery_app:celery_app worker --loglevel=info
```

---

# Deployment

The project is deployed on **Render** using Docker.

Services:

* FastAPI API
* Celery Worker
* Redis (Render Key Value)

Deployment configuration is defined in:

```
render.yaml
```

The system uses the Playwright Docker image to support browser automation.

---

# Key Design Decisions

## Asynchronous processing

Scraping and downloading documents can take several seconds.

Celery ensures:

* API remains responsive
* tasks run in background workers
* retries are supported

---

## Playwright instead of requests

The UARB site is driven by dynamic forms and buttons.

Playwright allows reliable automation of:

* search
* tab navigation
* file downloads

---

## Email-driven interface

Email provides a simple universal interface:

* no frontend required
* works from any device
* easy to integrate with enterprise workflows

---

# Error Handling

The pipeline includes safeguards for:

* invalid matter numbers
* unsupported document types
* missing documents
* download failures
* retry logic via Celery

---

# Limitations

* Downloads capped at **10 documents**
* Playwright scraping speed depends on site performance
* Email parsing currently uses rule-based extraction

Future improvements could include:

* LLM-powered parsing
* full document indexing
* regulatory precedent search

---

# Future Improvements

Possible extensions:

* RAG-powered regulatory search
* vector database of filings
* Slack or API interface
* automated precedent discovery
* multi-regulator ingestion

---

# Author

Hetvi Patel

Email agent address:

```
dev@hetvi.ca
```

---

# Challenge Context

This project was built as part of the **Senpilot Software Engineering Intern Challenge**, which required building an AI agent that:

* receives email requests
* retrieves documents from the UARB database
* downloads files
* returns them as a ZIP attachment via email. 

