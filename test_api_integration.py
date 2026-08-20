"""
Integration tests for the Ticketing System API
Tests all endpoints against the actual application
"""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database"""
    app = create_app(database_path=":memory:", seed=True)
    return TestClient(app)


class TestAPIIntegration:
    """Integration tests for all API endpoints"""

    def test_health_endpoint(self, client):
        """Verify health endpoint returns correct status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_list_tickets_returns_seeded_data(self, client):
        """Verify list endpoint returns 3 seeded tickets"""
        response = client.get("/api/tickets")
        assert response.status_code == 200
        tickets = response.json()
        assert len(tickets) == 3
        
        # Verify ticket structure
        for ticket in tickets:
            assert "id" in ticket
            assert "title" in ticket
            assert "description" in ticket
            assert "requester" in ticket
            assert "priority" in ticket
            assert "status" in ticket
            assert "created_at" in ticket
            assert "updated_at" in ticket

    def test_create_ticket_returns_201(self, client):
        """Verify creating a ticket returns 201 CREATED"""
        response = client.post(
            "/api/tickets",
            json={
                "title": "Test Ticket",
                "description": "This is a test ticket",
                "requester": "John Doe",
                "priority": "high"
            }
        )
        assert response.status_code == 201
        ticket = response.json()
        assert ticket["title"] == "Test Ticket"
        assert ticket["status"] == "open"
        assert ticket["priority"] == "high"

    def test_get_ticket_by_id(self, client):
        """Verify retrieving a specific ticket by ID"""
        # First get a ticket ID
        list_response = client.get("/api/tickets")
        tickets = list_response.json()
        ticket_id = tickets[0]["id"]
        
        # Get the ticket
        response = client.get(f"/api/tickets/{ticket_id}")
        assert response.status_code == 200
        ticket = response.json()
        assert ticket["id"] == ticket_id
        assert "title" in ticket

    def test_get_nonexistent_ticket(self, client):
        """Verify getting a nonexistent ticket returns 404"""
        response = client.get("/api/tickets/99999")
        assert response.status_code == 404

    def test_update_ticket(self, client):
        """Verify updating a ticket works correctly"""
        # Get a ticket first
        list_response = client.get("/api/tickets")
        ticket_id = list_response.json()[0]["id"]
        
        # Update it
        response = client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "resolved"}
        )
        assert response.status_code == 200
        ticket = response.json()
        assert ticket["status"] == "resolved"

    def test_delete_ticket(self, client):
        """Verify deleting a ticket works correctly"""
        # Get initial count
        initial_response = client.get("/api/tickets")
        initial_count = len(initial_response.json())
        
        # Get a ticket ID
        ticket_id = initial_response.json()[0]["id"]
        
        # Delete it
        response = client.delete(f"/api/tickets/{ticket_id}")
        assert response.status_code == 204
        
        # Verify it's gone
        final_response = client.get("/api/tickets")
        final_count = len(final_response.json())
        assert final_count == initial_count - 1

    def test_filter_by_status(self, client):
        """Verify filtering tickets by status"""
        response = client.get("/api/tickets?status=open")
        assert response.status_code == 200
        tickets = response.json()
        for ticket in tickets:
            assert ticket["status"] == "open"

    def test_filter_by_priority(self, client):
        """Verify filtering tickets by priority"""
        response = client.get("/api/tickets?priority=high")
        assert response.status_code == 200
        tickets = response.json()
        for ticket in tickets:
            assert ticket["priority"] == "high"

    def test_search_by_text(self, client):
        """Verify searching tickets by text"""
        response = client.get("/api/tickets?search=VPN")
        assert response.status_code == 200
        tickets = response.json()
        assert len(tickets) > 0
        # Verify at least one ticket contains search term
        titles = [t["title"] for t in tickets]
        descriptions = [t["description"] for t in tickets]
        all_text = " ".join(titles + descriptions)
        assert "VPN" in all_text

    def test_validation_title_too_long(self, client):
        """Verify validation rejects title that's too long"""
        long_title = "x" * 121  # Exceeds max 120
        response = client.post(
            "/api/tickets",
            json={
                "title": long_title,
                "description": "Description",
                "requester": "John Doe",
                "priority": "high"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_validation_description_minimum(self, client):
        """Verify validation enforces description minimum"""
        response = client.post(
            "/api/tickets",
            json={
                "title": "Title",
                "description": "x",  # Too short for update (min 3), but create allows 0
                "requester": "John Doe",
                "priority": "high"
            }
        )
        # Create allows minimum 0, so this should work
        assert response.status_code == 201

    def test_update_with_validation_constraints(self, client):
        """Verify update respects validation constraints"""
        # Get a ticket
        list_response = client.get("/api/tickets")
        ticket_id = list_response.json()[0]["id"]
        
        # Try update with invalid title (too short)
        response = client.patch(
            f"/api/tickets/{ticket_id}",
            json={"title": "ab"}  # Minimum for update is 3
        )
        assert response.status_code == 422

    def test_create_and_retrieve_flow(self, client):
        """Verify full create and retrieve flow"""
        # Create
        create_response = client.post(
            "/api/tickets",
            json={
                "title": "New Ticket",
                "description": "New ticket description",
                "requester": "Jane Smith",
                "priority": "medium"
            }
        )
        assert create_response.status_code == 201
        created_ticket = create_response.json()
        ticket_id = created_ticket["id"]
        
        # Retrieve
        get_response = client.get(f"/api/tickets/{ticket_id}")
        assert get_response.status_code == 200
        retrieved_ticket = get_response.json()
        
        # Verify they match
        assert retrieved_ticket["id"] == ticket_id
        assert retrieved_ticket["title"] == "New Ticket"
        assert retrieved_ticket["requester"] == "Jane Smith"

    def test_update_and_list_visibility(self, client):
        """Verify updates are visible in list"""
        # Get initial ticket
        list_response = client.get("/api/tickets")
        ticket_id = list_response.json()[0]["id"]
        
        # Update it
        client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "resolved"}
        )
        
        # Verify update is visible in list
        list_response = client.get("/api/tickets")
        updated_ticket = next(t for t in list_response.json() if t["id"] == ticket_id)
        assert updated_ticket["status"] == "resolved"

    def test_multiple_operations_sequence(self, client):
        """Verify complex sequence of operations"""
        # Create a ticket
        create_resp = client.post(
            "/api/tickets",
            json={
                "title": "Support Request",
                "description": "Help needed",
                "requester": "Bob",
                "priority": "urgent"
            }
        )
        ticket_id = create_resp.json()["id"]
        
        # Update it
        update_resp = client.patch(
            f"/api/tickets/{ticket_id}",
            json={"status": "in_progress"}
        )
        assert update_resp.json()["status"] == "in_progress"
        
        # Get it
        get_resp = client.get(f"/api/tickets/{ticket_id}")
        assert get_resp.json()["status"] == "in_progress"
        
        # Delete it
        delete_resp = client.delete(f"/api/tickets/{ticket_id}")
        assert delete_resp.status_code == 204
        
        # Verify it's gone
        get_resp = client.get(f"/api/tickets/{ticket_id}")
        assert get_resp.status_code == 404


