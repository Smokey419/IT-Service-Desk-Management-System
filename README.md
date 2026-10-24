
# IT Service Desk Management System

**CS4500 – CIT Seminar Capstone Project**  
**William Paterson University | Fall 2026**  
**Developer:** Brian Hernandez Delgado

## Project Overview

The IT Service Desk Management System is a web-based application developed to help small organizations manage IT support tickets and company equipment.

The system provides employees with a centralized platform to submit and track IT support requests. Administrators can review tickets, assign technicians, update priorities and statuses, document resolutions, and manage IT assets.

This project was developed as an individual capstone project using Python Flask and SQLite.

## Features

### Employee Features
- Secure account login and logout
- Submit IT support tickets
- Select ticket categories and priorities
- View submitted tickets and their current statuses
- Review administrator assignments and resolution notes
- Search and filter personal support tickets

### Administrator Features
- Administrator dashboard
- View and manage all support tickets
- Assign tickets to administrators
- Update ticket statuses and priorities
- Add resolution notes
- Search and filter support tickets
- Create and update IT asset records
- Track equipment assignments and availability

## Technologies Used

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| Authentication | Flask-Login, Werkzeug |
| Database ORM | Flask-SQLAlchemy |
| Testing | pytest |
| Development Environment | Visual Studio Code |
| Version Control | Git and GitHub |

## System Architecture

The application uses a web-based client-server architecture.

1. Employees and administrators access the application through a web browser.
2. Flask processes requests and manages authentication.
3. Role-based authorization restricts administrative functions.
4. Flask-SQLAlchemy communicates with the SQLite database.
5. The database stores user accounts, support tickets, and IT assets.
6. HTML templates and CSS display the appropriate information to users.

## Installation and Setup

This application is designed to run locally.

### 1. Clone the repository

```bash
git clone https://github.com/Smokey419/IT-Service-Desk-Management-System.git
cd IT-Service-Desk-Management-System
```

### 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the application

Set a unique Flask secret key using the `SECRET_KEY` environment variable.

The application uses a local SQLite database, which is not included in the repository.

The database tables are created when the application starts. Administrator and employee accounts must be provisioned separately before logging in.

### 5. Start the application

```bash
python app.py
```

Open a browser and navigate to:

http://127.0.0.1:5000

## Testing

The application was tested using pytest and manual functional testing.

**Automated test results: 12 tests passed.**

Testing included authentication, role-based access restrictions, ticket management, and other core application functions.

## Known Limitations

- The application runs locally and is not deployed to a public hosting service.
- The SQLite database is intended for a small-scale prototype.
- User accounts must be created before accessing the system.
- Email notifications and external IT service integrations are not implemented.
- The current configuration is intended for local development, not production deployment.

## Future Improvements

Potential future enhancements include:

- Email notifications for ticket updates
- Additional reporting and analytics
- Integration with Microsoft 365
- Cloud hosting and production deployment
- Enhanced asset tracking and reporting

## Project Status

**Completed – Fall 2026 Capstone MVP**

The core application is functional, and automated testing has been completed.

## Author

Brian Hernandez Delgado  
Bachelor of Science in Information Technology – Cybersecurity Concentration  
William Paterson University
