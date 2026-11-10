const messageBox = document.getElementById("messageBox");
const customerDetails = document.getElementById("customerDetails");
const customerSearch = document.getElementById("customerSearch");
const customerInfoPanel = document.getElementById("customerInfoPanel");
const searchButton = document.getElementById("searchCustomerBtn");

let currentCustomer = null;

// ==========================================
// 2. COMMON FUNCTIONS
// ==========================================

function showMessage(message, type = "error") {
    if (!messageBox) {
        console.error(message);
        return;
    }

    messageBox.textContent = message;
    messageBox.hidden = false;
    messageBox.className = `message ${type}`;
}

function hideMessage() {
    if (messageBox) {
        messageBox.hidden = true;
    }
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function formatMoney(value) {
    return Number(value || 0).toLocaleString("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    });
}

function formatDate(value) {
    if (!value) return "-";

    const date = new Date(String(value).replace(" ", "T"));

    if (Number.isNaN(date.getTime())) {
        return escapeHTML(value);
    }

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

function emptyMessage(message) {
    return `<p class="empty-state">${escapeHTML(message)}</p>`;
}

function createTable(headers, rows) {
    if (!rows.length) {
        return emptyMessage("No records found.");
    }

    return `
        <div class="info-content">
            <table>
                <thead>
                    <tr>
                        ${headers.map(header =>
                            `<th>${escapeHTML(header)}</th>`
                        ).join("")}
                    </tr>
                </thead>

                <tbody>
                    ${rows.join("")}
                </tbody>
            </table>
        </div>
    `;
}


function statusHTML(status) {
    const normalized = String(status || "Unknown")
        .trim()
        .toLowerCase();

    let statusClass = "status-unknown";

    switch (normalized) {
        case "pending":
            statusClass = "status-pending";
            break;

        case "in progress":
            statusClass = "status-progress";
            break;

        case "documents pending":
        case "documents required":
            statusClass = "status-documents";
            break;

        case "approved":
        case "resolved":
            statusClass = "status-approved";
            break;

        case "rejected":
            statusClass = "status-rejected";
            break;
    }

    return `
        <span class="record-status ${statusClass}">
            ${escapeHTML(status || "Unknown")}
        </span>
    `;
}


// ==========================================
// 3. CUSTOMER SEARCH
// ==========================================

async function searchCustomer() {

    if (!customerSearch || !searchButton) {
        showMessage("Customer search elements are missing from employee.html.");
        return;
    }

    const customerId = customerSearch.value.trim().toUpperCase();

    if (!customerId) {
        showMessage("Please enter a Customer ID.");
        return;
    }

    searchButton.disabled = true;
    searchButton.textContent = "Searching...";

    hideMessage();

    if (customerInfoPanel) {
        customerInfoPanel.hidden = true;
    }

    if (customerDetails) {
        customerDetails.hidden = true;
    }

    currentCustomer = null;

    try {
        const response = await fetch(
            `/api/employee/customer/${encodeURIComponent(customerId)}`,
            {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error("Invalid response received from the server.");
        }

        console.log("Employee customer API response:", data);

        if (!response.ok || !data.success) {
            showMessage(data.message || "Customer not found.");
            return;
        }

        if (!data.customer) {
            showMessage("Customer information is missing.");
            return;
        }

        // Store the complete response.
        // This includes all customer-related records.

        currentCustomer = {
            ...data,
            accounts: Array.isArray(data.accounts) ? data.accounts : [],
            cards: Array.isArray(data.cards) ? data.cards : [],
            transactions: Array.isArray(data.transactions) ? data.transactions : [],
            loans: Array.isArray(data.loans) ? data.loans : [],
            complaints: Array.isArray(data.complaints) ? data.complaints : []
        };

        console.log("Customer:", currentCustomer.customer);
        console.log("Accounts:", currentCustomer.accounts);
        console.log("Cards:", currentCustomer.cards);
        console.log("Transactions:", currentCustomer.transactions);
        console.log("Loans:", currentCustomer.loans);
        console.log("Complaints:", currentCustomer.complaints);

        const nameElement = document.getElementById("customerName");
        const idElement = document.getElementById("customerId");

        if (nameElement) {
            nameElement.textContent =
                currentCustomer.customer.full_name || "-";
        }

        if (idElement) {
            idElement.textContent =
                "Customer ID: " +
                (currentCustomer.customer.customer_id || customerId);
        }

        if (customerDetails) {
            customerDetails.hidden = false;
        }

        if (customerInfoPanel) {
            customerInfoPanel.hidden = true;
        }

        document.querySelectorAll(".customer-option").forEach(button => {
            button.classList.remove("selected");
        });

        if (customerDetails) {
            customerDetails.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }

        
    } catch (error) {
        console.error("Customer search error:", error);
        showMessage(error.message || "Unable to connect to the server.");

    } finally {
        searchButton.disabled = false;
        searchButton.textContent = "Search";
    }
}

// Register search events.

if (searchButton && customerSearch) {

    searchButton.addEventListener("click", searchCustomer);

    customerSearch.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            searchCustomer();
        }
    });

} else {
    console.error("Customer search input or button is missing.");
}

// ==========================================
// 4. CUSTOMER SECTION TITLES
// ==========================================

const sectionTitles = {
    accounts: "Customer Accounts",
    balance: "Customer Balance",
    transactions: "Customer Transactions",
    cards: "Customer Cards",
    loans: "Customer Loans",
    complaints: "Customer Complaints"
};

// ==========================================
// 5. CUSTOMER SECTION BUTTONS
// ==========================================

document.querySelectorAll(".customer-option").forEach(button => {

    button.addEventListener("click", () => {

        if (!currentCustomer) {
            showMessage("Please search for a customer first.");
            return;
        }

        document.querySelectorAll(".customer-option").forEach(item => {
            item.classList.remove("selected");
        });

        button.classList.add("selected");

        const section = button.dataset.section;

        const titleElement = document.getElementById("infoPanelTitle");

        if (titleElement) {
            titleElement.textContent =
                sectionTitles[section] || "Customer Information";
        }

        if (customerInfoPanel) {
            customerInfoPanel.hidden = false;
        }

        renderCustomerSection(section);

        if (customerInfoPanel) {
            customerInfoPanel.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });
        }
    });

});