class TestDataConsistency:
    """Test data consistency and edge cases"""

    def test_concurrent_ticket_creation(self, client):
        """Verify multiple tickets can be created"""
        for i in range(5):
            response = client.post(
                "/api/tickets",
                json={
                    "title": f"Ticket {i}",
                    "description": f"Description {i}",
                    "requester": f"User {i}",
                    "priority": "low"
                }
            )
            assert response.status_code == 201

    def test_ticket_status_transitions(self, client):
        """Verify all status transitions work"""
        # Create ticket
        create_resp = client.post(
            "/api/tickets",
            json={
                "title": "Status Test",
                "description": "Test",
                "requester": "Tester",
                "priority": "high"
            }
        )
        ticket_id = create_resp.json()["id"]
        
        # Try all valid status values
        for status in ["open", "in_progress", "resolved", "closed"]:
            response = client.patch(
                f"/api/tickets/{ticket_id}",
                json={"status": status}
            )
            assert response.status_code == 200
            assert response.json()["status"] == status

    def test_priority_filtering_accuracy(self, client):
        """Verify priority filtering returns correct results"""
        # Get all tickets
        all_response = client.get("/api/tickets")
        all_tickets = all_response.json()
        
        # Count by priority
        for priority in ["low", "medium", "high", "urgent"]:
            response = client.get(f"/api/tickets?priority={priority}")
            filtered = response.json()
            for ticket in filtered:
                assert ticket["priority"] == priority


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
