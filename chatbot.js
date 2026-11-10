
"use strict";

/* Prevent duplicate initialization if chatbot.js is loaded twice. */
if (!window.finAssistChatbotInitialized) {
    window.finAssistChatbotInitialized = true;

    document.addEventListener("DOMContentLoaded", () => {

        const chatMessages = document.getElementById("chatMessages");
        const chatForm = document.getElementById("chatForm");
        const chatInput = document.getElementById("chatInput");
        const sendButton = document.getElementById("sendButton");
        const quickActionArea = document.getElementById("quickActionArea");
        const clearChatBtn = document.getElementById("clearChatBtn");
        const characterCount = document.getElementById("characterCount");

        if (!chatMessages || !chatForm || !chatInput || !sendButton) {
            console.error("FinAssist chatbot: Required HTML elements are missing.");
            return;
        }

        const CHAT_API_URL = "/api/chat";
        const customerName =
            sessionStorage.getItem("customerName") || "Customer";

        const customerId =
            sessionStorage.getItem("customerId") ||
            sessionStorage.getItem("customerEmail") ||
            "customer";

        const CHAT_STORAGE_KEY = "finassist_chat_" + customerId;

        let chatHistory = [];
        let isSending = false;
        let typingElement = null;

        /* -----------------------------------------
           CUSTOMER NAME
        ----------------------------------------- */

        document.querySelectorAll("[data-customer-name]").forEach(element => {
            element.textContent = customerName;
        });

        /* -----------------------------------------
           STORAGE
        ----------------------------------------- */

        function saveChatHistory() {
            try {
                localStorage.setItem(
                    CHAT_STORAGE_KEY,
                    JSON.stringify(chatHistory)
                );
            } catch (error) {
                console.error("Unable to save chat history:", error);
            }
        }

        function loadChatHistory() {
            try {
                const saved = localStorage.getItem(CHAT_STORAGE_KEY);
                const parsed = saved ? JSON.parse(saved) : [];

                chatHistory = Array.isArray(parsed)
                    ? parsed.filter(item =>
                        item &&
                        typeof item.text === "string" &&
                        ["user", "bot"].includes(item.sender)
                    )
                    : [];

                if (chatHistory.length > 0) {
                    hideWelcomeScreen();
                    hideQuickActions();

                    chatHistory.forEach(item => {
                        createMessage(item.text, item.sender, false);
                    });
                }
            } catch (error) {
                console.error("Unable to restore chat history:", error);
                chatHistory = [];
            }

            scrollToBottom();
        }

        /* -----------------------------------------
           SCROLL
        ----------------------------------------- */

        function scrollToBottom() {
            requestAnimationFrame(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        }

        /* -----------------------------------------
           MESSAGE CREATION
        ----------------------------------------- */

        function createMessage(text, sender, shouldSave = true) {
            const row = document.createElement("div");

            row.className =
                "message-row " +
                (sender === "user" ? "user-row" : "bot-row");

            if (sender === "bot") {
                const avatar = document.createElement("div");
                avatar.className = "message-avatar";
                avatar.textContent = "F";
                row.appendChild(avatar);
            }

            const content = document.createElement("div");
            content.className = "message-content";

            const name = document.createElement("div");
            name.className = "message-name";
            name.textContent = sender === "user" ? "You" : "FinAssist AI";

            const bubble = document.createElement("div");
            bubble.className = "message-bubble";
            bubble.textContent = String(text);

            content.appendChild(name);
            content.appendChild(bubble);
            row.appendChild(content);
            chatMessages.appendChild(row);

            if (shouldSave) {
                chatHistory.push({
                    sender,
                    text: String(text),
                    time: new Date().toISOString()
                });

                saveChatHistory();
            }

            scrollToBottom();
            return row;
        }

        function addUserMessage(text) {
            return createMessage(text, "user");
        }

        function addBotMessage(text) {
            return createMessage(text, "bot");
        }

        /* -----------------------------------------
           TYPING INDICATOR
        ----------------------------------------- */

        function showTypingIndicator() {
            if (typingElement) return;

            const row = document.createElement("div");
            row.className = "message-row bot-row";

            const avatar = document.createElement("div");
            avatar.className = "message-avatar";
            avatar.textContent = "F";

            const content = document.createElement("div");
            content.className = "message-content";

            const name = document.createElement("div");
            name.className = "message-name";
            name.textContent = "FinAssist AI";

            const typing = document.createElement("div");
            typing.className = "message-bubble typing-indicator";
            typing.setAttribute("aria-label", "FinAssist is typing");

            for (let i = 0; i < 3; i++) {
                const dot = document.createElement("span");
                typing.appendChild(dot);
            }

            content.appendChild(name);
            content.appendChild(typing);

            row.appendChild(avatar);
            row.appendChild(content);

            chatMessages.appendChild(row);
            typingElement = row;

            scrollToBottom();
        }

        function hideTypingIndicator() {
            if (typingElement) {
                typingElement.remove();
                typingElement = null;
            }
        }

        /* -----------------------------------------
           WELCOME AND QUICK ACTIONS
        ----------------------------------------- */

        function hideWelcomeScreen() {
            const welcome = document.getElementById("welcomeScreen");

            if (welcome) {
                welcome.remove();
            }
        }

        function hideQuickActions() {
            if (quickActionArea) {
                quickActionArea.hidden = true;
            }
        }

        function showQuickActions() {
            if (quickActionArea) {
                quickActionArea.hidden = false;
            }
        }

        function showWelcomeScreen() {
            const welcome = document.createElement("div");
            welcome.className = "welcome-screen";
            welcome.id = "welcomeScreen";

            const icon = document.createElement("div");
            icon.className = "welcome-icon";
            icon.textContent = "F";

            const heading = document.createElement("h2");
            heading.append("Hello, ");

            const customer = document.createElement("span");
            customer.textContent = customerName;
            heading.appendChild(customer);
            heading.append("!");

            const paragraph = document.createElement("p");
            paragraph.textContent =
                "I'm your FinAssist AI banking assistant. What would you like to do today?";

            welcome.append(icon, heading, paragraph);
            chatMessages.appendChild(welcome);
        }

        /* -----------------------------------------
           INPUT
        ----------------------------------------- */

        function updateCharacterCount() {
            if (characterCount) {
                characterCount.textContent =
                    `${chatInput.value.length} / 2000`;
            }
        }

        function resizeInput() {
            chatInput.style.height = "auto";
            chatInput.style.height =
                Math.min(chatInput.scrollHeight, 130) + "px";
        }

        function setSendingState(state) {
            isSending = state;

            sendButton.disabled = state;
            chatInput.disabled = state;

            document.querySelectorAll(".quick-action").forEach(button => {
                button.disabled = state;
            });

            sendButton.innerHTML = state
                ? "…"
                : "<span>↑</span>";
        }

        /* -----------------------------------------
           SEND MESSAGE
        ----------------------------------------- */

        async function sendMessage(message) {
            const cleanMessage = String(message || "").trim();

            if (!cleanMessage || isSending) return;

            if (cleanMessage.length > 2000) {
                addBotMessage(
                    "Your message is too long. Please keep it under 2,000 characters."
                );
                return;
            }

            hideWelcomeScreen();
            hideQuickActions();

            addUserMessage(cleanMessage);

            chatInput.value = "";
            updateCharacterCount();
            resizeInput();

            setSendingState(true);
            showTypingIndicator();

            try {
                const response = await fetch(CHAT_API_URL, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        message: cleanMessage
                    })
                });

                let result;

                try {
                    result = await response.json();
                } catch {
                    throw new Error(
                        "The server returned an invalid response."
                    );
                }

                if (!response.ok || result.success === false) {
                    throw new Error(
                        result.message ||
                        result.reply ||
                        "Unable to process your request."
                    );
                }

                const reply =
                    result.reply ||
                    result.response ||
                    result.message;

                if (typeof reply !== "string" || !reply.trim()) {
                    throw new Error(
                        "The server did not provide a response."
                    );
                }

                hideTypingIndicator();
                addBotMessage(reply);

            } catch (error) {
                hideTypingIndicator();

                console.error("FinAssist chatbot error:", error);

                addBotMessage(
                    error.message === "Failed to fetch"
                        ? "Unable to connect to FinAssist. Please check that the Flask server is running."
                        : error.message || "Something went wrong. Please try again."
                );

            } finally {
                setSendingState(false);
                chatInput.focus();
            }
        }

        /* -----------------------------------------
           EVENT HANDLERS
           Use capture phase to prevent other scripts
           from also handling chatbot interactions.
        ----------------------------------------- */

        document.addEventListener("click", event => {
            const button = event.target.closest("[data-question]");

            if (!button) return;
            if (!chatForm.contains(button)) {
                // Only handle suggestions inside this chatbot.
                if (!quickActionArea || !quickActionArea.contains(button)) {
                    return;
                }
            }

            event.preventDefault();
            event.stopImmediatePropagation();

            if (isSending || button.disabled) return;

            sendMessage(button.dataset.question || "");

        }, true);

        document.addEventListener("submit", event => {
            if (event.target !== chatForm) return;

            event.preventDefault();
            event.stopImmediatePropagation();

            sendMessage(chatInput.value);

        }, true);

        document.addEventListener("keydown", event => {
            if (event.target !== chatInput) return;

            if (
                event.key === "Enter" &&
                !event.shiftKey &&
                !event.isComposing
            ) {
                event.preventDefault();
                event.stopImmediatePropagation();

                if (!isSending) {
                    chatForm.requestSubmit();
                }
            }
        }, true);

        /* -----------------------------------------
           INPUT EVENTS
        ----------------------------------------- */

        chatInput.addEventListener("input", () => {
            updateCharacterCount();
            resizeInput();
        });

        /* -----------------------------------------
           CLEAR CONVERSATION
        ----------------------------------------- */

        function resetConversation() {
            if (isSending) return;

            chatHistory = [];

            try {
                localStorage.removeItem(CHAT_STORAGE_KEY);
            } catch (error) {
                console.error("Unable to clear saved conversation:", error);
            }

            hideTypingIndicator();
            chatMessages.replaceChildren();

            // Recreate only the greeting. No feature cards.
            showWelcomeScreen();
            showQuickActions();

            chatInput.value = "";
            updateCharacterCount();
            resizeInput();
            scrollToBottom();
            chatInput.focus();
        }

        if (clearChatBtn) {
            clearChatBtn.addEventListener("click", event => {
                event.preventDefault();
                event.stopImmediatePropagation();

                resetConversation();
            });
        }

        /* -----------------------------------------
           INITIALIZE
        ----------------------------------------- */

        loadChatHistory();
        updateCharacterCount();
        resizeInput();

        console.log("FinAssist chatbot initialized.");

    });
}
