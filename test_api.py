"""Tests for the ticketing system API."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import TicketPriority, TicketStatus


@pytest.fixture
def client():
    """Create a test client with an in-memory database."""
    app = create_app(database_path=":memory:", seed=False)
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket(client):
    """Test creating a new ticket."""
    ticket_data = {
        "title": "Test ticket",
        "description": "This is a test ticket",
        "requester": "Test User",
        "priority": "high"
    }
    response = client.post("/api/tickets", json=ticket_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == ticket_data["title"]
    assert data["description"] == ticket_data["description"]
    assert data["requester"] == ticket_data["requester"]
    assert data["priority"] == ticket_data["priority"]
    assert data["status"] == "open"
    assert "id" in data


def test_list_tickets(client):
    """Test listing tickets."""
    # Create a ticket first
    ticket_data = {
        "title": "Test ticket",
        "description": "This is a test ticket",
        "requester": "Test User",
        "priority": "medium"
    }
    client.post("/api/tickets", json=ticket_data)
    
    # List tickets
    response = client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == ticket_data["title"]


def test_get_ticket(client):
    """Test getting a specific ticket."""
    # Create a ticket
    ticket_data = {
        "title": "Test ticket",
        "description": "This is a test ticket",
        "requester": "Test User",
        "priority": "low"
    }
    create_response = client.post("/api/tickets", json=ticket_data)
    ticket_id = create_response.json()["id"]
    
    # Get the ticket
    response = client.get(f"/api/tickets/{ticket_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["title"] == ticket_data["title"]


def test_update_ticket(client):
    """Test updating a ticket."""
    # Create a ticket
    ticket_data = {
        "title": "Test ticket",
        "description": "This is a test ticket",
        "requester": "Test User",
        "priority": "medium"
    }
    create_response = client.post("/api/tickets", json=ticket_data)
    ticket_id = create_response.json()["id"]
    
    # Update the ticket
    update_data = {"status": "in_progress"}
    response = client.patch(f"/api/tickets/{ticket_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["title"] == ticket_data["title"]  # Unchanged


def test_delete_ticket(client):
    """Test deleting a ticket."""
    # Create a ticket
    ticket_data = {
        "title": "Test ticket to delete",
        "description": "This ticket will be deleted",
        "requester": "Test User",
        "priority": "low"
    }
    create_response = client.post("/api/tickets", json=ticket_data)
    ticket_id = create_response.json()["id"]
    
    # Delete the ticket
    response = client.delete(f"/api/tickets/{ticket_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/tickets/{ticket_id}")
    assert get_response.status_code == 404


def test_filter_by_status(client):
    """Test filtering tickets by status."""
    # Create tickets with different statuses
    client.post("/api/tickets", json={
        "title": "Open ticket",
        "description": "An open ticket",
        "requester": "User1",
        "priority": "medium"
    })
    
    create_response = client.post("/api/tickets", json={
        "title": "In progress ticket",
        "description": "A ticket in progress",
        "requester": "User2",
        "priority": "high"
    })
    ticket_id = create_response.json()["id"]
    client.patch(f"/api/tickets/{ticket_id}", json={"status": "in_progress"})
    
    # Filter by status
    response = client.get("/api/tickets?status=in_progress")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "in_progress"


def test_filter_by_priority(client):
    """Test filtering tickets by priority."""
    # Create tickets with different priorities
    client.post("/api/tickets", json={
        "title": "Low priority",
        "description": "Low priority ticket",
        "requester": "User1",
        "priority": "low"
    })
    
    client.post("/api/tickets", json={
        "title": "High priority",
        "description": "High priority ticket",
        "requester": "User2",
        "priority": "high"
    })
    
    # Filter by priority
    response = client.get("/api/tickets?priority=high")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["priority"] == "high"


def test_search_tickets(client):
    """Test searching tickets."""
    # Create tickets
    client.post("/api/tickets", json={
        "title": "Login bug",
        "description": "Users cannot login",
        "requester": "John Doe",
        "priority": "urgent"
    })
    
    client.post("/api/tickets", json={
        "title": "Display issue",
        "description": "Screen not rendering",
        "requester": "Jane Smith",
        "priority": "medium"
    })
    
    # Search by title
    response = client.get("/api/tickets?search=login")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "login" in data[0]["title"].lower()


def test_validation_errors(client):
    """Test that validation errors are properly handled."""
    # Empty title should fail
    invalid_data = {
        "title": "",
        "description": "Test",
        "requester": "User",
        "priority": "medium"
    }
    response = client.post("/api/tickets", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_nonexistent_ticket(client):
    """Test getting a ticket that doesn't exist."""
    response = client.get("/api/tickets/99999")
    assert response.status_code == 404
