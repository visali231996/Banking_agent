import docx
import json
from typing import TypedDict, Annotated, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
import operator
import os
import logging
import streamlit as st

# Configure the logging settings
logging.basicConfig(filename='logfile.log', level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BankingAgentState(TypedDict): 
    messages: Annotated[Sequence[BaseMessage], operator.add] 
    user_id: str 
    authenticated: bool 
    intent: str 
    account_balance: float | None 
    transaction_amount: float | None 
    recipient_account: str | None 
    risk_score: float 
    needs_approval: bool 
    transaction_history: list[dict]
    pending_action: dict | None

def load_banking_db(file_path):
    # Use the 'file_path' variable passed into the function
    # OR if you want to hardcode it, do it like this:
    path = r"C:\Users\HP\Desktop\AI assignemts\ACCOUNTS.docx"
    
    try:
        doc = docx.Document(path)
        # Join all paragraphs into one single string
        full_text = "".join([p.text for p in doc.paragraphs]).strip()
        
        data = json.loads(full_text)
        return data["ACCOUNTS_DB"], data["TRANSACTIONS_DB"]
    except Exception as e:
        logging.error("path specified is wrong or json file is not uploaded")
        print(f"Error: {e}")
        return {}, []

# Usage
ACCOUNTS_DB, TRANSACTIONS_DB = load_banking_db("ACCOUNTS.docx")

import re
from datetime import datetime

def authenticate_user(state: BankingAgentState):
    # STEP 1: If already authenticated in a previous turn, skip PIN check
    if state.get("authenticated") is True:
        return {"authenticated": True} 

    # STEP 2: Only check for PIN if we aren't authenticated yet
    human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    if not human_messages:
        return {"authenticated": False}
        
    user_input = human_messages[-1].content
    current_user = ACCOUNTS_DB.get(state.get("user_id", "ACC-001"))
    
    # Check if PIN exists in the latest input
    if current_user and current_user["pin"] in user_input:
        return {
            "authenticated": True, 
            "messages": [AIMessage(content="✅ Authenticated.")]
        }
    
    return {
        "authenticated": False, 
        "messages": [AIMessage(content="🔒 PIN required to proceed.")]
    }

def check_balance(state: BankingAgentState):
    """Retrieves the current balance for the authenticated user."""
    user_id = state.get("user_id", "ACC-001") # Default for testing
    account_info = ACCOUNTS_DB.get(user_id)
    
    if account_info:
        balance = account_info["balance"]
        msg = f"🏦 Your current account balance is: **${balance:,.2f}**"
        return {
            "account_balance": balance,
            "messages": [AIMessage(content=msg)]
        }
    else:
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find your account details.")]}
    
def intent_router(state: BankingAgentState):
    """Decides which node to go to based on the classified intent."""
    intent = state.get("intent")
    print(f"--- DEBUG: Router routing for intent: {intent}")
    if intent == "confirm_action":
        return "execute"
    if intent == "balance":
        return "check_balance"
    elif intent == "transfer":
        return "validate_transfer"
    elif intent == "history":
        return "get_history"
    else:
        return END
def classify_intent(state: BankingAgentState):
    print("--- DEBUG: Classifying Intent ---")
    # Always look at the absolute latest message
    latest_text = state["messages"][-1].content.lower().strip()
    
    # Check for confirmation FIRST
    if latest_text == "yes" and state.get("pending_action"):
        logging.info(f"USER {state['user_id']}: Confirmed pending action.")
        print("--- DEBUG: Detected Intent: confirm_action ---")
        return {"intent": "confirm_action"}

    # Get the original user message
    human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    text = human_messages[-1].content.lower()
    
    intent = "unknown"
    amount = None
    recipient = None

    # Check for keywords
    if any(word in text for word in ["history", "transactions", "past", "recent"]):
        intent = "history"
    elif "balance" in text or "money" in text:
        intent = "balance"
    elif "transfer" in text or "send" in text:
        intent = "transfer"
        # Logic to find amount/recipient...
        amounts = re.findall(r'(?:\$|transfer\s|send\s)(\d+)', text)
        if amounts: amount = float(amounts[0])
        acc_match = re.search(r'acc-\d+', text)
        if acc_match: recipient = acc_match.group(0).upper()

    print(f"--- DEBUG: Detected Intent: {intent}")
    logging.info(f"USER {state['user_id']}: Intent detected as {intent} for amount {amount}")
    return {
        "intent": intent, 
        "transaction_amount": amount, 
        "recipient_account": recipient,
        "messages": [] 
    }
def assess_risk(state: BankingAgentState):
    print("--- DEBUG: Assessing Risk ---")
    amount = state.get("transaction_amount") or 0
    user_data = ACCOUNTS_DB.get("ACC-001", {})
    avg = user_data.get("avg_transaction", 1000) # Fallback to 1000
    
    risk = 0.0
    if amount > 5000: risk = 2.0
    elif amount >= 1000 or amount >= (avg * 3): risk = 1.0
    
    print(f"--- DEBUG: Risk Score Calculated: {risk} ---")
    logging.warning(f"SECURITY: Risk assessment for {state['user_id']} - Amount: {amount} - Score: {risk}")
    return {"risk_score": risk}

def execute_transfer(state: BankingAgentState):
    user_id = state.get("user_id", "ACC-001")
    
    # Check if pending_action exists AND is a dictionary
    pending = state.get("pending_action")
    if isinstance(pending, dict) and "amount" in pending:
        amt = pending["amount"]
    else:
        # Fallback to the transaction_amount detected by the classifier
        amt = state.get("transaction_amount") or 0
        
    ACCOUNTS_DB[user_id]["balance"] -= amt
    
    # Log the successful transaction
    logging.info(f"SUCCESS: {user_id} moved ${amt}. Balance: {ACCOUNTS_DB[user_id]['balance']}")
    
    return {
        "messages": [AIMessage(content=f"✅ Transfer completed! New balance: ${ACCOUNTS_DB[user_id]['balance']:,.2f}")],
        "pending_action": None,
        "intent": "none"
    }

def ask_for_approval(state: BankingAgentState):
    amount = state.get("transaction_amount")
    recipient = state.get("recipient_account")
    
    msg = f"⚠️ **Wait!** Transferring ${amount:,.2f} is unusual. Reply 'YES' to confirm."
    
    # Save the details so we don't forget them in the next turn
    return {
        "messages": [AIMessage(content=msg)],
        "pending_action": {"type": "transfer", "amount": amount, "to": recipient}
    }

def route_risk(state: BankingAgentState):
    if state["risk_score"] == 2.0: return "escalate"
    if state["risk_score"] == 1.0: return "approval"
    return "execute"

def get_history(state: BankingAgentState):
    """Filters the transaction list for the specific user."""
    user_id = state.get("user_id", "ACC-001")
    
    # Filter for transactions involving this account
    user_txns = [
        tx for tx in TRANSACTIONS_DB 
        if tx["from_account"] == user_id or tx["to_account"] == user_id
    ]
    
    if not user_txns:
        return {"messages": [AIMessage(content="You have no recent transactions.")]}
    
    # Format the last 5 transactions into a nice string
    history_msg = "📝 **Your Recent Transactions:**\n"
    for tx in user_txns[-5:]:  # Show latest 5
        direction = "OUT" if tx["from_account"] == user_id else "IN"
        history_msg += f"- {tx['timestamp'][:10]} | {direction} | ${tx['amount']:,.2f} | Status: {tx['status']}\n"
        
    return {
        "transaction_history": user_txns,
        "messages": [AIMessage(content=history_msg)]
    }

import uuid

def escalate_to_fraud_team(state: BankingAgentState):
    """
    Handles high-risk transactions by blocking execution 
    and escalating to the mock fraud department.
    """
    # Generate a mock Case ID for the user to reference
    print("--- DEBUG: Reached Fraud Node ---") # Add this!
    case_id = f"FRD-{uuid.uuid4().hex[:8].upper()}"
    
    amount = state.get("transaction_amount", 0.0)
    recipient = state.get("recipient_account", "Unknown Account")
    
    # Professional but firm security message
    escalation_msg = (
        f"🚨 **Security Alert: Transaction Blocked** 🚨\n\n"
        f"Your request to transfer **${amount:,.2f}** to **{recipient}** has been flagged "
        f"by our automated risk assessment system.\n\n"
        f"**Status:** Escalated for Manual Review\n"
        f"**Reference Number:** {case_id}\n\n"
        f"For your protection, this transfer has been halted. Our fraud prevention team "
        f"will review the activity and contact you within 24 hours. No funds have been moved."
    )
    
    return {
        "messages": [AIMessage(content=escalation_msg)],
        "needs_approval": False  # Escalation overrides any pending approval
    }





st.title(" JSON-Doc bank Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

for msg in st.session_state.messages:
    # msg is a LangChain object, so we check .type or isinstance
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

if prompt := st.chat_input("my pin is 1234,check my balance"):
    st.chat_message("user").markdown(prompt)
    user_msg = HumanMessage(content=prompt)
    st.session_state.messages.append(user_msg)

    workflow = StateGraph(BankingAgentState)
    # 1. Define Nodes
    workflow.add_node("auth", authenticate_user)
    workflow.add_node("classify", classify_intent)
    workflow.add_node("check_balance", check_balance)
    workflow.add_node("get_history", get_history)
    workflow.add_node("validate_transfer", assess_risk) 
    workflow.add_node("execute", execute_transfer)
    workflow.add_node("escalate", escalate_to_fraud_team)
    workflow.add_node("ask_approval", ask_for_approval)

    # 2. Entry Point
    workflow.set_entry_point("auth")

    # 3. Auth -> Classify (Linear progression if successful)
    # 1. AUTH -> CLASSIFY
    # This moves from Auth to Classify automatically if authenticated
    workflow.add_conditional_edges(
        "auth",
        lambda state: "classify" if state.get("authenticated") else END
    )

    # 2. CLASSIFY -> ACTIONS
    # IMPORTANT: This must be a conditional edge from 'classify'
    workflow.add_conditional_edges(
        "classify",
        intent_router,
        {
            "check_balance": "check_balance",
            "validate_transfer": "validate_transfer",
            "get_history": "get_history",
            "execute": "execute",
            END: END
        }
    )

    # 3. VALIDATE -> RISK ROUTE
    # This moves from risk assessment to the final action
    workflow.add_conditional_edges(
        "validate_transfer",
        route_risk,
        {
            "execute": "execute",
            "escalate": "escalate",
            "approval": "ask_approval"
        }
    )

    # 6. Terminal Edges
    workflow.add_edge("execute", END)
    workflow.add_edge("check_balance", END)
    workflow.add_edge("get_history", END)
    workflow.add_edge("escalate", END)
    workflow.add_edge("ask_approval", END)
    app = workflow.compile()

    try:
        graph_png = app.get_graph().draw_mermaid_png()
        
        # 3. Display it in the Streamlit Sidebar or Main page
        with st.sidebar:
            st.subheader("Agent Workflow")
            st.image(graph_png)
    except Exception as e:
        # If graphviz isn't installed, this might fail silently
        print(f"Could not generate graph: {e}")

    
# Initial State with PIN included so it passes the 'auth' node
    initial_state = {
        "messages": st.session_state.messages,
        "user_id": "ACC-001",
        "authenticated": st.session_state.authenticated,
        "intent": "none",
        "risk_score" :0.0,
        "pending_action" : st.session_state.get("pending_action", None)
    }

    # Run the app with a clear recursion limit
    result = app.invoke(initial_state, config={"recursion_limit": 10})

 


    response_msg = result["messages"][-1]
    st.session_state.authenticated = result.get("authenticated", False)
    st.session_state.pending_action = result.get("pending_action")
    
    # 4. Show assistant message and save to state
    with st.chat_message("assistant"):
        st.markdown(response_msg.content)
    
    st.session_state.messages.append(response_msg)