// ==========================================
// 6. CUSTOMER SECTION RENDERING
// ==========================================

function renderCustomerSection(section) {

    const content = document.getElementById("customerInfoContent");

    if (!content) {
        console.error("customerInfoContent element is missing.");
        return;
    }

    if (!currentCustomer) {
        content.innerHTML = emptyMessage("Please search for a customer first.");
        return;
    }

    switch (section) {

        case "accounts":
            renderAccounts(content);
            break;

        case "balance":
            renderBalance(content);
            break;

        case "transactions":
            renderTransactions(content);
            break;

        case "cards":
            renderCards(content);
            break;

        case "loans":
            renderLoans(content);
            break;

        case "complaints":
            renderComplaints(content);
            break;

        default:
            content.innerHTML = emptyMessage("Section not available.");
    }
}

// ==========================================
// 7. CUSTOMER ACCOUNTS
// ==========================================

function renderAccounts(content) {

    const accounts = currentCustomer.accounts || [];

    if (!accounts.length) {
        content.innerHTML = emptyMessage("No accounts found for this customer.");
        return;
    }

    const totalBalance = accounts.reduce(
        (sum, account) => sum + Number(account.balance || 0),
        0
    );

    const rows = accounts.map(account => `
        <tr>
            <td>${escapeHTML(account.account_number)}</td>
            <td>${escapeHTML(account.account_type)}</td>
            <td>${escapeHTML(account.ifsc_code || "-")}</td>
            <td><strong>${formatMoney(account.balance)}</strong></td>
            <td>${statusHTML(account.status)}</td>
        </tr>
    `);

    content.innerHTML = `
        <div class="account-summary">
            <div class="account-total">
                <span>Total Account Balance</span>
                <h2>${formatMoney(totalBalance)}</h2>
                <small>${accounts.length} linked account(s)</small>
            </div>
        </div>

        ${createTable([
            "Account Number",
            "Account Type",
            "IFSC Code",
            "Balance",
            "Status"
        ], rows)}
    `;
}

