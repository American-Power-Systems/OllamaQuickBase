# Private AI Document Processor (Azure/Ollama)

## 1. Executive Summary

This application is a private, self-hosted AI microservice designed to extract structured data from unstructured documents (Purchase Orders, Invoices, etc.).

**Purpose:** To replace our previous OpenAI-based workflow with a 100% "closed" model. This migration is driven by customer compliance requirements to ensure sensitive document data never leaves our internal Azure environment or is sent to third-party public APIs.

**Key Benefits:**
*   **Data Privacy:** Zero data egress. All processing happens on our private Azure VM.
*   **Cost Control:** Uses a fixed-cost CPU server with a job queue, eliminating variable per-token API fees.
*   **Flexibility:** "Stateless" design allows QuickBase to dynamically dictate the extraction logic via JSON prompts stored in a QuickBase "Prompt Library".

## 2. System Architecture

This application functions as the "Brain" in our document automation pipeline. It sits between our OCR layer and our database.

### The "Microservice" Role
This app is headless (no user interface). It accepts tasks via a REST API, processes them asynchronously, and writes the results directly back to QuickBase.

### The Data Flow
1.  **Trigger:** A document is emailed to QuickBase.
2.  **OCR:** QuickBase triggers our Replit App, which extracts raw text from the attachment.
3.  **Hand-off:** The Replit App sends a payload to this Azure Application.
    *   **Payload:**
        ```json
        {
          "record_id": 123,
          "po_text": "Raw OCR text...",
          "target_table_id": "bck7...",
          "target_field_ids": {"payment_terms": 6, "total": 7},
          "prompt_json": {"payment_terms": "string", "total": "string"}
        }
        ```
4.  **Queue:** This app accepts the payload and adds it to a Redis Job Queue (responding immediately with "202 Accepted").
5.  **Processing:** A background Worker Process pulls the job:
    *   Feeds `po_text` and `prompt_json` (received from QuickBase) into the local Ollama (Llama 3) model.
    *   Waits for the AI to extract the JSON answers (approx. 3-5 mins per doc).
6.  **Completion:** The Worker uses the `target_table_id` and `target_field_ids` to write the results directly back to QuickBase.

## 3. Technical Stack

This application is deployed on a standard Azure Virtual Machine (Ubuntu 22.04 LTS).

*   **API Layer:** Python Flask + Gunicorn (Handles incoming HTTP requests).
*   **Queue System:** Redis Server + RQ (Redis Queue) (Manages the workload to prevent server overload).
*   **AI Engine:** Ollama running a local Llama 3 model (Performs the actual extraction logic).
*   **Infrastructure:** Azure B-series VM (CPU-optimized, cost-effective).

## 4. Operational Notes

*   **Latency:** This is a batch processing system, not real-time. Expect a 5-10 minute turnaround time from upload to data population.
*   **Scaling:** The system is designed to handle ~100 documents/day sequentially. If volume increases significantly, we can vertically scale the VM or add more Worker processes.
*   **Maintenance:**
    *   Logs are managed via systemd (services: `ai-api` and `ai-worker`).
    *   To update the extraction logic (e.g., adding a new field), do not edit this code. Update the JSON Prompt stored in the QuickBase "Prompt Library" table.

## 5. Deployment

Deployments are automated via GitHub Actions.
**Important:** This repository contains both a frontend (client) and backend (generated_backend). For the Azure AI Processor, we only deploy the contents of `generated_backend`.

1.  **Push to main:** Triggers the pipeline.
2.  **Action:** SSHs into the Azure VM, pulls the latest code, updates dependencies (`pip install`), and restarts the systemd services.
