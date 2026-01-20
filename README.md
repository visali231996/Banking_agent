# BANKING TRANSACTION AGENT
An intelligent Banking Assistant built using LangGraph, LangChain, and Streamlit, capable of authenticating users, checking balances, transferring funds, assessing transaction risk, and escalating suspicious activity — all backed by a JSON database stored inside a DOCX file.

---
## FEATURES
*  PIN-based Authentication

* Check Account Balance

* Money Transfers

* Risk Assessment Engine

* Approval Flow for Medium-Risk Transactions

* Fraud Escalation for High-Risk Transfers

* Transaction History Viewer

* Stateful Agent using LangGraph

* DOCX-based JSON Database

* Interactive Streamlit Chat UI

* Live Agent Workflow Visualization (Mermaid Graph)

## TECH STACK
```
| Technology  | Purpose                        |
| ----------- | ------------------------------ |
| Python      | Core language                  |
| Streamlit   | UI & Chat Interface            |
| LangGraph   | Agent workflow & state machine |
| LangChain   | Message abstractions           |
| python-docx | Read DOCX JSON database        |
| Logging     | Security & audit logs          |
```

## PROJECT STRUCTURE
```
.
├── sample.py                # Main Streamlit app
├── ACCOUNTS.docx            # JSON database (accounts + transactions)
├── logfile.log              # Security & activity logs
├── README.md                # Project documentation
```

## Installation & Setup
1. Clone the Repository
```
git clone https://github.com/visali231996/Banking_agent.git
cd json-doc-banking-agent
```
2.Install the dependencies
```
pip install streamlit langgraph langchain python-docx
```
3.Run the application
```
streamlit run sample.py
```
## SECURITY LOGIC
```
| Risk Level | Action                     |
| ---------- | -------------------------- |
| Low        | Auto-execute               |
| Medium     | User confirmation required |
| High       | Fraud escalation & block   |
```
## LIMITATIONS

* Single-user demo (ACC-001)

* Local DOCX file dependency

* Not production-grade security

* Demo-level NLP intent detection

