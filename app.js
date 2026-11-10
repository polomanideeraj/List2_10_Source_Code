
"use strict";

document.addEventListener("DOMContentLoaded", () => {

    // ---------------- LOGOUT ----------------
    document.querySelectorAll("#logoutBtn, [data-logout]").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();

            try {
                await fetch("/api/logout", {
                    method: "POST",
                    credentials: "same-origin"
                });
            } catch (error) {
                console.error("Logout request failed:", error);
            }
const customerId =
    sessionStorage.getItem("customerId") ||
    sessionStorage.getItem("customerEmail") ||
    "customer";

localStorage.removeItem("finassist_chat_" + customerId);
            sessionStorage.clear();
            window.location.replace("/login.html");
        });
    });


    // ---------------- SERVICES DROPDOWN ----------------
    const servicesToggle = document.getElementById("servicesToggle");
    const servicesSubmenu = document.getElementById("servicesSubmenu");
    const servicesArrow = document.getElementById("servicesArrow");

    if (servicesToggle && servicesSubmenu) {
        servicesToggle.addEventListener("click", () => {
            const isOpening = servicesSubmenu.hidden;

            servicesSubmenu.hidden = !isOpening;
            servicesToggle.setAttribute("aria-expanded", String(isOpening));

            if (servicesArrow) {
                servicesArrow.textContent = isOpening ? "⌃" : "⌄";
            }
        });
    }


    // ---------------- CUSTOMER PROFILE ----------------
    const savedCustomerName =
        sessionStorage.getItem("customerName") || "Customer";

    document.querySelectorAll("[data-customer-name]").forEach((element) => {
        element.textContent = savedCustomerName;
    });

    document.querySelectorAll("[data-avatar]").forEach((element) => {
        element.textContent = savedCustomerName.charAt(0).toUpperCase();
    });


    // ---------------- LOGIN ----------------
    // Only attach login handling to the actual login form.
    // Never use document.querySelector("form") as a fallback.
    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const role =
                document.getElementById("role")?.value ||
                document.getElementById("userRole")?.value ||
                document.querySelector('[name="role"]:checked')?.value ||
                "customer";

            const userId =
                document.getElementById("userId")?.value?.trim() ||
                document.getElementById("customerId")?.value?.trim() ||
                document.getElementById("employeeId")?.value?.trim() ||
                document.querySelector('[name="user_id"]')?.value?.trim() ||
                "";

            const email =
                document.getElementById("email")?.value?.trim() ||
                document.getElementById("customerEmail")?.value?.trim() ||
                document.querySelector('[name="email"]')?.value?.trim() ||
                "";

            const password =
                document.getElementById("password")?.value ||
                document.querySelector('[name="password"]')?.value ||
                "";

            let message = document.getElementById("loginMessage");

            if (!message) {
                message = document.createElement("p");
                message.id = "loginMessage";
                message.setAttribute("role", "alert");
                loginForm.appendChild(message);
            }

            if (!userId || !password) {
                message.textContent = "Enter your ID and password.";
                return;
            }

            const submitButton = loginForm.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (submitButton) submitButton.disabled = true;

            message.textContent = "Signing in...";

            try {
                const response = await fetch("/api/login", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        role: role.toLowerCase(),
                        user_id: userId,
                        email: email,
                        password: password
                    })
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(result.message || "Login failed.");
                }

                sessionStorage.clear();

                if (result.role === "customer") {
                    sessionStorage.setItem("userRole", "customer");
                    sessionStorage.setItem(
                        "customerName",
                        result.customer?.name || "Customer"
                    );
                    sessionStorage.setItem(
                        "customerEmail",
                        result.customer?.email || email
                    );

                    window.location.replace("/dashboard.html");

                } else if (result.role === "employee") {
                    sessionStorage.setItem("userRole", "employee");
                    sessionStorage.setItem("employeeId", userId);

                    window.location.replace("/employee.html");

                } else {
                    throw new Error("Unknown account type.");
                }

            } catch (error) {
                message.textContent =
                    error.message || "Unable to connect to the server.";

            } finally {
                if (submitButton) submitButton.disabled = false;
            }
        });
    }


    // ---------------- COMPLAINTS ----------------
    const complaintForm = document.getElementById("complaintForm");
    const complaintTableBody =
        document.getElementById("complaintTableBody");
    const complaintEmpty = document.getElementById("complaintEmpty");
    const complaintFeedback =
        document.getElementById("complaintFeedback");

    async function loadComplaints() {
        if (!complaintTableBody) return;

        try {
            const response = await fetch("/api/my-complaints", {
                method: "GET",
                credentials: "same-origin"
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(
                    result.message || "Could not load complaints."
                );
            }

            const complaints = result.complaints || [];

            complaintTableBody.replaceChildren();

            if (complaintEmpty) {
                complaintEmpty.hidden = complaints.length > 0;
            }

            complaints.forEach((complaint) => {
                const row = document.createElement("tr");

                const cells = [
                    "CP" + complaint.id,
                    complaint.subject,
                    extractCategory(complaint.message),
                    formatDate(complaint.created_at),
                    complaint.status
                ];

                cells.forEach((value) => {
                    const cell = document.createElement("td");
                    cell.textContent = value || "—";
                    row.appendChild(cell);
                });

                complaintTableBody.appendChild(row);
            });

        } catch (error) {
            console.error("Loading complaints failed:", error);

            if (complaintEmpty) {
                complaintEmpty.hidden = true;
            }

            if (complaintFeedback) {
                complaintFeedback.textContent =
                    error.message ||
                    "Could not load complaints. Please try again.";
            }
        }
    }

    function extractCategory(message) {
        const match = String(message || "").match(/^Category:\s*(.+)$/m);
        return match ? match[1].trim() : "General";
    }

    function formatDate(value) {
        if (!value) return "—";

        const date = new Date(value.replace(" ", "T"));

        if (Number.isNaN(date.getTime())) {
            return value;
        }

        return date.toLocaleDateString();
    }

    if (complaintForm) {
        loadComplaints();

        complaintForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const category =
                document.getElementById("complaintCategory")?.value.trim() ||
                "";

            const priority =
                document.getElementById("complaintPriority")?.value || "Normal";

            const subject =
                document.getElementById("complaintSubject")?.value.trim() ||
                "";

            const description =
                document.getElementById("complaintDescription")?.value.trim() ||
                "";

            if (!category || !subject || !description) {
                if (complaintFeedback) {
                    complaintFeedback.textContent =
                        "Please fill in all required fields.";
                }
                return;
            }

            const submitButton = complaintForm.querySelector(
                'button[type="submit"]'
            );

            if (submitButton) submitButton.disabled = true;

            if (complaintFeedback) {
                complaintFeedback.textContent = "Submitting complaint...";
            }

            try {
                const response = await fetch("/api/submit-complaint", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        subject: subject,
                        message:
                            "Category: " + category +
                            "\nPriority: " + priority +
                            "\n\nDescription: " + description
                    })
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.message || "Complaint submission failed."
                    );
                }

                complaintForm.reset();

                if (complaintFeedback) {
                    complaintFeedback.textContent =
                        "Complaint submitted successfully. Reference: CP" +
                        result.complaint_id;
                }

                await loadComplaints();

            } catch (error) {
                if (complaintFeedback) {
                    complaintFeedback.textContent =
                        error.message ||
                        "Unable to submit complaint. Please try again.";
                }

            } finally {
                if (submitButton) submitButton.disabled = false;
            }
        });
    }


    // ---------------- CHATBOT ----------------
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");

    function addChatMessage(text, sender) {
        if (!chatMessages) return;

        const message = document.createElement("div");
        message.className = "message " + sender;
        message.textContent = text;

        chatMessages.appendChild(message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function getChatReply(question) {
        const text = question.toLowerCase();

        if (text.includes("block") && text.includes("card")) {
            return "To block your card, use your bank's official app or call its official customer-support number. Never share your PIN or OTP.";
        }

        if (text.includes("transfer") || text.includes("pending")) {
            return "Check the transfer status and transaction history in your bank's official app. If money was debited and the transfer remains pending, contact your bank.";
        }

        if (
            text.includes("password") ||
            text.includes("reset") ||
            text.includes("login")
        ) {
            return "Use the password-reset option on your bank's official website or app. Never share your password or OTP.";
        }

        if (text.includes("complaint")) {
            return "Open the Complaints section, fill in the form, and select Submit complaint. Your complaint should then appear under Your complaints.";
        }

        if (
            text.includes("human") ||
            text.includes("person") ||
            text.includes("agent")
        ) {
            return "To connect with our customer-support team ";
        }

        if (text.includes("loan") || text.includes("emi")) {
            return "Check the Loans section for application options. Review the interest rate, fees, eligibility, and repayment period before applying.";
        }

        if (text.includes("balance")) {
            return "Check your balance using your bank's official app, internet banking, ATM, or account statement.";
        }

        if (text.includes("hello") || text.includes("hi")) {
            return "Hello! I can help with general questions about cards, transfers, passwords, loans, and complaints. What do you need help with?";
        }

        return "I can help with general questions about cards, transfers, passwords, loans, and complaints. For account-specific information, contact your bank through its official support channels.";
    }

    function sendQuestion(question) {
        const cleanQuestion = String(question || "").trim();

        if (!cleanQuestion || !chatMessages) return;

        addChatMessage(cleanQuestion, "user");
        addChatMessage(getChatReply(cleanQuestion), "bot");
    }

    if (chatForm && chatInput) {
        chatForm.addEventListener("submit", (event) => {
            event.preventDefault();

            const question = chatInput.value.trim();

            if (!question) return;

            sendQuestion(question);

            chatInput.value = "";
            chatInput.focus();
        });

        document.querySelectorAll("[data-question]").forEach((button) => {
            button.addEventListener("click", () => {
                sendQuestion(button.dataset.question || "");
            });
        });
    }

});
