# AI Chatbot for Banking Services

## 1. Project Overview

AI Chatbot for Banking Services is a web-based application developed to bring commonly used banking features together in one place. It provides separate portals for customers and employees, along with a chatbot that helps users access supported banking information and services.

The chatbot uses predefined keywords and rules to identify customer requests. Depending on the request, it can provide a response, retrieve relevant information from the application's database, or ask the customer for confirmation before processing a selected action.

This project was developed as an academic prototype to demonstrate the use of web technologies, backend programming and database integration in a banking application.

## 2. Main Features

### Customer Portal
- Customer registration and login.
- View account details and balance information.
- Access transaction history.
- View and manage available card services.
- Access loan-related information and EMI estimates.
- Submit complaints and check their status.
- Interact with the banking chatbot.

### Employee Portal
- Employee login.
- Search for customer records.
- View available customer and account information.
- Review and manage complaints.
- View and manage loan applications.

### Chatbot
- Accepts banking-related questions and requests.
- Identifies supported requests using predefined keywords and patterns.
- Retrieves relevant information from the application's database.
- Requests confirmation for selected operations.
- Provides a suitable response when a request is not recognised.

## 3. Test Login Credentials

The following credentials are provided for demonstrating the customer and employee portals.

### Customer Test Login

| Field | Test Credential |
|---|---|
| Name | Dheeraj |
| Email | dheeraj@gmail.com |
| MPIN | 0296 |

### Employee Login

| Field | Test Credential |
|---|---|
| Employee ID | NOB12 |
| Password | nobita@123 |

**Note:** These credentials are intended for project demonstration only. They should be changed or disabled before using the application in any real environment. Do not publish working credentials in a public GitHub repository.

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| HTML | Structure of web pages |
| CSS | Styling and page layout |
| JavaScript | Browser-side interactions |
| Python | Backend programming |
| Flask | Web framework and application routes |
| SQLite | Database management |
| Visual Studio Code | Development environment |

## 5. Project Structure

The project contains frontend files, backend code and database-related files.

The main components are:

- **app.py** – Flask application and backend logic.
- **HTML files** – Login pages, dashboards and banking service pages.
- **CSS files** – Styling and layout of the application.
- **JavaScript files** – Frontend interactions and communication with backend routes.
- **SQLite database** – Stores customer, account, transaction and other prototype records.

The exact file and folder names may vary depending on the final project directory.

## 6. Requirements

Before running the application, make sure the following are available:

- Python 3 installed on the computer.
- Flask installed.
- Visual Studio Code or another code editor.
- A modern web browser.
- The project source files and SQLite database, if required by the application.

## 7. How to Run the Project

**Step 1: Open the project**

Extract the project folder, open Visual Studio Code and select the project directory.

**Step 2: Open the terminal**

Open the terminal in Visual Studio Code.

**Step 3: Install Flask**

Run the following command in the terminal:

```bash
pip install flask
```

**Step 4: Start the application**

Run the Flask application using:

```bash
python app.py
```

**Step 5: Open the application**

After the Flask server starts, open the local address displayed in the terminal in your web browser. The usual Flask development address is:

```text
http://127.0.0.1:5000/
```

**Step 6: Log in**

Use the customer test credentials to access the customer portal or the employee credentials to access the employee dashboard.

## 8. Database Information

The application uses SQLite to store its prototype data. The database supports information related to customers, accounts, transactions, cards, loans and complaints.

The Flask backend communicates with the database to retrieve or update records when users perform supported operations.

The application uses its own local database and is not connected to a real bank's database.

## 9. Important Notes and Limitations

- This project is developed for academic demonstration purposes.
- The banking records are prototype data and do not represent actual bank accounts.
- The application does not process real-money transfers or payments.
- The chatbot uses predefined rules and does not use a trained large language model or RAG pipeline.
- The chatbot may not recognise every possible way of asking a question.
- The application is not intended for storing real banking credentials or handling actual financial activities.
- Additional security testing and improvements would be required before considering any production use.

## 10. Future Improvements

The project can be extended in several ways:

- Improve query understanding using NLP or a suitable trained AI model.
- Connect to authorised banking APIs, subject to approval and security requirements.
- Strengthen authentication and data protection.
- Improve mobile compatibility.
- Introduce additional banking services and employee reporting features.

## 11. Project Information

**Project Title:** AI Chatbot for Banking Services

**Student:** Dheeraj Yadav

**Unique Project ID:** List2_10

**Institution:** The ICFAI Foundation for Higher Education, Hyderabad

**Faculty Guide:** Dr. Santosh Kumar Sahoo

**Project Guide:** Dr. D. Srinivasa Rao