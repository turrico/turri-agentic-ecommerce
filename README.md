# Connecting Communities

## Turri.CR's Agentic E-commerce Platform

![Architecture Diagram](docs/architecture_diagram.png)

This repository contains the source code for **Turri.AI**, a multi-agent system built with the **Google Agent Development Kit (ADK)** for the [Agent Development Kit Hackathon with Google Cloud](https://adk-hackathon.devpost.com/).

Our system connects to a real-world WooCommerce store to provide intelligent, personalized experiences for customers and powerful, on-demand analytics for producers.

> **[➡️ Read our full Submission for a detailed project overview.](https://turrico.github.io/turri-agentic-ecommerce/)**

---

## 🚀 Get it Running

This project is containerized with Docker for easy setup.

### Prerequisites

- Docker
- Docker Compose

### 1. Environment Setup

First, create your local environment file from the template.

```bash
cp .env.template .env
```

Then, open the `.env` file and fill in your credentials for Google Cloud, WooCommerce, PostgreSQL, and Redis.

### 2. Launch the Stack

Build the Docker image and start all the necessary services (API, PostgreSQL database, and Redis).

```bash
docker compose up -d --build
```

The API will be available at `http://127.0.0.1:${API_PORT}` (replace `${API_PORT}` with the value set in your `.env` file).

### 3. Explore the API

You can explore all available endpoints via the interactive documentation (powered by Swagger UI) at:
http://127.0.0.1:${API_PORT}/docs

### 4. Populate the Database

To make the agents functional, you'll need to populate the database. Use the `/admin` endpoints in the API documentation to trigger the data ingestion scripts for WooCommerce and Google Analytics.

---

## 💬 Chat Demo Frontends

The frontends used in our chat demo can be found in the [`frontend/`](./frontend/) directory:

- `consumer.html`, `producer.html`, `onboarding.html`

These minimal HTML files demonstrate how to interact with the API for different conversation flows in the demo.

---

## 📂 Code Structure

The project is organized into three main directories within `src/`:

- `src/api`: Handles the FastAPI web server, endpoints, and request/response models.
- `src/agents`: Contains all the ADK agent definitions, tools, and multi-agent logic for both customers and producers.
- `src/turri_data_hub`: Manages the data layer, including database models (SQLModel), data ingestion scripts (from WooCommerce, BigQuery), and the core recommendation engine logic.

---

## 🛠️ Key Technologies

- **AI & Agents**: Google Agent Development Kit (ADK), Gemini Models, Google `text-embedding-004`.
- **Cloud & Data**: Google BigQuery, PostgreSQL with `pgvector`, Redis.
- **Backend**: FastAPI, Docker, SQLModel.