// ==========================================
// 8. CUSTOMER BALANCE
// ==========================================

function renderBalance(content) {

    const accounts = currentCustomer.accounts || [];

    if (!accounts.length) {
        content.innerHTML = emptyMessage("No accounts available.");
        return;
    }

    const totalBalance = accounts.reduce(
        (sum, account) => sum + Number(account.balance || 0),
        0
    );

    content.innerHTML = `
        <div class="account-summary">
            <div class="account-total">
                <span>Combined Customer Balance</span>
                <h2>${formatMoney(totalBalance)}</h2>
                <small>Across ${accounts.length} account(s)</small>
            </div>
        </div>

        <h3>Individual Account Balances</h3>

        ${accounts.map(account => `
            <div class="balance-row">
                <div>
                    <strong>${escapeHTML(account.account_type)}</strong>
                    <p>Account: ${escapeHTML(account.account_number)}</p>
                    <small>${escapeHTML(account.status)}</small>
                </div>

                <strong>${formatMoney(account.balance)}</strong>
            </div>
        `).join("")}
    `;
}

// ==========================================
// 9. CUSTOMER TRANSACTIONS
// ==========================================

function renderTransactions(content) {

    const transactions = currentCustomer.transactions || [];

    if (!transactions.length) {
        content.innerHTML = emptyMessage("No transactions found.");
        return;
    }

    const rows = transactions.map(transaction => {

        const isCredit =
            String(transaction.transaction_type).toLowerCase() === "credit";

        return `
            <tr>
                <td>${formatDate(transaction.transaction_date)}</td>

                <td>${escapeHTML(transaction.description || "-")}</td>

                <td class="${isCredit ? "credit" : "debit"}">
                    ${escapeHTML(transaction.transaction_type)}
                </td>

                <td class="${isCredit ? "credit" : "debit"}">
                    ${isCredit ? "+" : "-"}${formatMoney(transaction.amount)}
                </td>

                <td>${escapeHTML(transaction.account_number)}</td>

                <td>${statusHTML(transaction.status)}</td>
            </tr>
        `;
    });

    content.innerHTML = createTable([
        "Date",
        "Description",
        "Type",
        "Amount",
        "Account Number",
        "Status"
    ], rows);
}

// ==========================================
// 10. CUSTOMER CARDS
// ==========================================

function renderCards(content) {

    const cards = currentCustomer.cards || [];

    if (!cards.length) {
        content.innerHTML = emptyMessage("No cards found for this customer.");
        return;
    }

    const rows = cards.map(card => `
        <tr>
            <td>${escapeHTML(card.card_type)}</td>
            <td>•••• ${escapeHTML(card.last_four_digits || "----")}</td>
            <td>${escapeHTML(card.account_number || "-")}</td>
            <td>${escapeHTML(card.expiry_date || "-")}</td>
            <td>${statusHTML(card.status)}</td>
        </tr>
    `);

    content.innerHTML = createTable([
        "Card Type",
        "Card Number",
        "Linked Account",
        "Expiry Date",
        "Status"
    ], rows);
}

// ==========================================
// 11. CUSTOMER LOANS
// ==========================================

