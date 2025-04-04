# 🌍 TravelBuddy – AI-Powered Travel Planning Assistant

**TravelBuddy** is a next-gen AI travel planner that creates fully personalized travel itineraries through natural language conversations. Built using a modular, multi-agent architecture, semantic search, and real-time travel APIs, it offers a unified, intelligent travel planning experience.

---

## ✈️ Key Features

- 🧠 **Multi-Agent Architecture** – Dedicated AI agents for flights, hotels, weather, events, safety, and itinerary creation.
- 🔍 **Semantic Search** – Vector embeddings enable personalized travel recommendations based on user intent.
- 🏨 **Real-Time Integrations** – Connects with leading travel APIs like OpenWeather, Amadeus, Booking.com, Google Places, and more.
- 📊 **Snowflake Analytics** – Stores and visualizes trends in travel data, such as hotel pricing, weather patterns, and attraction popularity.
- 🧾 **Auto-Generated Itineraries** – End-to-end travel plans, exportable as PDFs.

---
## CodeLabs : https://codelabs-preview.appspot.com/?file_id=1fQP0SWzcP6RK2q4F1uP7kdM_ib6DFbKTyXTciWjbvb0#0
## 📌 Project Overview

### Scope

- Proof-of-concept travel planning platform with two core microservices
- Real-time travel data ingestion from 2–3 third-party APIs
- Vector search capability using Pinecone
- Snowflake-powered analytics
- Minimal front-end interface for demo

### Stakeholders

- Individual travelers
- Travel agencies
- Corporate travel departments
- Tourism and destination marketing organizations

---

## 🚧 Problem Statement

### Challenges

- Travel planning is fragmented across platforms
- Lack of semantic search and true personalization
- Manual itinerary creation is time-consuming
- Contextual factors like weather or advisories are not integrated

### Opportunities

- Natural language understanding for preferences
- Vector embeddings for intent-based recommendations
- Unified travel experience in one platform
- Learn from user feedback to improve over time

---

## 🔗 Data Sources

| Service               | API                           |
|-----------------------|-------------------------------|
| Weather               | OpenWeather API               |
| Flights               | Amadeus Flight Offers API     |
| Hotels                | Booking.com / Hotels.com API  |
| Attractions           | Google Places / TripAdvisor   |
| Events                | Ticketmaster / Eventbrite     |
| Safety Advisories     | Government Travel APIs        |
| Synthetic User Data   | Internal for testing          |

---

## 🔄 Data Pipeline

1. **Data Ingestion** – Connect to real-time APIs
2. **Processing & Transformation** – Normalize and structure data
3. **Vector Embedding** – Generate semantic vectors
4. **Storage** – Pinecone (vector) + Snowflake (analytics)
5. **Analytics & Trends** – User behavior, pricing, reviews
6. **Recommendation Engine** – Personalized suggestions
7. **Itinerary Generator** – Full trip creation

---

## 🧠 Snowflake Analytics

- Weather trend analysis (last 5-day patterns)
- Hotel pricing analytics (by location and type)
- Attraction popularity (by reviews and frequency)
- Event engagement tracking
- Predictive modeling for trip recommendations

---

## 🧩 Microservices & APIs

| Service              | Purpose                              | Example Endpoint                          |
|----------------------|---------------------------------------|-------------------------------------------|
| Weather              | Forecasts & historical trends         | `/api/weather/forecast/{location}`        |
| Flight Search        | Flight offers and pricing             | `/api/flights/search`                     |
| Hotel Booking        | Accommodation matching                | `/api/hotels/search`                      |
| Attractions & Tours  | POI recommendations                   | `/api/attractions/recommended`           |
| Event Discovery      | Local events during travel            | `/api/events/search/{location}`           |
| Safety Advisory      | Risk alerts and travel warnings       | `/api/safety/advisory/{country}`          |
| Itinerary Generator  | Full trip plan generation             | `/api/itinerary/generate`                 |

---

## ✅ Milestones

### Phase 1: Foundation
- Architecture & Snowflake schema design
- Dev environment setup
- API planning

### Phase 2: Core Development
- Snowflake pipelines
- First microservice
- Vector DB (Pinecone) setup

### Phase 3: Feature Implementation
- Second microservice
- Dashboard in Snowflake
- Basic recommendation logic

### Phase 4: Finalization
- Testing and bug fixes
- Project presentation & live demo
- Final documentation

---

## ⚠️ Risks & Mitigation

> _TBD – Please add this section based on your project experience_

---

## 🎯 Expected Outcomes

- Functional microservices with working endpoints
- Snowflake views for:
  - Weather analytics
  - Hotel pricing
  - Attraction popularity
- Basic semantic search via Pinecone
- Live demo of travel recommendation + itinerary generation

---

## 💡 Benefits

- Personalized travel experience
- Unified planning in one assistant
- Enhanced discovery of overlooked options
- Smarter, faster itinerary building

---

## 📁 Tech Stack

- **LLM Agents**: CrewAI + LLMs (e.g., LLaMA 3 via Groq)
- **Vector DB**: Pinecone
- **Data Warehouse**: Snowflake
- **APIs**: OpenWeather, Amadeus, Booking.com, TripAdvisor, Eventbrite, and more
- **Frontend**: (MVP or CLI-based demo)

---

## 📸 Demo & Screenshots

> _Add screenshots or a Loom link to your final project presentation here_

---

## 👥 Contributors

- Vishal Prasanna
- Sai Srunith Silvery
- Sai Priya Veerabomma

---

## 📜 License

MIT License – Feel free to fork, extend, and build upon TravelBuddy.

---

