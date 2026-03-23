"""
Tests for billing API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.database.models import (
    User, Order, TokenUsage, Agent, VM, Plan,
    OrderType, OrderStatus, UserRole, UserStatus, VMStatus, AgentStatus
)
from app.core.security import hash_password


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="billing_test@example.com",
        username="billing_test_user",
        password_hash=hash_password("testpass123"),
        balance=Decimal("100.00"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_plan(db: AsyncSession) -> Plan:
    """Create a test plan."""
    plan = Plan(
        name="Test Plan",
        description="Test plan for billing",
        cpu=2,
        memory=2048,
        disk=20,
        max_agents=5,
        max_channels=5,
        price_per_month=Decimal("50.00")
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@pytest.fixture
async def test_vm(db: AsyncSession, test_user: User, test_plan: Plan) -> VM:
    """Create a test VM."""
    vm = VM(
        user_id=test_user.id,
        plan_id=test_plan.id,
        name="test-vm-billing",
        status=VMStatus.RUNNING,
        cpu=2,
        memory=2048,
        disk=20,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


@pytest.fixture
async def test_agent(db: AsyncSession, test_vm: VM) -> Agent:
    """Create a test agent."""
    agent = Agent(
        vm_id=test_vm.id,
        name="test-agent-billing",
        status=AgentStatus.RUNNING,
        model_config={"provider": "platform", "model_name": "gpt-4"}
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@pytest.fixture
async def test_token_usage(
    db: AsyncSession, 
    test_user: User, 
    test_agent: Agent, 
    test_vm: VM
) -> TokenUsage:
    """Create test token usage records."""
    usage = TokenUsage(
        agent_id=test_agent.id,
        vm_id=test_vm.id,
        user_id=test_user.id,
        model="gpt-4",
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost=Decimal("0.15")
    )
    db.add(usage)
    await db.commit()
    await db.refresh(usage)
    return usage


@pytest.fixture
async def test_order(db: AsyncSession, test_user: User) -> Order:
    """Create a test order."""
    order = Order(
        user_id=test_user.id,
        type=OrderType.RECHARGE,
        amount=Decimal("50.00"),
        balance_before=Decimal("50.00"),
        balance_after=Decimal("100.00"),
        description="Test recharge",
        status=OrderStatus.COMPLETED,
        payment_method="alipay"
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


class TestBillingBalance:
    """Tests for balance endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_balance_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_order: Order,
        test_token_usage: TokenUsage
    ):
        """Test getting balance information."""
        response = await client.get(
            "/api/v1/billing/balance",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        balance_data = data["data"]
        assert "balance" in balance_data
        assert "pending" in balance_data
        assert "total_recharged" in balance_data
        assert "total_used" in balance_data
        
        # Verify values
        assert balance_data["balance"] == 100.0
        assert balance_data["total_recharged"] == 50.0
        assert balance_data["total_used"] == 0.15
    
    @pytest.mark.asyncio
    async def test_get_balance_unauthorized(self, client: AsyncClient):
        """Test getting balance without authentication."""
        response = await client.get("/api/v1/billing/balance")
        assert response.status_code == 401


class TestBillingUsage:
    """Tests for usage records endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_usage_records_success(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        test_token_usage: TokenUsage
    ):
        """Test getting usage records."""
        response = await client.get(
            "/api/v1/billing/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Check pagination structure
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]
        
        # Check record content
        items = data["data"]["items"]
        assert len(items) == 1
        
        record = items[0]
        assert record["model"] == "gpt-4"
        assert record["prompt_tokens"] == 1000
        assert record["completion_tokens"] == 500
        assert record["total_tokens"] == 1500
        assert record["cost"] == 0.15
    
    @pytest.mark.asyncio
    async def test_get_usage_with_date_filter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_token_usage: TokenUsage
    ):
        """Test getting usage records with date filter."""
        start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = await client.get(
            f"/api/v1/billing/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_usage_with_agent_filter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_agent: Agent,
        test_token_usage: TokenUsage
    ):
        """Test getting usage records filtered by agent."""
        response = await client.get(
            f"/api/v1/billing/usage?agent_id={test_agent.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_usage_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_token_usage: TokenUsage
    ):
        """Test usage records pagination."""
        response = await client.get(
            "/api/v1/billing/usage?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10


class TestBillingStats:
    """Tests for usage statistics endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_stats_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_token_usage: TokenUsage
    ):
        """Test getting usage statistics."""
        response = await client.get(
            "/api/v1/billing/stats?period=month",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        stats = data["data"]
        assert stats["total_tokens"] == 1500
        assert stats["total_cost"] == 0.15
        assert "by_agent" in stats
        assert "by_model" in stats
        assert len(stats["by_model"]) == 1
        assert stats["by_model"][0]["model"] == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_get_stats_by_period(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_token_usage: TokenUsage
    ):
        """Test getting statistics for different periods."""
        for period in ["day", "week", "month"]:
            response = await client.get(
                f"/api/v1/billing/stats?period={period}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["period"] == period
    
    @pytest.mark.asyncio
    async def test_get_stats_invalid_period(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting statistics with invalid period."""
        response = await client.get(
            "/api/v1/billing/stats?period=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


class TestBillingOrders:
    """Tests for orders endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_orders_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: Order
    ):
        """Test getting order history."""
        response = await client.get(
            "/api/v1/billing/orders",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        items = data["data"]["items"]
        assert len(items) == 1
        
        order = items[0]
        assert order["type"] == "recharge"
        assert order["amount"] == 50.0
        assert order["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_get_orders_with_type_filter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: Order
    ):
        """Test getting orders filtered by type."""
        response = await client.get(
            "/api/v1/billing/orders?order_type=recharge",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_orders_with_status_filter(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: Order
    ):
        """Test getting orders filtered by status."""
        response = await client.get(
            "/api/v1/billing/orders?status=completed",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_orders_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_order: Order
    ):
        """Test orders pagination."""
        response = await client.get(
            "/api/v1/billing/orders?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10


class TestBillingRecharge:
    """Tests for recharge endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_recharge_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db: AsyncSession
    ):
        """Test creating a recharge order."""
        recharge_data = {
            "amount": 100.0,
            "payment_method": "alipay"
        }
        
        response = await client.post(
            "/api/v1/billing/recharge",
            json=recharge_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        result = data["data"]
        assert result["amount"] == 100.0
        assert result["status"] == "completed"
        assert result["balance_before"] == 100.0
        assert result["balance_after"] == 200.0
        assert "order_id" in result
        
        # Verify balance updated in database
        await db.refresh(test_user)
        assert float(test_user.balance) == 200.0
    
    @pytest.mark.asyncio
    async def test_create_recharge_invalid_amount(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating recharge with invalid amount."""
        recharge_data = {
            "amount": -10.0,
            "payment_method": "alipay"
        }
        
        response = await client.post(
            "/api/v1/billing/recharge",
            json=recharge_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_create_recharge_invalid_payment_method(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test creating recharge with invalid payment method."""
        recharge_data = {
            "amount": 100.0,
            "payment_method": "invalid_method"
        }
        
        response = await client.post(
            "/api/v1/billing/recharge",
            json=recharge_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid payment method" in response.json()["data"]["error"]
    
    @pytest.mark.asyncio
    async def test_create_recharge_wechat(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db: AsyncSession
    ):
        """Test creating recharge with WeChat payment."""
        recharge_data = {
            "amount": 50.0,
            "payment_method": "wechat"
        }
        
        response = await client.post(
            "/api/v1/billing/recharge",
            json=recharge_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["payment_method"] == "wechat"


class TestBillingPermissions:
    """Tests for billing API permissions."""
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_data(
        self,
        client: AsyncClient,
        test_token_usage: TokenUsage,
        db: AsyncSession
    ):
        """Test that users cannot access other users' billing data."""
        # Create another user
        other_user = User(
            email="other@example.com",
            username="other_user",
            password_hash=hash_password("pass123"),
            balance=Decimal("50.00"),
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)
        
        # Login as other user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "other@example.com",
                "password": "pass123"
            }
        )
        
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access first user's data
        response = await client.get(
            "/api/v1/billing/usage",
            headers=headers
        )
        
        # Should get empty results, not the other user's data
        data = response.json()
        assert data["data"]["total"] == 0
