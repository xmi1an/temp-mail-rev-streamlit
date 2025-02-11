import streamlit as st
import requests
import string
import random
import time
import re

# Constants
API_BASE_URL = st.secrets["API_BASE_URL"]


# Function to get domains with caching
@st.cache_data(ttl=3600)
def get_domains():
    try:
        response = requests.get(f"{API_BASE_URL}/domains")
        response.raise_for_status()
        return response.json()["domains"]
    except requests.RequestException as e:
        st.error(f"Error fetching domains: {e}")
        return []


# Function to generate email address
def generate_email(domain, name):
    data = {"domain": domain, "name": name, "token": ""}
    try:
        response = requests.post(f"{API_BASE_URL}/email/new", json=data)
        response.raise_for_status()
        return response.json()["email"]
    except requests.RequestException as e:
        st.error(f"Error generating email: {e}")
        return None


# Function to check for incoming messages
def check_messages(email):
    try:
        response = requests.get(f"{API_BASE_URL}/email/{email}/messages")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching messages: {e}")
        return []


# Function to generate a random word
def random_word(length=6):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


# Function to validate custom email name
def validate_email_name(name):
    pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    return bool(pattern.match(name))


def main():
    # Set page configuration
    st.set_page_config(page_title="Temp-Mail", layout="wide")
    st.title("📬 Temp-Mail")

    # Initialize session state variables
    if "generated_email" not in st.session_state:
        st.session_state["generated_email"] = None
    if "polling_complete" not in st.session_state:
        st.session_state["polling_complete"] = False
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "polling_attempts" not in st.session_state:
        st.session_state["polling_attempts"] = 0
    if "max_attempts" not in st.session_state:
        st.session_state["max_attempts"] = 6  # 6 attempts x 5 seconds = 30 seconds
    if "custom_name" not in st.session_state:
        st.session_state["custom_name"] = ""

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        name_length = st.number_input(
            "Random Name Length",
            min_value=4,
            max_value=20,
            value=6,
            step=1,
            help="Define the length of the randomly generated email prefix.",
        )
        st.markdown("---")

    # Tabs for navigation
    tabs = st.tabs(["📧 Generate Email", "📥 Check Messages"])

    # -------------------- Tab 1: Generate Email --------------------
    with tabs[0]:
        st.subheader("Generate a Temporary Email Address")

        # Fetch domains
        with st.spinner("Fetching available domains..."):
            domains = get_domains()

        if not domains:
            st.error("Unable to fetch domains. Please try again later.")
            st.stop()

        # Display domains in a dropdown and email name input side by side using columns
        col1, col2 = st.columns([2, 2])

        with col1:
            domain_names = [domain["name"] for domain in domains]
            if st.session_state["generated_email"]:
                # Pre-select the domain based on the current email
                current_domain = st.session_state["generated_email"].split("@")[-1]
                if current_domain in domain_names:
                    default_index = domain_names.index(current_domain)
                else:
                    default_index = 0
            else:
                default_index = 0

            selected_domain = st.selectbox(
                "Select Domain", domain_names, index=default_index, key="select_domain"
            )

        with col2:
            # st.markdown("### Custom Email Name (Optional)")
            email_name = st.text_input(
                "Custom Email Name (Optional)",
                value=st.session_state["custom_name"],
                help="Use letters, numbers, underscores (_), or hyphens (-). Leave blank for a random name.",
            )

        # Update session state with custom name
        st.session_state["custom_name"] = email_name.strip()

        # Button to generate a new email aligned center
        generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
        with generate_col2:
            if st.button("🔄 Generate New Email"):
                if email_name:
                    if validate_email_name(email_name):
                        name_to_use = email_name
                    else:
                        st.error(
                            "Invalid email name. Only letters, numbers, underscores, or hyphens are allowed."
                        )
                        st.stop()
                else:
                    name_to_use = random_word(length=int(name_length))

                with st.spinner("Generating your temporary email..."):
                    generated_email = generate_email(selected_domain, name_to_use)

                if generated_email:
                    st.session_state["generated_email"] = generated_email
                    st.session_state["messages"] = []  # Reset messages
                    st.session_state["polling_complete"] = False
                    st.session_state["polling_attempts"] = 0
                    st.session_state["custom_name"] = (
                        ""  # Reset custom name after generation
                    )
                    st.success(f"**Generated Temp Email:** `{generated_email}`")

        # Display the generated email in a styled container
        if st.session_state["generated_email"]:
            st.markdown("---")
            email_container = st.container()
            email_col1, email_col2 = st.columns([3, 1])
            with email_col1:
                st.markdown(
                    f"### **Your Temporary Email:** `{st.session_state['generated_email']}`"
                )
            with email_col2:
                # Copy to clipboard functionality using a workaround
                copy_code = f"{st.session_state['generated_email']}"
                st.code(copy_code, language="text")  # Display email
                # Note: Streamlit does not have a built-in clipboard copy, but you can use JavaScript hacks or custom components.

    # -------------------- Tab 2: Check Messages --------------------
    with tabs[1]:
        if not st.session_state["generated_email"]:
            st.info(
                "Please generate an email address from the **Generate Email** tab first."
            )
            st.stop()

        st.subheader(
            f"📥 Check Incoming Emails for `{st.session_state['generated_email']}`"
        )

        # Divider
        st.markdown("---")

        # Placeholder for messages and status
        messages_placeholder = st.empty()

        # Function to perform polling
        def perform_polling():
            for attempt in range(st.session_state["max_attempts"]):
                st.session_state["polling_attempts"] += 1
                with messages_placeholder.container():
                    messages = check_messages(st.session_state["generated_email"])
                    if messages:
                        st.session_state["messages"] = messages
                        st.success(f"📬 **{len(messages)}** New Message(s) Found:")
                        for idx, msg in enumerate(messages, 1):
                            with st.expander(f"📩 Message {idx}: {msg['subject']}"):
                                st.markdown(f"**From:** {msg['from']}")
                                st.markdown(f"**Subject:** {msg['subject']}")
                                st.markdown(f"**Body:** {msg['body_text']}")
                        st.session_state["polling_complete"] = True
                        return
                    else:
                        st.info(
                            f"No new messages... (Attempt {attempt + 1} of {st.session_state['max_attempts']})"
                        )
                # Wait for 5 seconds before next attempt
                time.sleep(5)
            # After polling attempts are complete
            st.session_state["polling_complete"] = True
            with messages_placeholder.container():
                st.info("✅ Polling complete. No new messages found.")

        # Check if polling is already complete
        if (
            not st.session_state["polling_complete"]
            and st.session_state["polling_attempts"] < st.session_state["max_attempts"]
        ):
            with st.spinner("🔍 Checking for new messages..."):
                perform_polling()

        # Display messages if any
        if st.session_state["messages"]:
            st.success(
                f"📬 **{len(st.session_state['messages'])}** New Message(s) Found:"
            )
            for idx, msg in enumerate(st.session_state["messages"], 1):
                with st.expander(f"📩 Message {idx}: {msg['subject']}"):
                    st.markdown(f"**From:** {msg['from']}")
                    st.markdown(f"**Subject:** {msg['subject']}")
                    st.markdown(f"**Body:** {msg['body_text']}")

        # After polling, show manual check button
        if st.session_state["polling_complete"]:
            manual_check_col1, manual_check_col2, manual_check_col3 = st.columns(
                [1, 2, 1]
            )
            with manual_check_col2:
                if st.button("🔄 Manually Check for New Messages"):
                    with st.spinner("🔍 Checking for messages..."):
                        messages = check_messages(st.session_state["generated_email"])
                    if messages:
                        st.session_state["messages"] = messages
                        st.success(f"📬 **{len(messages)}** New Message(s) Found:")
                        for idx, msg in enumerate(messages, 1):
                            with st.expander(f"📩 Message {idx}: {msg['subject']}"):
                                st.markdown(f"**From:** {msg['from']}")
                                st.markdown(f"**Subject:** {msg['subject']}")
                                st.markdown(f"**Body:** {msg['body_text']}")
                    else:
                        st.info("✅ No new messages found.")

        # Footer Information
        st.markdown("---")
        st.info(
            "🔄 Automatically checked for new messages every 5 seconds for 30 seconds."
        )


# Run the app
if __name__ == "__main__":
    main()
