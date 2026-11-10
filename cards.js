
/* =====================================
   COMMON ELEMENTS
===================================== */

const cardsGrid = document.getElementById("cardsGrid");
const messageBox = document.getElementById("messageBox");
const addCardPanel = document.getElementById("addCardPanel");
const addCardForm = document.getElementById("addCardForm");
const submitCardBtn = document.getElementById("submitCardBtn");

const addCardBtn = document.getElementById("addCardBtn");
const cancelCardBtn = document.getElementById("cancelCardBtn");
const refreshCardsBtn = document.getElementById("refreshCardsBtn");

let customerFullName = "";


/* =====================================
   SAFE HTML
===================================== */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}


/* =====================================
   API RESPONSE HANDLER
===================================== */

async function readJSON(response) {
    const text = await response.text();

    try {
        return JSON.parse(text);
    } catch (error) {
        if (text.trim().startsWith("<")) {
            throw new Error(
                "Server returned HTML instead of JSON. Check your Flask route."
            );
        }
        throw new Error("Invalid server response.");
    }
}


/* =====================================
   MESSAGE
===================================== */

function showMessage(message, type = "error") {
    messageBox.textContent = message;
    messageBox.className = "message " + type;
}

function hideMessage() {
    messageBox.textContent = "";
    messageBox.className = "message";
}


/* =====================================
   SIDEBAR SERVICES MENU
===================================== */

const servicesToggle = document.getElementById("servicesToggle");
const servicesSubmenu = document.getElementById("servicesSubmenu");
const servicesArrow = document.getElementById("servicesArrow");

if (servicesToggle && servicesSubmenu && servicesArrow) {
    servicesToggle.addEventListener("click", () => {
        const isOpen = servicesSubmenu.style.display !== "none";

        servicesSubmenu.style.display = isOpen ? "none" : "block";
        servicesArrow.textContent = isOpen ? "›" : "⌄";

        servicesToggle.setAttribute(
            "aria-expanded",
            String(!isOpen)
        );
    });
}


/* =====================================
   LOGOUT
===================================== */

const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {
    logoutBtn.addEventListener("click", async function(event) {
        event.preventDefault();

        try {
            await fetch("/api/logout", {
                method: "POST",
                credentials: "same-origin"
            });
        } catch (error) {
            console.error("Logout error:", error);
        }

        window.location.href = "login.html";
    });
}


/* =====================================
   LOAD CUSTOMER PROFILE
===================================== */

async function loadCustomerDetails() {
    try {
        const response = await fetch("/api/my-profile", {
            credentials: "same-origin"
        });

        const data = await readJSON(response);

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to load customer profile."
            );
        }

        const customer = data.customer || {};

        customerFullName = customer.full_name || "";

        if (!customerFullName.trim()) {
            throw new Error(
                "Customer name was not returned by the profile API."
            );
        }

        const cardholderName =
            document.getElementById("cardholderName");

        const customerName =
            document.getElementById("customerName");

        const userAvatar =
            document.getElementById("userAvatar");

        if (cardholderName) {
            cardholderName.value = customerFullName;
        }

        if (customerName) {
            customerName.textContent = customerFullName;
        }

        if (userAvatar) {
            userAvatar.textContent =
                customerFullName.trim().charAt(0).toUpperCase();
        }

        await loadCustomerAccounts();

    } catch (error) {
        showMessage(error.message);
    }
}


/* =====================================
   LOAD CUSTOMER ACCOUNTS
===================================== */

async function loadCustomerAccounts() {
    const accountSelect =
        document.getElementById("linkedAccount");

    if (!accountSelect) return;

    try {
        const response = await fetch("/api/my-accounts", {
            credentials: "same-origin"
        });

        const data = await readJSON(response);

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to load accounts."
            );
        }

        const accounts = data.accounts || [];

        accountSelect.innerHTML =
            '<option value="">Select an account</option>';

        const activeAccounts = accounts.filter(account =>
            String(account.status || "Active").toLowerCase() === "active"
        );

        if (activeAccounts.length === 0) {
            accountSelect.innerHTML =
                '<option value="">No active accounts available</option>';
            return;
        }

        activeAccounts.forEach(account => {
            const option = document.createElement("option");

            option.value = account.account_number;

            option.textContent =
                account.account_number + " - " + account.account_type;

            accountSelect.appendChild(option);
        });

    } catch (error) {
        accountSelect.innerHTML =
            '<option value="">Unable to load accounts</option>';

        showMessage(error.message);
    }
}


/* =====================================
   ADD CARD FORM SHOW / HIDE
===================================== */

function openAddCardForm() {
    if (!addCardPanel) {
        console.error("Add Card panel was not found.");
        return;
    }

    addCardPanel.classList.add("show");
    hideMessage();

    const cardNumberInput =
        document.getElementById("cardNumber");

    if (cardNumberInput) {
        cardNumberInput.focus();
    }
}