function renderLoans(content) {

    const loans = currentCustomer.loans || [];

    if (!loans.length) {
        content.innerHTML = emptyMessage(
            "No loan applications found for this customer."
        );
        return;
    }

    const rows = loans.map(loan => `
        <tr>
            <td>${escapeHTML(loan.id)}</td>
            <td>${escapeHTML(loan.loan_type)}</td>
            <td>${formatMoney(loan.amount)}</td>
            <td>${escapeHTML(loan.tenure_months)} months</td>
            <td>${formatDate(loan.applied_at)}</td>
            <td>${statusHTML(loan.status)}</td>
        </tr>
    `);

    content.innerHTML = createTable([
        "Loan ID",
        "Loan Type",
        "Amount",
        "Tenure",
        "Applied Date",
        "Status"
    ], rows);
}

// ==========================================
// 12. CUSTOMER COMPLAINTS
// ==========================================

function renderComplaints(content) {

    const complaints = currentCustomer.complaints || [];

    if (!complaints.length) {
        content.innerHTML = emptyMessage(
            "No complaints found for this customer."
        );
        return;
    }

    const rows = complaints.map(complaint => `
        <tr>
            <td>${escapeHTML(complaint.id)}</td>
            <td>${escapeHTML(complaint.subject)}</td>
            <td>${escapeHTML(complaint.message)}</td>
            <td>${formatDate(complaint.created_at)}</td>
            <td>${statusHTML(complaint.status)}</td>
        </tr>
    `);

    content.innerHTML = createTable([
        "Complaint ID",
        "Subject",
        "Message",
        "Date",
        "Status"
    ], rows);
}

// ==========================================
// 13. CLOSE CUSTOMER INFORMATION PANEL
// ==========================================

const closeInfoPanel = document.getElementById("closeInfoPanel");

if (closeInfoPanel) {

    closeInfoPanel.addEventListener("click", () => {

        if (customerInfoPanel) {
            customerInfoPanel.hidden = true;
        }

        document.querySelectorAll(".customer-option").forEach(button => {
            button.classList.remove("selected");
        });

    });

}

// ==========================================
// 14. EMPLOYEE LOGOUT
// ==========================================

const logoutButton = document.getElementById("logoutBtn");

if (logoutButton) {

    logoutButton.addEventListener("click", async () => {

        logoutButton.disabled = true;

        try {

            const response = await fetch("/api/logout", {
                method: "POST",
                credentials: "same-origin"
            });

            if (!response.ok) {
                showMessage("Unable to log out. Please try again.");
                logoutButton.disabled = false;
                return;
            }

            window.location.href = "login.html";

        } catch (error) {

            console.error("Logout error:", error);
            showMessage("Unable to connect to the server.");
            logoutButton.disabled = false;

        }

    });

}

console.log("FinAssist Employee Portal JavaScript loaded successfully.");

// ======================================================
// FINASSIST EMPLOYEE - COMPLAINT & LOAN MANAGEMENT
// ======================================================


// ======================================================
// 1. SHARED DATA
// ======================================================

let allComplaints = [];
let allLoans = [];


// ======================================================
// 2. ALL CUSTOMER COMPLAINTS
// ======================================================

async function loadAllComplaints() {

    const tableBody = document.getElementById("complaintsTableBody");

    if (!tableBody) return;

    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="empty-state">Loading complaints...</td>
        </tr>
    `;

    try {

        const response = await fetch("/api/employee/complaints", {
            method: "GET",
            credentials: "same-origin",
            headers: { "Accept": "application/json" }
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Unable to load complaints.");
        }

        allComplaints = Array.isArray(data.complaints)
            ? data.complaints
            : [];

        renderAllComplaints();
        loadDashboardStats();

    } catch (error) {

        console.error("Complaint loading error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    Unable to load complaints.
                </td>
            </tr>
        `;
    }
}


