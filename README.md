# FinRisk Intelligence
### AI-Powered Financial Risk Intelligence & Event-Driven Portfolio Stress Testing

**S&P Global & Crisil Campus Hackathon 2026**

**Candidate Name:** Pulkit Agrawal  
**College / Campus:** VIT Bhopal University  
**Submission Type:** Individual  

---

## 🔗 Submission Links

| Deliverable | Link |
|---|---|
| 🌐 Public GitHub Repository | https://github.com/PulkitAg13/VIT_Bhopal_University-Pulkit_Agrawal-Hackathon_ |
| 🎥 Demo Video | **[PASTE UNLISTED YOUTUBE LINK HERE]** |
| 📊 Presentation Deck | **[PASTE PRESENTATION LINK HERE]** |

> **Before submission:** Replace the two placeholder links above with the final publicly accessible YouTube demo link and presentation/deck link.

---

# 1. Project Overview

## The Problem

Financial risk teams continuously monitor large volumes of financial news, market information, and social-media-driven signals. The challenge is not simply finding information — it is determining **which events matter, how significant they are, whether multiple sources corroborate the same event, and how those events could affect an existing portfolio**.

Traditional monitoring workflows often require analysts to manually read large amounts of unstructured text, identify relevant companies or entities, classify events, assess sentiment and severity, and then translate those signals into portfolio-level risk decisions.

This creates a gap between:

**Unstructured Financial Information → Risk Intelligence → Portfolio Decision-Making**

---

## The Solution

**FinRisk Intelligence** is an AI-powered financial risk intelligence platform that converts unstructured financial information into structured, explainable risk signals and connects those signals directly to portfolio stress testing.

The platform processes financial text through a mandatory NLP pipeline that performs:

- Financial-domain sentiment analysis
- Financial event classification
- Named entity extraction and resolution
- Semantic similarity and event deduplication
- Novelty detection
- Source corroboration
- Explainable impact scoring
- Event clustering and lifecycle tracking

Each detected event can produce structured intelligence including:

- **Sentiment Score:** -1 to +1
- **Event Classification:** Financial event taxonomy
- **Impact Score:** 1–10
- Affected entities
- Source and provenance information
- Explainable risk factors
- Event cluster and lifecycle information

High-impact eligible events can automatically trigger the portfolio stress-testing engine, creating a direct connection between **event intelligence and financial risk assessment**.

---

# 2. Core Capabilities

## 🧠 AI-Powered Risk Intelligence

### Financial Sentiment Analysis

Uses **ProsusAI/FinBERT** to determine financial-domain sentiment rather than relying on generic sentiment analysis.

Outputs include:

- Positive
- Neutral
- Negative
- Continuous sentiment score

---

### Event Classification

Uses **facebook/bart-large-mnli** for zero-shot classification into the platform's financial event taxonomy.

Examples of event categories include:

- Geopolitical
- Macroeconomic
- Credit Event
- M&A
- Product Launch
- Regulatory
- Market-related events
- Other financial risk events

---

### Entity Extraction & Resolution

Uses transformer-based Named Entity Recognition with:

**dslim/bert-base-NER**

The extracted entities are subsequently resolved against canonical financial entities and enriched using the project's entity configuration.

This allows the system to connect multiple mentions of the same company or financial entity to a common risk timeline.

---

### Semantic Deduplication & Event Clustering

The system uses sentence embeddings from:

**all-MiniLM-L6-v2**

to identify semantically similar information.

Events can be grouped using:

- Semantic similarity
- Event classification
- Entity overlap
- Temporal proximity

This helps prevent multiple reports about the same underlying event from being treated as completely independent risk signals.

---

### Explainable Impact Scoring

FinRisk Intelligence generates an explainable **1–10 Impact Score** using multiple risk-related components.

The scoring process considers factors such as:

- Sentiment
- Event severity
- Novelty
- Entity relevance
- Corroboration
- Recency
- Other contextual risk signals

The system exposes the reasoning behind the impact score rather than treating the score as an opaque prediction.

---

### Source Corroboration

Events can be evaluated across multiple sources using provenance information such as:

- Provider
- Domain
- Source type
- Source URL

This allows the system to distinguish between isolated signals and events supported by multiple sources.

---

# 3. Event-Driven Portfolio Stress Testing

The second major component of FinRisk Intelligence is the **portfolio stress-testing engine**.

Instead of stopping after identifying a risky event, the platform asks:

> **"What could this event do to the portfolio?"**

The system maintains a synthetic wholesale banking portfolio containing:

- **18 positions**
- **6 asset classes**
- **$100M total portfolio value**

The stress engine supports multiple predefined stress scenarios and evaluates asset-level impacts.

### Example Workflow

```text
Financial News / Social Signal
              ↓
       NLP Risk Engine
              ↓
   Entity + Event Detection
              ↓
 Sentiment + Impact + Novelty
              ↓
      Event Classification
              ↓
    Event Clustering
              ↓
 High-Impact Event Detected
              ↓
      Stress Test Trigger
              ↓
     Portfolio Simulation
              ↓
 Asset-Level Impact Analysis
              ↓
     Portfolio Risk View