function closeAddCardForm() {
    if (!addCardPanel) return;

    addCardPanel.classList.remove("show");

    if (addCardForm) {
        addCardForm.reset();
    }

    const cardholderName =
        document.getElementById("cardholderName");

    if (cardholderName) {
        cardholderName.value = customerFullName;
    }

    hideMessage();
}

if (addCardBtn) {
    addCardBtn.addEventListener("click", function(event) {
        event.preventDefault();
        openAddCardForm();
    });
} else {
    console.error("Add New Card button not found: check its HTML ID.");
}

if (cancelCardBtn) {
    cancelCardBtn.addEventListener("click", function(event) {
        event.preventDefault();
        closeAddCardForm();
    });
}

if (refreshCardsBtn) {
    refreshCardsBtn.addEventListener("click", loadCards);
}


/* =====================================
   CARD NUMBER FORMATTING
===================================== */

const cardNumberInput = document.getElementById("cardNumber");

if (cardNumberInput) {
    cardNumberInput.addEventListener("input", function() {
        let digits = this.value
            .replace(/\D/g, "")
            .slice(0, 16);

        this.value = digits.replace(/(\d{4})(?=\d)/g, "$1 ");
    });
}


/* =====================================
   CVV VALIDATION
===================================== */

const cvvInput = document.getElementById("cvv");

if (cvvInput) {
    cvvInput.addEventListener("input", function() {
        this.value = this.value
            .replace(/\D/g, "")
            .slice(0, 3);
    });
}


/* =====================================
   EXPIRY INPUTS
===================================== */

const expiryMonthInput =
    document.getElementById("expiryMonth");

const expiryYearInput =
    document.getElementById("expiryYear");

if (expiryMonthInput) {
    expiryMonthInput.addEventListener("input", function() {
        this.value = this.value
            .replace(/\D/g, "")
            .slice(0, 2);
    });
}

if (expiryYearInput) {
    expiryYearInput.addEventListener("input", function() {
        this.value = this.value
            .replace(/\D/g, "")
            .slice(0, 4);
    });
}


/* =====================================
   LOAD CARDS
===================================== */

async function loadCards() {
    if (!cardsGrid) return;

    hideMessage();

    cardsGrid.innerHTML =
        '<div class="loading">Loading your cards...</div>';

    try {
        const response = await fetch("/api/my-cards", {
            credentials: "same-origin"
        });

        const data = await readJSON(response);

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to load cards."
            );
        }

        const cards = Array.isArray(data.cards)
            ? data.cards
            : [];

        updateSummary(cards);
        displayCards(cards);

    } catch (error) {
        cardsGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <h3>Unable to load cards</h3>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;

        showMessage(error.message);
    }
}


/* =====================================
   UPDATE SUMMARY
===================================== */

function updateSummary(cards) {
    const active = cards.filter(card =>
        String(card.status).toLowerCase() === "active"
    ).length;

    const blocked = cards.filter(card =>
        String(card.status).toLowerCase() === "blocked"
    ).length;

    document.getElementById("totalCards").textContent =
        cards.length;

    document.getElementById("activeCards").textContent =
        active;

    document.getElementById("blockedCards").textContent =
        blocked;
}


/* =====================================
   DISPLAY CARDS
===================================== */

