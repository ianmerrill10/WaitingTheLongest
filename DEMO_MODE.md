# Waiting The Longest™ - Demo Mode

This document explains how to run the application in Demo Mode.

## Overview

Demo Mode allows you to experience the full functionality of the Waiting The Longest™ platform using generated data linked to real shelter records. This is useful for development, testing, and showcasing the application features without needing live animal data.

## Prerequisites

- Python 3.8+
- Dependencies installed (`pip install -r backend/requirements.txt`)
- Database initialized

## Setup

1.  **Generate Demo Data**
    Run the following command to populate the database with 50 demo animals linked to real shelters:
    ```bash
    python backend/tools/generate_demo_data.py
    ```
    *Note: This script uses `placedog.net` and `placekitten.com` for placeholder images.*

2.  **Start the Backend Server**
    Start the FastAPI server:
    ```bash
    python -m uvicorn backend.app.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

3.  **Access the Frontend**
    Open `http://127.0.0.1:8000/demo` in your web browser.

## Features in Demo Mode

-   **Browse Animals**: View a list of 50 demo animals with various breeds, ages, and statuses.
-   **Filtering**: Test filters for Species, Age, Size, Gender, and State.
-   **Animal Details**: Click on any animal to view their detailed profile, including:
    -   Calculated "Days Waiting"
    -   Shelter contact information (from real shelter data)
    -   Affiliate product recommendations
    -   Similar animals
-   **Shelter Directory**: Browse the list of 1,172 real shelters.

## Troubleshooting

-   **No Animals Showing**: Ensure you ran the `generate_demo_data.py` script. Check the database count.
-   **Server Error**: Check the terminal output for any Python errors. Ensure all dependencies are installed.
-   **Images Not Loading**: Ensure you have an internet connection, as placeholder images are fetched from external services.

## Resetting Data

To clear the demo data and start fresh (e.g., for real ingestion), you would typically clear the `animals` and `observations` tables in the database.
