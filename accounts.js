document.addEventListener("DOMContentLoaded", () => {

    // ==================================
    // ELEMENTS
    // ==================================

    const accountsMainView = document.getElementById("accountsMainView");
    const addAccountPanel = document.getElementById("addAccountPanel");

    const showAddAccountBtn = document.getElementById("showAddAccountBtn");
    const closeAddAccountBtn = document.getElementById("closeAddAccountBtn");
    const cancelAddAccountBtn = document.getElementById("cancelAddAccountBtn");

    const addAccountForm = document.getElementById("addAccountForm");
    const createAccountBtn = document.getElementById("createAccountBtn");

    const newAccountType = document.getElementById("newAccountType");
    const initialDeposit = document.getElementById("initialDeposit");

    const accountsList = document.getElementById("accountsList");
    const accountCount = document.getElementById("accountCount");

    const totalAccountBalance = document.getElementById("totalAccountBalance");
    const balanceAccountSelect = document.getElementById("balanceAccountSelect");

    const accountsMessage = document.getElementById("accountsMessage");
    const createAccountMessage = document.getElementById("createAccountMessage");

    const customerName = document.getElementById("customerName");


    let accounts = [];


    // ==================================
    // HELPER FUNCTIONS
    // ==================================

    function formatCurrency(amount) {
        return Number(amount || 0).toLocaleString("en-IN", {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2
        });
    }


    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => {
            const entities = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            };

            return entities[character];
        });
    }


    function showMessage(element, message, type = "info") {
        element.textContent = message;
        element.className = `fa-message ${type}`;
        element.hidden = false;
    }


    function hideMessage(element) {
        element.hidden = true;
        element.textContent = "";
    }


    /*
       Safely read JSON responses.

       If Flask sends HTML instead of JSON, this gives
       a useful error instead of "Unexpected token '<'".
    */

    async function readResponse(response) {
        const contentType = response.headers.get("content-type") || "";
        const responseText = await response.text();

        if (!contentType.includes("application/json")) {

            const preview = responseText
                .replace(/<[^>]*>/g, " ")
                .replace(/\s+/g, " ")
                .trim()
                .slice(0, 180);

            throw new Error(
                `Server returned HTML instead of JSON (HTTP ${response.status}). ` +
                `Check the Flask route and terminal. ${preview}`
            );
        }

        try {
            return JSON.parse(responseText);
        } catch {
            throw new Error("The server returned an invalid JSON response.");
        }
    }


    // ==================================
    // SCREEN NAVIGATION
    // ==================================

    function showAccountsScreen() {
        addAccountPanel.hidden = true;
        accountsMainView.hidden = false;

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }


    function showAddAccountScreen() {
        accountsMainView.hidden = true;
        addAccountPanel.hidden = false;

        hideMessage(createAccountMessage);

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }


    showAddAccountBtn.addEventListener("click", () => {
        addAccountForm.reset();
        showAddAccountScreen();
    });


    closeAddAccountBtn.addEventListener("click", showAccountsScreen);

    cancelAddAccountBtn.addEventListener("click", showAccountsScreen);


    // ==================================
    // LOAD CUSTOMER SESSION
    // ==================================

    async function loadCustomerSession() {

        try {
            const response = await fetch("/api/session", {
                credentials: "same-origin"
            });

            const data = await readResponse(response);

            if (!response.ok || data.logged_in === false) {
                window.location.href = "login.html";
                return false;
            }

            const name =
                data.customer_name ||
                data.name ||
                data.customer?.name;

            if (name) {
                customerName.textContent = name;
                document.querySelector(".fa-profile-avatar").textContent =
                    name.charAt(0).toUpperCase();
            }

            return true;

        } catch (error) {
            console.error("Session error:", error);

            // Continue to the account API, which can also
            // report whether the customer is logged in.
            return true;
        }
    }


    // ==================================
    // LOAD ACCOUNTS
    // ==================================

    async function loadAccounts() {

        hideMessage(accountsMessage);

        try {

            const response = await fetch("/api/my-accounts", {
                method: "GET",
                credentials: "same-origin"
            });

            const data = await readResponse(response);

            if (!response.ok || data.success === false) {
                throw new Error(data.message || "Unable to load accounts.");
            }

            accounts = Array.isArray(data.accounts)
                ? data.accounts
                : [];

            renderAccounts();
            updateAccountSelector();

            return true;

        } catch (error) {

            console.error("Account loading error:", error);

            accountsList.innerHTML = `
                <div class="fa-empty-state">
                    <h3>Unable to load accounts</h3>
                    <p>${escapeHTML(error.message)}</p>
                </div>
            `;

            accountCount.textContent = "0";
            totalAccountBalance.textContent = formatCurrency(0);

            showMessage(
                accountsMessage,
                error.message,
                "error"
            );

            return false;
        }
    }


    // ==================================
    // DISPLAY ACCOUNT CARDS
    // ==================================

    function renderAccounts() {

        accountCount.textContent = accounts.length;

        if (accounts.length === 0) {

            accountsList.innerHTML = `
                <div class="fa-empty-state">
                    <h3>No accounts found</h3>
                    <p>You haven't created any bank accounts yet.</p>
                    <p>Click Add Account to create your first account.</p>
                </div>
            `;

            return;
        }


        accountsList.innerHTML = accounts.map(account => {

            const accountNumber = escapeHTML(account.account_number);
            const accountType = escapeHTML(account.account_type);
            const ifscCode = escapeHTML(account.ifsc_code || "Not available");

            const balance = formatCurrency(account.balance);

            const status = String(account.status || "Active").toLowerCase();
            const isActive = status === "active";

            return `

                <div class="fa-account-card">

                    <div class="fa-account-top">

                        <div class="fa-account-type">

                            <div class="fa-account-icon">
                                ▣
                            </div>

                            <span>${accountType} Account</span>

                        </div>

                        <span class="fa-status ${isActive ? "active" : "inactive"}">
                            ${isActive ? "Active" : "Inactive"}
                        </span>

                    </div>


                    <div class="fa-account-balance-label">
                        Available Balance
                    </div>

                    <div class="fa-account-balance">
                        ${balance}
                    </div>


                    <div class="fa-account-details">

                        <div class="fa-detail-row">
                            <span>Account Number</span>
                            <strong>${accountNumber}</strong>
                        </div>

                        <div class="fa-detail-row">
                            <span>IFSC Code</span>
                            <strong>${ifscCode}</strong>
                        </div>

                        <div class="fa-detail-row">
                            <span>Account Type</span>
                            <strong>${accountType}</strong>
                        </div>

                    </div>


                    <div class="fa-account-actions">

                        <button
                            type="button"
                            class="fa-status-toggle ${isActive ? "deactivate" : ""}"
                            data-account-number="${accountNumber}"
                            data-new-status="${isActive ? "Inactive" : "Active"}"
                        >
                            ${isActive ? "Deactivate Account" : "Activate Account"}
                        </button>

                    </div>

                </div>

            `;

        }).join("");
    }


    // ==================================
    // ACCOUNT BALANCE SELECTOR
    // ==================================

    function updateAccountSelector() {

        balanceAccountSelect.innerHTML = `
            <option value="">Select an account</option>
        `;

        accounts.forEach(account => {

            const option = document.createElement("option");

            option.value = account.account_number;

            option.textContent =
                `${account.account_type} - ${account.account_number}`;

            balanceAccountSelect.appendChild(option);

        });


        if (accounts.length > 0) {

            const activeAccount = accounts.find(
                account => String(account.status).toLowerCase() === "active"
            );

            const selectedAccount = activeAccount || accounts[0];

            balanceAccountSelect.value = selectedAccount.account_number;

            updateSelectedBalance();

        } else {

            totalAccountBalance.textContent = formatCurrency(0);

        }
    }


    function updateSelectedBalance() {

        const selectedNumber = balanceAccountSelect.value;

        const selectedAccount = accounts.find(
            account => account.account_number === selectedNumber
        );

        if (selectedAccount) {

            totalAccountBalance.textContent =
                formatCurrency(selectedAccount.balance);

        } else {

            totalAccountBalance.textContent = formatCurrency(0);

        }
    }


    balanceAccountSelect.addEventListener("change", updateSelectedBalance);


    // ==================================
    // CREATE NEW ACCOUNT
    // ==================================

    addAccountForm.addEventListener("submit", async event => {

        event.preventDefault();

        hideMessage(createAccountMessage);

        const accountType = newAccountType.value;

        const deposit = Number(initialDeposit.value);


        if (!["Savings", "Current"].includes(accountType)) {

            showMessage(
                createAccountMessage,
                "Please select a valid account type.",
                "error"
            );

            return;
        }


        if (!Number.isFinite(deposit) || deposit < 0 || deposit > 100000000) {

            showMessage(
                createAccountMessage,
                "Please enter a valid initial deposit.",
                "error"
            );

            return;
        }


        createAccountBtn.disabled = true;
        createAccountBtn.textContent = "Creating Account...";


        try {

            const response = await fetch("/api/add-account", {

                method: "POST",

                credentials: "same-origin",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    account_type: accountType,
                    initial_deposit: deposit
                })

            });


            const data = await readResponse(response);


            if (!response.ok || data.success === false) {
                throw new Error(data.message || "Account creation failed.");
            }


            showMessage(
                createAccountMessage,
                data.message || "Account created successfully!",
                "success"
            );


            /*
               Refresh the account list.
               If refresh succeeds, return to the accounts screen.
            */

            const refreshed = await loadAccounts();

            if (!refreshed) {
                throw new Error(
                    "Account was created, but the account list could not be refreshed. " +
                    "Return to Accounts and refresh the page."
                );
            }


            addAccountForm.reset();

            showAccountsScreen();

            showMessage(
                accountsMessage,
                data.message || "Your new account has been created successfully.",
                "success"
            );


        } catch (error) {

            console.error("Create account error:", error);

            showMessage(
                createAccountMessage,
                error.message,
                "error"
            );

        } finally {

            createAccountBtn.disabled = false;
            createAccountBtn.textContent = "Create Account";

        }

    });


    // ==================================
    // ACTIVATE / DEACTIVATE ACCOUNT
    // ==================================

    accountsList.addEventListener("click", async event => {

        const button = event.target.closest(".fa-status-toggle");

        if (!button) {
            return;
        }


        const accountNumber = button.dataset.accountNumber;
        const newStatus = button.dataset.newStatus;

        const action = newStatus === "Active"
            ? "activate"
            : "deactivate";


        const confirmed = confirm(
            `Are you sure you want to ${action} this account?`
        );

        if (!confirmed) {
            return;
        }


        button.disabled = true;


        try {

            const response = await fetch(
                `/api/account-status/${encodeURIComponent(accountNumber)}`,
                {

                    method: "PATCH",

                    credentials: "same-origin",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        status: newStatus
                    })

                }
            );


            const data = await readResponse(response);


            if (!response.ok || data.success === false) {
                throw new Error(data.message || "Unable to update account status.");
            }


            await loadAccounts();

            showMessage(
                accountsMessage,
                data.message || `Account ${action}d successfully.`,
                "success"
            );


        } catch (error) {

            console.error("Account status error:", error);

            showMessage(
                accountsMessage,
                error.message,
                "error"
            );

            button.disabled = false;

        }

    });


    // ==================================
    // INITIALIZE PAGE
    // ==================================

    async function initializeAccountsPage() {

        const loggedIn = await loadCustomerSession();

        if (!loggedIn) {
            return;
        }

        await loadAccounts();

    }


    initializeAccountsPage();

});