function renderAllComplaints() {

    const tableBody = document.getElementById("complaintsTableBody");

    if (!tableBody) return;

    const searchValue =
        document.getElementById("complaintSearch")?.value
            .trim().toLowerCase() || "";

    const statusFilter =
        document.getElementById("complaintStatusFilter")?.value || "";

    const filtered = allComplaints.filter(complaint => {

        const matchesSearch =
            String(complaint.id || "").toLowerCase().includes(searchValue) ||
            String(complaint.customer_id || "").toLowerCase().includes(searchValue) ||
            String(complaint.full_name || "").toLowerCase().includes(searchValue);

        const matchesStatus =
            !statusFilter ||
            String(complaint.status || "").toLowerCase() === statusFilter.toLowerCase();

        return matchesSearch && matchesStatus;
    });

    if (!filtered.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    No matching complaints found.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = filtered.map(complaint => {

        const id = Number(complaint.id);

        const statuses = [
            "Pending",
            "In Progress",
            "Resolved",
            "Rejected"
        ];

        return `
            <tr>
                <td>${escapeHTML(complaint.id)}</td>
                <td>${escapeHTML(complaint.customer_id)}</td>
                <td>${escapeHTML(complaint.full_name || "-")}</td>
                <td>${escapeHTML(complaint.subject)}</td>
                <td>${formatDate(complaint.created_at)}</td>
                <td>${statusHTML(complaint.status)}</td>

                <td>
                    <select id="allComplaintStatus-${id}">
                        ${statuses.map(status => `
                            <option value="${status}"
                                ${String(complaint.status).toLowerCase() === status.toLowerCase() ? "selected" : ""}>
                                ${status}
                            </option>
                        `).join("")}
                    </select>

                    <button type="button"
                        class="update-all-complaint"
                        data-id="${id}">
                        Update
                    </button>
                </td>
            </tr>
        `;

    }).join("");

    tableBody.querySelectorAll(".update-all-complaint").forEach(button => {
        button.addEventListener("click", () => {
            updateAllComplaintStatus(Number(button.dataset.id), button);
        });
    });
}


// ======================================================
// 3. UPDATE COMPLAINT STATUS
// ======================================================

async function updateAllComplaintStatus(id, button) {

    const select = document.getElementById(`allComplaintStatus-${id}`);

    if (!select) return;

    button.disabled = true;
    button.textContent = "Updating...";

    try {

        const response = await fetch(`/api/employee/complaints/${id}`, {
            method: "PATCH",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                status: select.value
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Complaint update failed.");
        }

        const complaint = allComplaints.find(
            item => Number(item.id) === id
        );

        if (complaint) {
            complaint.status = data.status || select.value;
        }

        renderAllComplaints();

        

    } catch (error) {

        console.error("Complaint update error:", error);
        showMessage(error.message || "Unable to update complaint.");

        button.disabled = false;
        button.textContent = "Update";
    }
}


// ======================================================
// 4. ALL LOAN APPLICATIONS
// ======================================================

async function loadAllLoans() {

    const tableBody = document.getElementById("loansTableBody");

    if (!tableBody) return;

    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="empty-state">Loading loan applications...</td>
        </tr>
    `;

    try {

        const response = await fetch("/api/employee/loans", {
            method: "GET",
            credentials: "same-origin",
            headers: { "Accept": "application/json" }
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Unable to load loan applications.");
        }

        allLoans = Array.isArray(data.loans)
            ? data.loans
            : [];

        renderAllLoans();

    } catch (error) {

        console.error("Loan loading error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    Unable to load loan applications.
                </td>
            </tr>
        `;
    }
}


function renderAllLoans() {

    const tableBody = document.getElementById("loansTableBody");

    if (!tableBody) return;

    const searchValue =
        document.getElementById("loanSearch")?.value
            .trim().toLowerCase() || "";

    const statusFilter =
        document.getElementById("loanStatusFilter")?.value || "";

    const filtered = allLoans.filter(loan => {

        const matchesSearch =
            String(loan.id || "").toLowerCase().includes(searchValue) ||
            String(loan.customer_id || "").toLowerCase().includes(searchValue) ||
            String(loan.full_name || "").toLowerCase().includes(searchValue);

        const matchesStatus =
            !statusFilter ||
            String(loan.status || "").toLowerCase() === statusFilter.toLowerCase();

        return matchesSearch && matchesStatus;
    });

    if (!filtered.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    No matching loan applications found.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = filtered.map(loan => {

        const id = Number(loan.id);

        const statuses = [
            "Pending",
            "Documents Pending",
            "In Progress",
            "Approved",
            "Rejected"
        ];

        return `
            <tr>
                <td>${escapeHTML(loan.id)}</td>
                <td>${escapeHTML(loan.customer_id)}</td>
                <td>${escapeHTML(loan.full_name || "-")}</td>
                <td>${escapeHTML(loan.loan_type)}</td>
                <td>${formatDate(loan.applied_at)}</td>
                <td>${statusHTML(loan.status)}</td>

                <td>
                    <select id="allLoanStatus-${id}">
                        ${statuses.map(status => `
                            <option value="${status}"
                                ${String(loan.status).toLowerCase() === status.toLowerCase() ? "selected" : ""}>
                                ${status}
                            </option>
                        `).join("")}
                    </select>

                    <button type="button"
                        class="update-all-loan"
                        data-id="${id}">
                        Update
                    </button>
                </td>
            </tr>
        `;

    }).join("");

    tableBody.querySelectorAll(".update-all-loan").forEach(button => {
        button.addEventListener("click", () => {
            updateAllLoanStatus(Number(button.dataset.id), button);
        });
    });
}


// ======================================================
// 5. UPDATE LOAN STATUS
// ======================================================

async function updateAllLoanStatus(id, button) {

    const select = document.getElementById(`allLoanStatus-${id}`);

    if (!select) return;

    button.disabled = true;
    button.textContent = "Updating...";

    try {

        const response = await fetch(`/api/employee/loans/${id}`, {
            method: "PATCH",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                status: select.value
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Loan update failed.");
        }

        const loan = allLoans.find(item => Number(item.id) === id);

        if (loan) {
            loan.status = data.status || select.value;
        }

        renderAllLoans();

        

    } catch (error) {

        console.error("Loan update error:", error);
        showMessage(error.message || "Unable to update loan.");

        button.disabled = false;
        button.textContent = "Update";
    }
}


// ======================================================
// 6. SEARCH AND FILTER EVENTS
// ======================================================

document.getElementById("complaintSearch")
    ?.addEventListener("input", renderAllComplaints);

document.getElementById("complaintStatusFilter")
    ?.addEventListener("change", renderAllComplaints);

document.getElementById("loanSearch")
    ?.addEventListener("input", renderAllLoans);

document.getElementById("loanStatusFilter")
    ?.addEventListener("change", renderAllLoans);

// LOAD DASHBOARD SUMMARY
async function loadDashboardStats() {
    try {
        const response = await fetch("/api/employee/dashboard", {
            credentials: "same-origin"
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "Unable to load dashboard stats.");
        }

        // Complaint counts only
        const setCount = (id, value) => {
            const element = document.getElementById(id);

            if (element) {
                element.textContent = value ?? 0;
            }
        };

        setCount("totalCount", data.complaints.total);
        setCount("pendingCount", data.complaints.pending);
        setCount("progressCount", data.complaints.in_progress);
        setCount("resolvedCount", data.complaints.resolved);

    } catch (error) {
        console.error("Dashboard stats error:", error);
    }
}
// ======================================================
// 7. INITIAL LOAD
// ======================================================

if (document.getElementById("complaintsTableBody")) {
    loadAllComplaints();
    loadDashboardStats();
}

if (document.getElementById("loansTableBody")) {
    loadAllLoans();
}


// ======================================================
// END OF COMPLAINT & LOAN MANAGEMENT
// ======================================================
