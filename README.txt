
GETTING STARTED

Prerequisites:
- Python 3.8+
- MongoDB

Installation:

1. Clone the repository:
   git clone <repository-url>
   cd FastApiFinal

2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Create a .env file in the project root with the following variables:
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=api_management

Running the API:

Start the FastAPI server:
uvicorn app.main:app --reload

The API will be available at http://localhost:8000



USAGE GUIDE

Authentication:

Register a User:
POST /register
{
  "username": "username",
  "password": "password"
}

Get an Authentication Token:
POST /token
Form data:
- username: your_username
- password: your_password

Note include the JWT token in the header:
Authorization: Bearer jwt_token

Admin Operations:

Permission Management:

Create a Permission:
POST /admin/permissions
{
  "name": "storage_access",
  "endpoint": "/service/storage",
  "description": "Access to storage API"
}

List Permissions:
GET /admin/permissions

Update a Permission:
PUT /admin/permissions/{name}
{
  "name": "storage_access",
  "endpoint": "/service/storage",
  "description": "Updated description"
}

Delete a Permission:
DELETE /admin/permissions/{name}

Subscription Plan Management:

Create a Plan:
POST /admin/plans
{
  "name": "basic_plan",
  "description": "Basic API access",
  "permissions": ["storage_access", "compute_access"],
  "call_limit": 1000
}

List Plans:
GET /admin/plans

Update a Plan:
PUT /admin/plans/{name}
{
  "name": "basic_plan",
  "description": "Updated description",
  "permissions": ["storage_access", "compute_access", "analytics_access"],
  "call_limit": 2000
}

Delete a Plan:
DELETE /admin/plans/{name}

User Management:

Create a User:
POST /admin/users/

List Users:
GET /admin/users/

Get User Details:
GET /admin/users/{username}

Delete a User:
DELETE /admin/users/{username}

Assign a Plan to a User:
POST /admin/users/{username}/assign-plan/{plan_name}

View User Usage:
GET /admin/users/{username}/usage

User Operations:

Subscription Management:

Subscribe to a Plan:
POST /subscription/subscribe/{plan_name}?duration_days=30

Get Subscription Details (includes usage statistics):
GET /subscription/details

View Usage Statistics:
GET /subscription/usage

API Services:

The following services are available (access depends on subscription plan):

GET /service/storage
GET /service/compute
GET /service/ai
GET /service/monitoring
GET /service/security
GET /service/networking
GET /service/analytics
GET /service/messaging

Example Workflow:

1. Admin creates permissions for different API endpoints
2. Admin creates subscription plans with different permission sets
3. Users register and subscribe to plans
4. Users access API services based on their subscription permissions
5. The system tracks usage and enforces rate limits
6. Users can view their usage statistics
7. Admins can monitor and manage all users, plans, and permissions