function displayCards(cards) {
    if (!cards.length) {
        cardsGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💳</div>
                <h3>No Cards Found</h3>
                <p>You currently have no linked banking cards.</p>
                <p style="margin-top:10px;">
                    Click "Add New Card" to add your cards.
                </p>
            </div>
        `;
        return;
    }

    cardsGrid.innerHTML = cards.map(card => {
        const type = String(card.card_type || "Debit");
        const isCredit = type.toLowerCase().includes("credit");

        const status = String(card.status || "Active");
        const isActive = status.toLowerCase() === "active";
        const cardId = Number(card.id);

        const fullNumber = String(card.card_number || "")
            .replace(/\D/g, "")
            .slice(0, 16);

        const formattedNumber = /^\d{16}$/.test(fullNumber)
            ? fullNumber.replace(/(\d{4})(?=\d)/g, "$1 ")
            : "Full number unavailable";

        const expiryParts =
            String(card.expiry_date || "").split("-");

        const expiry = expiryParts.length === 2
            ? `${expiryParts[1]}/${expiryParts[0]}`
            : (card.expiry_date || "N/A");

        return `
            <div class="card-item">

                <article class="bank-card ${isCredit ? "credit-card" : "debit-card"}">

    <div class="card-top">
        <div class="bank-name">FINASSIST BANK</div>

        <div class="card-type-label">
            ${escapeHTML(type.toUpperCase())}
        </div>
    </div>

    <div class="card-chip"></div>

    <div class="card-number">
        ${escapeHTML(formattedNumber)}
    </div>

    <div class="card-bottom">

        <div class="cardholder-section">
            <div class="cardholder-label">
                CARDHOLDER NAME
            </div>

            <div class="cardholder-name">
                ${escapeHTML(customerFullName)}
            </div>
        </div>

        <div class="expiry-section">
            <div class="card-label">VALID THRU</div>

            <div class="card-value">
                ${escapeHTML(expiry)}
            </div>
        </div>

    </div>

</article>

                <div class="card-management">

                    <span class="status-text ${isActive ? "active" : "blocked"}">
                        Status: ${escapeHTML(status)}
                    </span>

                    <button
                        type="button"
                        class="card-action-btn ${isActive ? "block-card-btn" : "activate-card-btn"}"
                        onclick="changeCardStatus(
                            ${cardId},
                            '${isActive ? "Blocked" : "Active"}'
                        )">

                        ${isActive ? "Block Card" : "Activate Card"}

                    </button>

                </div>

            </div>
        `;
    }).join("");
}


/* =====================================
   BLOCK / ACTIVATE CARD
===================================== */

async function changeCardStatus(cardId, newStatus) {
    const action = newStatus === "Blocked"
        ? "block"
        : "activate";

    if (!Number.isInteger(cardId) || cardId <= 0) {
        showMessage("Invalid card ID. Please refresh the page.");
        return;
    }

    if (!confirm(`Are you sure you want to ${action} this card?`)) {
        return;
    }

    try {
        const response = await fetch(
            `/api/my-cards/${cardId}/status`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    status: newStatus
                })
            }
        );

        const data = await readJSON(response);

        if (!response.ok || !data.success) {
            throw new Error(
                data.message || "Unable to update card status."
            );
        }

        showMessage(
            `Card ${action}ed successfully!`,
            "success"
        );

        await loadCards();

    } catch (error) {
        showMessage(error.message);
    }
}


/* =====================================
   SUBMIT NEW CARD
===================================== */

if (addCardForm) {
    addCardForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        hideMessage();

        const cardNumber = document.getElementById("cardNumber")
            .value.replace(/\D/g, "");

        const cardType =
            document.getElementById("cardType").value;

        const expiryMonth =
            document.getElementById("expiryMonth").value.trim();

        const expiryYear =
            document.getElementById("expiryYear").value.trim();

        const cvv =
            document.getElementById("cvv").value;

        const accountNumber =
            document.getElementById("linkedAccount").value;

        if (!/^\d{16}$/.test(cardNumber)) {
            showMessage("Card number must contain exactly 16 digits.");
            return;
        }

        if (!cardType) {
            showMessage("Please select a card type.");
            return;
        }

        if (!/^\d{3}$/.test(cvv)) {
            showMessage("CVV must contain exactly 3 digits.");
            return;
        }

        if (!/^(0[1-9]|1[0-2])$/.test(expiryMonth)) {
            showMessage("Expiry month must be between 01 and 12.");
            return;
        }

        if (!/^\d{4}$/.test(expiryYear)) {
            showMessage("Expiry year must contain 4 digits.");
            return;
        }

        const month = Number(expiryMonth);
        const year = Number(expiryYear);
        const now = new Date();

        if (
            year < now.getFullYear() ||
            (
                year === now.getFullYear() &&
                month < now.getMonth() + 1
            )
        ) {
            showMessage("Please enter a future expiry date.");
            return;
        }

        const expiryDate =
            `${year}-${String(month).padStart(2, "0")}`;

        if (!accountNumber) {
            showMessage("Please select an active linked account.");
            return;
        }

        if (!customerFullName) {
            showMessage("Customer profile is not loaded. Refresh the page.");
            return;
        }

        submitCardBtn.disabled = true;
        submitCardBtn.textContent = "Submitting...";

        try {
            const response = await fetch("/api/my-cards", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "same-origin",
                body: JSON.stringify({
                    card_number: cardNumber,
                    card_type: cardType,
                    expiry_date: expiryDate,
                    cvv: cvv,
                    account_number: accountNumber
                })
            });

            const data = await readJSON(response);

            if (!response.ok || !data.success) {
                throw new Error(
                    data.message || "Unable to add card."
                );
            }

            addCardForm.reset();

            document.getElementById("cardholderName").value =
                customerFullName;

            addCardPanel.classList.remove("show");

            showMessage(
                "Your card has been added successfully!",
                "success"
            );

            await loadCards();

        } catch (error) {
            showMessage(error.message);
        } finally {
            submitCardBtn.disabled = false;
            submitCardBtn.textContent = "Submit Card";
        }
    });
}


/* =====================================
   INITIAL PAGE LOAD
===================================== */

async function initializeCardsPage() {
    if (document.getElementById("userAvatar")) {
        document.getElementById("userAvatar").textContent = "D";
    }

    await loadCustomerDetails();
    await loadCards();
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        initializeCardsPage
    );
} else {
    initializeCardsPage();
}
